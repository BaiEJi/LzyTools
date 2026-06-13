"""HTTP 客户端工厂和生命周期管理。

自动组装 transport 链（Retry + CircuitBreaker）和结构化日志钩子，
返回原生 httpx.AsyncClient 实例。
"""

import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from loguru import logger

from basic_tool.context.propagation import inject_headers_to_httpx
from basic_tool.http_client.config import HttpConfig
from basic_tool.http_client.transport import CircuitBreakerTransport, RetryTransport


class HttpClient:
    """HTTP 客户端，封装 httpx.AsyncClient 的生命周期和横切关注点。

    自动配置重试、熔断、结构化日志。
    返回的 client 属性就是原生 httpx.AsyncClient，用法完全一致。

    使用示例::

        config = HttpConfig(
            base_url="https://api.example.com",
            retry=RetryConfig(max_retries=3),
            circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
        )
        http = HttpClient(config)
        await http.init()

        # 用原生 httpx API 发请求
        resp = await http.client.get("/users/1")
        resp = await http.client.post("/users", json={"name": "test"})

        await http.close()

        # 或用 async with
        async with HttpClient(config) as http:
            resp = await http.client.get("/health")
    """

    def __init__(self, config: HttpConfig) -> None:
        """初始化 HttpClient。

        Args:
            config: HTTP 客户端配置。
        """
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """返回底层 httpx.AsyncClient 实例。

        Returns:
            原生 httpx.AsyncClient，用法完全一致。

        Raises:
            RuntimeError: 未调用 init() 时访问。
        """
        if self._client is None:
            raise RuntimeError("HttpClient 未初始化，请先调用 await init()")
        return self._client

    async def init(self) -> None:
        """初始化 httpx.AsyncClient。

        自动组装 transport 链和日志钩子。幂等操作。

        Raises:
            初始化失败时抛出原始异常。
        """
        if self._client is not None:
            logger.warning("HttpClient 已初始化，跳过重复初始化")
            return

        try:
            transport = self._build_transport()
            event_hooks = self._build_event_hooks()
            timeout = httpx.Timeout(
                connect=self._config.connect_timeout,
                read=self._config.read_timeout,
                write=self._config.timeout,
                pool=self._config.timeout,
            )
            limits = httpx.Limits(
                max_connections=self._config.max_connections,
                max_keepalive_connections=self._config.max_keepalive,
            )

            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=self._config.headers or None,
                timeout=timeout,
                limits=limits,
                follow_redirects=self._config.follow_redirects,
                http2=self._config.http2,
                transport=transport,
                event_hooks=event_hooks,
            )

            logger.info(
                "HttpClient 初始化完成 | base_url={} retry={} circuit_breaker={}",
                self._config.base_url,
                self._config.retry is not None,
                self._config.circuit_breaker is not None,
            )
        except Exception as e:
            logger.error("HttpClient 初始化失败 | base_url={} error={}", self._config.base_url, e)
            self._client = None
            raise

    async def close(self) -> None:
        """关闭 httpx.AsyncClient。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("HttpClient 已关闭")

    async def __aenter__(self) -> "HttpClient":
        """异步上下文管理器入口。"""
        await self.init()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口。"""
        await self.close()

    def _build_transport(self) -> httpx.AsyncBaseTransport:
        """根据配置组装 transport 链。

        组装顺序：RetryTransport → CircuitBreakerTransport → AsyncHTTPTransport
        外层重试 → 内层熔断 → 实际网络。

        Returns:
            组装好的 transport。
        """
        transport: httpx.AsyncBaseTransport = httpx.AsyncHTTPTransport(retries=0)

        if self._config.circuit_breaker is not None:
            transport = CircuitBreakerTransport(transport, self._config.circuit_breaker)

        if self._config.retry is not None:
            transport = RetryTransport(
                transport, self._config.retry, metrics=self._config.metrics
            )

        return transport

    def _build_event_hooks(self) -> dict[str, list]:
        """构建事件钩子（日志 + 上下文传播头注入 + 出站请求指标）。

        当 ``log_requests`` 为 True 时记录请求/响应日志。
        当 ``propagate_context`` 为 True 时，在请求发出前自动注入当前
        请求上下文的传播头（X-Trace-Id 等），不覆盖用户已设置的头。
        当 ``metrics`` 不为 None 时，``on_response`` 钩子额外记录
        ``http_client_requests_total``（counter）和
        ``http_client_request_duration_seconds``（histogram）；记录失败
        不影响请求本身（try/except 兜底）。

        Returns:
            httpx event_hooks 字典。无活跃配置时返回空字典。
        """
        need_request_hook = (
            self._config.log_requests
            or self._config.propagate_context
            or self._config.metrics is not None
        )
        if not need_request_hook:
            return {}

        need_start_time = self._config.log_requests or self._config.metrics is not None

        async def on_request(request: httpx.Request) -> None:
            """请求开始钩子：注入上下文传播头并记录日志。"""
            if self._config.propagate_context:
                ctx_headers = inject_headers_to_httpx()
                for name, value in ctx_headers.items():
                    if name not in request.headers:
                        request.headers[name] = value

            if need_start_time:
                request.extensions["_start_time"] = time.monotonic()

            if self._config.log_requests:
                logger.info(
                    "HTTP 请求开始 | method={} url={}",
                    request.method, request.url,
                )

        hooks: dict[str, list] = {"request": [on_request]}

        if self._config.log_requests or self._config.metrics is not None:
            async def on_response(response: httpx.Response) -> None:
                """请求完成钩子：记录日志和/或出站请求指标。"""
                request = response.request
                start = request.extensions.get("_start_time")
                elapsed_ms = (time.monotonic() - start) * 1000 if start else 0

                if self._config.log_requests:
                    logger.info(
                        "HTTP 请求完成 | method={} url={} status={} elapsed={:.1f}ms",
                        request.method, request.url,
                        response.status_code, elapsed_ms,
                    )

                    if response.is_error:
                        body_preview = ""
                        if self._config.log_response_body:
                            body_preview = response.text[:self._config.max_body_log_size]
                        logger.warning(
                            "HTTP 请求异常 | method={} url={} status={} body={}",
                            request.method, request.url,
                            response.status_code, body_preview,
                        )

                if self._config.metrics is not None:
                    try:
                        self._config.metrics.counter(
                            "http_client_requests_total",
                            labels={
                                "method": request.method,
                                "url": str(request.url),
                                "status": str(response.status_code),
                            },
                        )
                        self._config.metrics.histogram(
                            "http_client_request_duration_seconds",
                            elapsed_ms / 1000,
                            labels={
                                "method": request.method,
                                "url": str(request.url),
                            },
                        )
                    except Exception:
                        logger.debug("metrics 记录失败", exc_info=True)

            hooks["response"] = [on_response]

        return hooks
