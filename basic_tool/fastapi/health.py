"""健康检查端点。

提供 Kubernetes 风格的存活性探针和就绪性探针，
支持检查 Redis、HTTP Client、TaskQueue 等服务状态。
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger


def create_health_router(
    prefix: str = "/health",
    **service_checks: Any,
) -> APIRouter:
    """创建健康检查路由器。

    注册两个端点：
    - GET {prefix} — 存活探针，始终返回 200。
    - GET {prefix}/ready — 就绪探针，检查所有已注入的服务状态。

    Args:
        prefix: 端点路径前缀。
        **service_checks: 命名的服务检查器，每个值需有 async check() 方法。
                          例如 cache=Cache 实例, http_client=HttpClient 实例。

    Returns:
        配置好的 APIRouter。
    """
    router = APIRouter(tags=["health"])

    @router.get(prefix)
    async def liveness() -> dict:
        """存活探针。

        Returns:
            {"status": "healthy"}，进程存活即返回 200。
        """
        return {"status": "healthy"}

    @router.get(f"{prefix}/ready")
    async def readiness(request: Request) -> JSONResponse:
        """就绪探针。

        检查所有已注入的服务状态。任一服务异常时返回 503。

        Returns:
            {"status": "ready"|"degraded", "checks": {...}}
        """
        checks: dict[str, str] = {}

        for name, service in service_checks.items():
            try:
                if hasattr(service, "check"):
                    result = await service.check()
                    if isinstance(result, dict) and result.get("status") == "error":
                        checks[name] = "error"
                    else:
                        checks[name] = "ok"
                elif hasattr(service, "client"):
                    # 对于 Cache 等有 client 属性的服务，尝试 ping
                    client = service.client
                    if hasattr(client, "ping"):
                        await client.ping()
                        checks[name] = "ok"
                    else:
                        checks[name] = "ok"
                else:
                    checks[name] = "ok"
            except Exception as e:
                logger.warning("健康检查失败 | service={} error={}", name, e)
                checks[name] = "error"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "ready" if all_ok else "degraded",
                "checks": checks,
            },
        )

    return router
