"""HttpClient 生命周期和配置测试。"""

import httpx
import pytest

from basic_tool.context.ctx import request_context
from basic_tool.http_client.client import HttpClient
from basic_tool.http_client.config import CircuitBreakerConfig, HttpConfig, RetryConfig
from basic_tool.http_client.transport import CircuitBreakerTransport, RetryTransport
from basic_tool.metrics.collector import MetricsCollector
from basic_tool.metrics.config import MetricsConfig


def _mock_handler(status_code: int = 200, body: str = "ok"):
    """创建一个返回固定响应的 mock handler。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, text=body)

    return handler


class TestHttpClientLifecycle:
    """HttpClient 生命周期测试。"""

    @pytest.mark.asyncio
    async def test_init_and_close(self):
        """init() 创建客户端，close() 关闭。"""
        config = HttpConfig()
        http = HttpClient(config)

        # Mock transport 以避免真实网络请求
        mock_transport = httpx.MockTransport(_mock_handler(200))
        await http.init()
        http._client._transport = mock_transport

        assert http._client is not None
        await http.close()
        assert http._client is None

    @pytest.mark.asyncio
    async def test_client_before_init_raises(self):
        """未初始化时访问 client 抛出 RuntimeError。"""
        config = HttpConfig()
        http = HttpClient(config)

        with pytest.raises(RuntimeError, match="未初始化"):
            _ = http.client

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """async with 自动初始化和关闭。"""
        config = HttpConfig()

        async with HttpClient(config) as http:
            # Mock transport
            mock_transport = httpx.MockTransport(_mock_handler(200))
            http._client._transport = mock_transport
            assert http._client is not None

        # 退出后应已关闭
        assert http._client is None

    @pytest.mark.asyncio
    async def test_init_idempotent(self):
        """重复 init() 不会创建新客户端。"""
        config = HttpConfig()
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(_mock_handler(200))
        await http.init()
        http._client._transport = mock_transport

        first_client = http._client
        await http.init()
        assert http._client is first_client

    @pytest.mark.asyncio
    async def test_client_is_native_httpx(self):
        """client 属性返回原生 httpx.AsyncClient。"""
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(_mock_handler(200))
        await http.init()
        http._client._transport = mock_transport

        assert isinstance(http.client, httpx.AsyncClient)
        await http.close()


class TestHttpClientTransportAssembly:
    """HttpClient transport 组装测试。"""

    def test_build_transport_no_config(self):
        """无重试和熔断配置时使用默认 transport。"""
        config = HttpConfig()
        http = HttpClient(config)
        transport = http._build_transport()

        # 应该是原生 AsyncHTTPTransport
        assert isinstance(transport, httpx.AsyncHTTPTransport)

    def test_build_transport_with_retry(self):
        """有重试配置时组装 RetryTransport。"""
        config = HttpConfig(retry=RetryConfig(max_retries=3))
        http = HttpClient(config)
        transport = http._build_transport()

        assert isinstance(transport, RetryTransport)

    def test_build_transport_with_circuit_breaker(self):
        """有熔断配置时组装 CircuitBreakerTransport。"""
        config = HttpConfig(circuit_breaker=CircuitBreakerConfig(failure_threshold=5))
        http = HttpClient(config)
        transport = http._build_transport()

        assert isinstance(transport, CircuitBreakerTransport)

    def test_build_transport_with_both(self):
        """同时有重试和熔断时，RetryTransport 在外层。"""
        config = HttpConfig(
            retry=RetryConfig(max_retries=3),
            circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
        )
        http = HttpClient(config)
        transport = http._build_transport()

        # 外层是 Retry，内层是 CircuitBreaker
        assert isinstance(transport, RetryTransport)
        assert isinstance(transport._inner, CircuitBreakerTransport)


class TestHttpClientRequests:
    """HttpClient 实际请求测试（使用 MockTransport）。"""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """GET 请求正常工作。"""
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(_mock_handler(200, '{"data": 1}'))
        await http.init()
        http._client._transport = mock_transport

        response = await http.client.get("/api/data")
        assert response.status_code == 200
        assert response.json() == {"data": 1}
        await http.close()

    @pytest.mark.asyncio
    async def test_post_request(self):
        """POST 请求正常工作。"""

        async def handler(request: httpx.Request) -> httpx.Response:
            body = await request.aread()
            return httpx.Response(200, text=body.decode())

        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(handler)
        await http.init()
        http._client._transport = mock_transport

        response = await http.client.post("/api/data", json={"key": "value"})
        assert response.status_code == 200
        await http.close()


def _header_capture_handler():
    """创建一个捕获请求头的 mock handler，返回 (captured_dict, handler)。"""
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        for key in request.headers:
            captured[key] = request.headers[key]
        return httpx.Response(200, text="ok")

    return captured, handler


class TestContextPropagation:
    """上下文传播头自动注入测试。"""

    @pytest.mark.asyncio
    async def test_headers_injected_when_context_active(self):
        """活跃上下文 + propagate=True → 注入 X-Trace-Id。"""
        captured, handler = _header_capture_handler()
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(handler)

        async with request_context(trace_id="abc123", span_id="def456"):
            await http.client.get("/api")

        await http.close()
        assert captured.get("x-trace-id") == "abc123"
        assert captured.get("x-span-id") == "def456"

    @pytest.mark.asyncio
    async def test_headers_not_injected_without_context(self):
        """无活跃上下文 → 不注入 X-Trace-Id。"""
        captured, handler = _header_capture_handler()
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(handler)

        await http.client.get("/api")

        await http.close()
        assert "x-trace-id" not in captured

    @pytest.mark.asyncio
    async def test_headers_not_injected_when_disabled(self):
        """propagate_context=False → 即使有上下文也不注入。"""
        captured, handler = _header_capture_handler()
        config = HttpConfig(base_url="http://test", propagate_context=False)
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(handler)

        async with request_context(trace_id="abc123"):
            await http.client.get("/api")

        await http.close()
        assert "x-trace-id" not in captured

    @pytest.mark.asyncio
    async def test_user_headers_not_overwritten(self):
        """用户显式设置的 X-Trace-Id 不被覆盖。"""
        captured, handler = _header_capture_handler()
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(handler)

        async with request_context(trace_id="ctx-trace"):
            await http.client.get("/api", headers={"X-Trace-Id": "user-value"})

        await http.close()
        assert captured.get("x-trace-id") == "user-value"


def _make_collector() -> MetricsCollector:
    """构造一个未初始化（无网络）的 MetricsCollector 用于测试。"""
    return MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://vm:8428")


class TestHttpClientMetrics:
    """HttpClient 出站请求指标采集测试。"""

    @pytest.mark.asyncio
    async def test_metrics_recorded_when_provided(self):
        """提供 MetricsCollector 时记录 counter 和 histogram。"""
        collector = _make_collector()
        config = HttpConfig(base_url="http://test", metrics=collector, log_requests=False)
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(_mock_handler(200))

        await http.client.get("/api/data")
        await http.close()

        counter_points = collector._buffers.get("http_client_requests_total", [])
        assert len(counter_points) == 1
        cp = counter_points[0]
        assert cp.labels["method"] == "GET"
        assert cp.labels["status"] == "200"
        assert "/api/data" in cp.labels["url"]

        hist_points = collector._buffers.get("http_client_request_duration_seconds", [])
        assert len(hist_points) == 1
        hp = hist_points[0]
        assert hp.labels["method"] == "GET"
        assert "/api/data" in hp.labels["url"]
        assert hp.value >= 0

    @pytest.mark.asyncio
    async def test_metrics_labels_status_code(self):
        """不同状态码被记录到 status label。"""
        collector = _make_collector()
        config = HttpConfig(base_url="http://test", metrics=collector, log_requests=False)
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(_mock_handler(500))
        await http.client.get("/api/fail")
        await http.close()

        cp = collector._buffers["http_client_requests_total"][0]
        assert cp.labels["status"] == "500"

    @pytest.mark.asyncio
    async def test_metrics_none_zero_overhead(self):
        """metrics=None 时正常工作，无额外钩子。"""
        config = HttpConfig(base_url="http://test", log_requests=False, propagate_context=False)
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(_mock_handler(200))

        response = await http.client.get("/api/data")
        assert response.status_code == 200
        await http.close()

    @pytest.mark.asyncio
    async def test_metrics_none_no_response_hook(self):
        """metrics=None 且 log_requests=False 时不注册 response 钩子。"""
        config = HttpConfig(log_requests=False, propagate_context=False)
        http = HttpClient(config)
        hooks = http._build_event_hooks()
        assert "response" not in hooks

    @pytest.mark.asyncio
    async def test_metrics_records_without_log_requests(self):
        """log_requests=False 但 metrics 提供时仍记录指标，且不记录日志。"""
        collector = _make_collector()
        config = HttpConfig(base_url="http://test", metrics=collector, log_requests=False)
        http = HttpClient(config)

        await http.init()
        http._client._transport = httpx.MockTransport(_mock_handler(200))
        await http.client.get("/api/x")
        await http.close()

        assert "http_client_requests_total" in collector._buffers

    def test_no_circular_import(self):
        """http_client 和 metrics 无循环导入。"""
        import basic_tool.http_client  # noqa: F401
        import basic_tool.metrics  # noqa: F401
