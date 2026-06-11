"""HTTP 客户端健康检查。

向指定健康检查端点发送 GET 请求，返回可用性状态和熔断器状态。
"""

import time

from loguru import logger

from basic_tool.http_client.client import HttpClient


class HttpHealth:
    """HTTP 客户端健康检查。

    向指定健康检查端点发送 GET 请求，返回可用性状态。
    同时返回熔断器状态（如果启用）。

    使用示例::

        http = HttpClient(config)
        await http.init()
        health = HttpHealth(http)
        result = await health.check()
        # {"status": "healthy", "status_code": 200, "latency_ms": 42.1, "circuit_breaker": "closed"}
    """

    def __init__(self, http: HttpClient, health_path: str = "/health") -> None:
        """初始化 HttpHealth。

        Args:
            http: HttpClient 实例。
            health_path: 健康检查端点路径。
        """
        self._http = http
        self._health_path = health_path

    async def check(self) -> dict:
        """执行健康检查。

        Returns:
            健康状态字典，包含 status、status_code、latency_ms、circuit_breaker 字段。
        """
        start = time.monotonic()

        try:
            response = await self._http.client.get(self._health_path)
            latency_ms = (time.monotonic() - start) * 1000

            result = {
                "status": "healthy" if response.status_code < 400 else "unhealthy",
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 1),
                "circuit_breaker": self._get_circuit_breaker_state(),
            }

            logger.info(
                "HTTP 健康检查完成 | status={} status_code={} latency={:.1f}ms",
                result["status"], result["status_code"], latency_ms,
            )
            return result

        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("HTTP 健康检查失败 | error={} latency={:.1f}ms", e, latency_ms)
            return {
                "status": "unreachable",
                "error": str(e),
                "latency_ms": round(latency_ms, 1),
                "circuit_breaker": self._get_circuit_breaker_state(),
            }

    def _get_circuit_breaker_state(self) -> str:
        """获取熔断器状态。

        Returns:
            熔断器状态字符串，未启用时返回 "disabled"。
        """
        from basic_tool.http_client.transport import CircuitBreakerTransport

        try:
            transport = getattr(self._http.client, "_transport", None)
            if transport is None:
                return "disabled"
            # 沿 transport 链查找 CircuitBreakerTransport
            current = transport
            for _ in range(10):  # 防止无限循环
                if isinstance(current, CircuitBreakerTransport):
                    return current.state
                current = getattr(current, "_inner", None)
                if current is None:
                    break
        except Exception:
            pass

        return "disabled"
