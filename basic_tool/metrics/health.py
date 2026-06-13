"""
Metrics 健康检查。

检查 VictoriaMetrics 和 Redis 连接状态，返回结构化健康报告。
"""

from loguru import logger

from basic_tool.metrics.reader import MetricsReader
from basic_tool.metrics.writer import MetricsWriter


class MetricsHealth:
    """Metrics 模块健康检查。

    检查 writer（Redis 连接）和 reader（VictoriaMetrics 连接）的健康状态，
    返回 {"ok": bool, "components": {...}} 结构。

    使用示例::

        health = MetricsHealth(writer, reader)
        result = await health.check()
        # {"ok": True, "components": {"victoriametrics": {"ok": True}, "redis": {"ok": True}}}
    """

    def __init__(
        self,
        writer: MetricsWriter | None = None,
        reader: MetricsReader | None = None,
    ) -> None:
        """初始化健康检查器。

        Args:
            writer: MetricsWriter 实例（可选，用于检查 Redis 状态）。
            reader: MetricsReader 实例（可选，用于检查 VictoriaMetrics 状态）。
        """
        self._writer = writer
        self._reader = reader

    async def check(self) -> dict:
        """执行健康检查，返回结构化健康报告。

        检查 VictoriaMetrics（通过 reader 的 http client 发 GET 请求）和 Redis
        （通过 writer 的 cache client 发 PING）。任一组件不可用则 ok=False。
        当 writer/reader 为 None 时跳过该组件检查。

        Returns:
            {"ok": bool, "components": {}} — ok 为所有组件健康的 AND。
        """
        components: dict[str, dict] = {}

        # Check VictoriaMetrics via reader
        if self._reader is not None:
            vm_ok = False
            vm_error = None
            try:
                if self._reader._http is not None:
                    resp = await self._reader._http.get(
                        "/api/v1/query", params={"query": "up"}
                    )
                    vm_ok = resp.status_code == 200
                else:
                    vm_ok = False
                    vm_error = "reader not initialized"
            except Exception as e:
                vm_error = str(e)
            components["victoriametrics"] = {"ok": vm_ok}
            if vm_error:
                components["victoriametrics"]["error"] = vm_error

        # Check Redis via writer
        if self._writer is not None:
            redis_ok = False
            redis_error = None
            try:
                if self._writer._initialized and self._writer._cache is not None:
                    await self._writer.cache.client.ping()
                    redis_ok = True
                else:
                    redis_ok = False
                    redis_error = "writer not initialized"
            except Exception as e:
                redis_error = str(e)
            components["redis"] = {"ok": redis_ok}
            if redis_error:
                components["redis"]["error"] = redis_error

        overall_ok = (
            all(c.get("ok", False) for c in components.values())
            if components
            else True
        )
        return {"ok": overall_ok, "components": components}
