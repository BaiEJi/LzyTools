"""RetryTransport 和 CircuitBreakerTransport 测试。"""

import asyncio

import httpx
import pytest

from basic_tool.http_client.config import CircuitBreakerConfig, RetryConfig
from basic_tool.http_client.transport import CircuitBreakerTransport, RetryTransport
from basic_tool.metrics.collector import MetricsCollector
from basic_tool.metrics.config import MetricsConfig


def _mock_handler(status_code: int = 200, body: str = "ok"):
    """创建一个返回固定响应的 mock handler。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, text=body)

    return handler


def _mock_handler_sequence(responses: list):
    """创建一个按顺序返回不同响应的 mock handler。"""
    call_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        if isinstance(resp, Exception):
            raise resp
        return httpx.Response(status_code=resp, text=f"status={resp}")

    return handler, lambda: call_count


class TestRetryTransport:
    """RetryTransport 测试。"""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """成功响应不重试。"""
        config = RetryConfig(max_retries=3, retryable_status_codes=frozenset({503}))
        inner = httpx.MockTransport(_mock_handler(200))
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_on_retryable_status(self):
        """可重试状态码触发重试。"""
        handler, get_count = _mock_handler_sequence([503, 503, 200])
        config = RetryConfig(
            max_retries=3,
            backoff_factor=0.01,  # 快速退避
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(handler)
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
        assert get_count() == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """重试次数耗尽抛出异常。"""
        config = RetryConfig(
            max_retries=2,
            backoff_factor=0.01,
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(_mock_handler(503))
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("http://test/api")

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self):
        """连接异常触发重试。"""
        call_count = 0

        async def flaky_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused", request=request)
            return httpx.Response(200, text="ok")

        config = RetryConfig(
            max_retries=3,
            backoff_factor=0.01,
            retryable_status_codes=frozenset(),
        )
        inner = httpx.MockTransport(flaky_handler)
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_status(self):
        """非可重试状态码不重试。"""
        config = RetryConfig(
            max_retries=3,
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(_mock_handler(400))
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 400


class TestCircuitBreakerTransport:
    """CircuitBreakerTransport 测试。"""

    @pytest.mark.asyncio
    async def test_closed_state_allows_requests(self):
        """关闭状态允许请求通过。"""
        config = CircuitBreakerConfig(failure_threshold=5)
        inner = httpx.MockTransport(_mock_handler(200))
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
        assert transport.state == "closed"

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """连续失败达到阈值后开启熔断。"""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)
        inner = httpx.MockTransport(_mock_handler(500))
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            for _ in range(3):
                await client.get("http://test/api")

        assert transport.state == "open"

    @pytest.mark.asyncio
    async def test_open_state_rejects_requests(self):
        """熔断状态拒绝请求。"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60.0)
        inner = httpx.MockTransport(_mock_handler(500))
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            # 触发熔断
            await client.get("http://test/api")

            # 熔断后拒绝
            with pytest.raises(httpx.ConnectError, match="熔断器"):
                await client.get("http://test/api")

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        """恢复超时后进入半开状态。"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        inner = httpx.MockTransport(_mock_handler(500))
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            # 触发熔断
            await client.get("http://test/api")
            assert transport.state == "open"

            # 等待恢复
            await asyncio.sleep(0.15)
            assert transport.state == "half_open"

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """成功请求重置失败计数。"""
        config = CircuitBreakerConfig(failure_threshold=5)
        handler, get_count = _mock_handler_sequence([500, 500, 200])
        inner = httpx.MockTransport(handler)
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            await client.get("http://test/api")  # 失败 1
            await client.get("http://test/api")  # 失败 2
            await client.get("http://test/api")  # 成功

        assert transport.state == "closed"
        assert transport._failure_count == 0

    @pytest.mark.asyncio
    async def test_connect_error_counts_as_failure(self):
        """连接异常计入失败。"""
        call_count = 0

        async def failing_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused", request=request)

        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
        inner = httpx.MockTransport(failing_handler)
        transport = CircuitBreakerTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.ConnectError):
                await client.get("http://test/api")
            with pytest.raises(httpx.ConnectError):
                await client.get("http://test/api")

        assert transport.state == "open"


def _make_collector() -> MetricsCollector:
    """构造一个未初始化（无网络）的 MetricsCollector 用于测试。"""
    return MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://vm:8428")


class TestRetryTransportMetrics:
    """RetryTransport 重试指标测试。"""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_status_retry(self):
        """可重试状态码触发重试时记录 counter。"""
        handler, _ = _mock_handler_sequence([503, 503, 200])
        config = RetryConfig(
            max_retries=3,
            backoff_factor=0.01,
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(handler)
        collector = _make_collector()
        transport = RetryTransport(inner, config, metrics=collector)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
        points = collector._buffers.get("http_client_retries_total", [])
        assert len(points) == 2  # 两次 503 各记录一次
        assert all("http://test/api" == p.labels["url"] for p in points)

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_connect_error_retry(self):
        """连接异常触发重试时记录 counter。"""
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("refused", request=request)
            return httpx.Response(200, text="ok")

        config = RetryConfig(max_retries=3, backoff_factor=0.01)
        inner = httpx.MockTransport(handler)
        collector = _make_collector()
        transport = RetryTransport(inner, config, metrics=collector)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
        points = collector._buffers.get("http_client_retries_total", [])
        assert len(points) == 2  # 两次 ConnectError 各记录一次

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_exhausted(self):
        """重试耗尽时也记录 counter。"""
        handler, _ = _mock_handler_sequence([503, 503, 503])
        config = RetryConfig(
            max_retries=3,
            backoff_factor=0.01,
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(handler)
        collector = _make_collector()
        transport = RetryTransport(inner, config, metrics=collector)

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("http://test/api")

        points = collector._buffers.get("http_client_retries_total", [])
        assert len(points) == 4  # 3 次状态码重试 + 1 次耗尽

    @pytest.mark.asyncio
    async def test_metrics_none_no_overhead(self):
        """metrics=None（默认）时重试仍正常工作，无指标记录。"""
        handler, _ = _mock_handler_sequence([503, 200])
        config = RetryConfig(
            max_retries=3,
            backoff_factor=0.01,
            retryable_status_codes=frozenset({503}),
        )
        inner = httpx.MockTransport(handler)
        transport = RetryTransport(inner, config)  # metrics 默认 None

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_none_no_retry_no_error(self):
        """metrics=None 且无重试时正常返回。"""
        config = RetryConfig(max_retries=3)
        inner = httpx.MockTransport(_mock_handler(200))
        transport = RetryTransport(inner, config)

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("http://test/api")

        assert response.status_code == 200
