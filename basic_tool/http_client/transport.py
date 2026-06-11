"""自定义 HTTP transport 层。

提供 RetryTransport（带重试逻辑）和 CircuitBreakerTransport（带熔断器），
通过装饰器模式包装底层 transport，组合使用。

设计思路::

    用户请求 → RetryTransport → CircuitBreakerTransport → httpx.AsyncHTTPTransport → 网络
"""

import asyncio
import time
from typing import Any

import httpx
from loguru import logger

from basic_tool.http_client.config import CircuitBreakerConfig, RetryConfig


class RetryTransport(httpx.AsyncBaseTransport):
    """带重试逻辑的 HTTP transport。

    对可重试状态码和连接异常自动重试，指数退避。

    Args:
        inner: 被包装的底层 transport。
        config: 重试配置。
    """

    def __init__(self, inner: httpx.AsyncBaseTransport, config: RetryConfig) -> None:
        """初始化 RetryTransport。

        Args:
            inner: 被包装的底层 transport。
            config: 重试配置。
        """
        self._inner = inner
        self._config = config

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """发送请求，失败时自动重试。

        Args:
            request: httpx 请求对象。

        Returns:
            httpx 响应对象。

        Raises:
            重试次数耗尽后抛出最后一个异常。
        """
        last_exc: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await self._inner.handle_async_request(request)

                if response.status_code not in self._config.retryable_status_codes:
                    return response

                # 可重试的状态码
                last_exc = httpx.HTTPStatusError(
                    f"服务端错误 | status={response.status_code}",
                    request=request,
                    response=response,
                )
                logger.warning(
                    "HTTP 请求重试（状态码） | attempt={} max={} status={} url={}",
                    attempt + 1, self._config.max_retries,
                    response.status_code, request.url,
                )

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                logger.warning(
                    "HTTP 请求重试（连接异常） | attempt={} max={} error={} url={}",
                    attempt + 1, self._config.max_retries,
                    type(e).__name__, request.url,
                )

            # 退避等待
            if attempt < self._config.max_retries - 1:
                delay = self._config.backoff_factor * (2 ** attempt)
                await asyncio.sleep(delay)

        # 重试次数耗尽
        logger.error(
            "HTTP 请求重试耗尽 | max={} url={}",
            self._config.max_retries, request.url,
        )
        raise last_exc


class CircuitBreakerTransport(httpx.AsyncBaseTransport):
    """带熔断器的 HTTP transport。

    连续失败达到阈值后进入熔断状态，直接拒绝请求。
    熔断恢复超时后进入半开状态，放行一个请求试探。

    Args:
        inner: 被包装的底层 transport。
        config: 熔断器配置。
    """

    def __init__(self, inner: httpx.AsyncBaseTransport, config: CircuitBreakerConfig) -> None:
        """初始化 CircuitBreakerTransport。

        Args:
            inner: 被包装的底层 transport。
            config: 熔断器配置。
        """
        self._inner = inner
        self._config = config
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"  # closed | open | half_open

    @property
    def state(self) -> str:
        """返回当前熔断器状态。

        Returns:
            "closed"（正常）、"open"（熔断）、"half_open"（半开）。
        """
        self._check_recovery()
        return self._state

    def _check_recovery(self) -> None:
        """检查是否应该从熔断状态恢复到半开状态。"""
        if self._state == "open":
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed > self._config.recovery_timeout:
                self._state = "half_open"
                logger.info(
                    "熔断器恢复到半开状态 | recovery_timeout={}s",
                    self._config.recovery_timeout,
                )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """发送请求，熔断时直接拒绝。

        Args:
            request: httpx 请求对象。

        Returns:
            httpx 响应对象。

        Raises:
            httpx.ConnectError: 熔断状态时拒绝请求。
        """
        self._check_recovery()

        if self._state == "open":
            logger.warning("请求被熔断器拒绝 | state={} url={}", self._state, request.url)
            raise httpx.ConnectError(
                f"熔断器已开启 | failures={self._failure_count} "
                f"threshold={self._config.failure_threshold}",
                request=request,
            )

        try:
            response = await self._inner.handle_async_request(request)

            if response.status_code >= 500:
                self._record_failure(request.url)
            else:
                self._record_success()

            return response

        except (httpx.ConnectError, httpx.TimeoutException):
            self._record_failure(request.url)
            raise

    def _record_failure(self, url: Any) -> None:
        """记录一次失败。"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self._config.failure_threshold:
            self._state = "open"
            logger.error(
                "熔断器开启 | failures={} threshold={} url={}",
                self._failure_count, self._config.failure_threshold, url,
            )

    def _record_success(self) -> None:
        """记录一次成功，重置失败计数。"""
        if self._failure_count > 0:
            logger.info("熔断器重置 | previous_failures={}", self._failure_count)
        self._failure_count = 0
        self._state = "closed"
