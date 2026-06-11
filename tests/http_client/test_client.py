"""HttpClient 生命周期和配置测试。"""

import httpx
import pytest

from basic_tool.http_client.client import HttpClient
from basic_tool.http_client.config import CircuitBreakerConfig, HttpConfig, RetryConfig
from basic_tool.http_client.transport import CircuitBreakerTransport, RetryTransport


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
