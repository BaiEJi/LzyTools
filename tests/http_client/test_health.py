"""HttpHealth 健康检查测试。"""

import httpx
import pytest

from basic_tool.http_client.client import HttpClient
from basic_tool.http_client.config import CircuitBreakerConfig, HttpConfig
from basic_tool.http_client.health import HttpHealth
from basic_tool.http_client.transport import CircuitBreakerTransport


def _mock_handler(status_code: int = 200, body: str = "ok"):
    """创建一个返回固定响应的 mock handler。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, text=body)

    return handler


class TestHttpHealth:
    """HttpHealth 测试。"""

    @pytest.mark.asyncio
    async def test_check_healthy(self):
        """健康检查成功。"""
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(_mock_handler(200))
        await http.init()
        http._client._transport = mock_transport

        health = HttpHealth(http)
        result = await health.check()

        assert result["status"] == "healthy"
        assert result["status_code"] == 200
        assert "latency_ms" in result
        assert result["circuit_breaker"] == "disabled"
        await http.close()

    @pytest.mark.asyncio
    async def test_check_unhealthy(self):
        """下游返回 5xx 时状态为 unhealthy。"""
        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(_mock_handler(500))
        await http.init()
        http._client._transport = mock_transport

        health = HttpHealth(http)
        result = await health.check()

        assert result["status"] == "unhealthy"
        assert result["status_code"] == 500
        await http.close()

    @pytest.mark.asyncio
    async def test_check_unreachable(self):
        """下游不可达时状态为 unreachable。"""

        async def failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused", request=request)

        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(failing_handler)
        await http.init()
        http._client._transport = mock_transport

        health = HttpHealth(http)
        result = await health.check()

        assert result["status"] == "unreachable"
        assert "error" in result
        await http.close()

    @pytest.mark.asyncio
    async def test_check_custom_health_path(self):
        """自定义健康检查路径。"""

        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/ping":
                return httpx.Response(200, text="pong")
            return httpx.Response(404)

        config = HttpConfig(base_url="http://test")
        http = HttpClient(config)

        mock_transport = httpx.MockTransport(handler)
        await http.init()
        http._client._transport = mock_transport

        health = HttpHealth(http, health_path="/ping")
        result = await health.check()

        assert result["status"] == "healthy"
        assert result["status_code"] == 200
        await http.close()

    @pytest.mark.asyncio
    async def test_check_reports_circuit_breaker_state(self):
        """健康检查报告熔断器状态。"""
        config = HttpConfig(
            base_url="http://test",
            circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
        )
        http = HttpClient(config)
        await http.init()

        # Mock 最内层 transport（AsyncHTTPTransport），保留外层 CircuitBreakerTransport
        mock_inner = httpx.MockTransport(_mock_handler(200))
        # transport 链: CircuitBreakerTransport -> AsyncHTTPTransport
        # 替换 CircuitBreakerTransport 的 _inner
        http._client._transport._inner = mock_inner

        health = HttpHealth(http)
        result = await health.check()

        # transport 链中有 CircuitBreakerTransport
        assert result["circuit_breaker"] == "closed"
        await http.close()
