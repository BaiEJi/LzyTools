"""HTTP 客户端 SDK。

基于 httpx 的异步 HTTP 客户端封装，提供自动重试、熔断器、
结构化日志、健康检查和生命周期管理。

使用示例::

    from basic_tool.http_client import HttpClient, HttpConfig, RetryConfig, CircuitBreakerConfig

    config = HttpConfig(
        base_url="https://api.example.com",
        retry=RetryConfig(max_retries=3),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
    )

    async with HttpClient(config) as http:
        resp = await http.client.get("/users/1")
        resp = await http.client.post("/users", json={"name": "test"})
"""

from basic_tool.http_client.client import HttpClient
from basic_tool.http_client.config import CircuitBreakerConfig, HttpConfig, RetryConfig
from basic_tool.http_client.health import HttpHealth
from basic_tool.http_client.transport import CircuitBreakerTransport, RetryTransport

__all__ = [
    "HttpClient",
    "HttpConfig",
    "HttpHealth",
    "RetryConfig",
    "CircuitBreakerConfig",
    "RetryTransport",
    "CircuitBreakerTransport",
]
