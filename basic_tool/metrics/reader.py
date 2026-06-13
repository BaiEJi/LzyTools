"""
Metrics 查询器。

提供基于 PromQL 的范围查询、瞬时查询、标签值查询能力。
底层通过 VictoriaMetrics HTTP API (/api/v1/query_range, /api/v1/query, /api/v1/label) 查询。
"""

import httpx
from loguru import logger

from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.models import QueryResult, TimeRange


class MetricsReader:
    """
    指标查询器，通过 VictoriaMetrics HTTP API 执行 PromQL 查询。

    支持三种查询模式：
    - ``query_range``: 范围查询，返回时间序列矩阵（matrix）
    - ``query_instant``: 瞬时查询，返回当前时刻的标量向量（vector）
    - ``label_values``: 标签值查询，返回指定 label 的所有可选值

    通过 ``init()`` 初始化 httpx 客户端，``close()`` 释放资源。

    使用示例::

        config = MetricsConfig(vm_url="http://vm:8428")
        reader = MetricsReader(config)
        await reader.init()

        results = await reader.query_range("up", TimeRange(
            start=datetime(2023, 11, 14),
            end=datetime(2023, 11, 15),
            step="1m",
        ))
        for r in results:
            print(r.metric, r.values)

        await reader.close()

    Attributes:
        _config: Metrics 配置实例。
        _http: httpx 异步客户端（init 后创建，复用连接）。
    """

    def __init__(self, config: MetricsConfig) -> None:
        """初始化查询器。

        Args:
            config: Metrics 配置实例。
        """
        self._config = config
        self._http: httpx.AsyncClient | None = None

    async def init(self) -> None:
        """初始化 httpx 异步客户端。

        创建指向 VictoriaMetrics 的 ``httpx.AsyncClient``，复用连接。
        """
        self._http = httpx.AsyncClient(base_url=self._config.vm_url)

    async def close(self) -> None:
        """关闭 httpx 客户端。

        幂等操作：多次调用安全，不会重复关闭已关闭的客户端。
        """
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取已初始化的 httpx 客户端。

        Returns:
            httpx.AsyncClient 实例。

        Raises:
            RuntimeError: 未调用 init() 就访问此属性时抛出。
        """
        if self._http is None:
            raise RuntimeError("MetricsReader 未初始化，请先调用 init()")
        return self._http

    async def query_range(
        self, query: str, time_range: TimeRange
    ) -> list[QueryResult]:
        """执行 PromQL 范围查询。

        向 ``GET /api/v1/query_range`` 发送请求，返回时间范围内的所有时间序列。
        响应中 ``data.result`` 是 matrix，每个元素包含 ``metric`` 和
        多个 ``values`` 数据点（格式为 ``[unix_timestamp, value]``）。

        Args:
            query: PromQL 查询表达式（如 ``up``、``rate(http_requests_total[5m])``）。
            time_range: 查询时间范围，包含起止时间和步长。

        Returns:
            查询结果列表，每个 ``QueryResult`` 对应一条时间序列。

        Raises:
            httpx.HTTPStatusError: 远端返回非 2xx 状态码时抛出。
        """
        params = {
            "query": query,
            "start": time_range.start.timestamp(),
            "end": time_range.end.timestamp(),
            "step": time_range.step,
        }
        resp = await self.client.get("/api/v1/query_range", params=params)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", {}).get("result", []):
            results.append(
                QueryResult(
                    metric=item.get("metric", {}),
                    values=item.get("values", []),
                )
            )
        logger.info("范围查询完成 | query={} count={}", query, len(results))
        return results

    async def query_instant(self, query: str) -> list[QueryResult]:
        """执行 PromQL 瞬时查询。

        向 ``GET /api/v1/query`` 发送请求，返回当前时刻的向量结果。
        响应中 ``data.result`` 是 vector，每个元素包含 ``metric`` 和单个
        ``value`` 数据点（格式为 ``[unix_timestamp, value]``）。
        本方法将单个 ``value`` 包装为单元素 ``values`` 列表，统一为
        ``QueryResult`` 结构。

        Args:
            query: PromQL 查询表达式。

        Returns:
            查询结果列表，每个 ``QueryResult.values`` 恰好包含 1 个数据点。

        Raises:
            httpx.HTTPStatusError: 远端返回非 2xx 状态码时抛出。
        """
        params = {"query": query, "time": "now"}
        resp = await self.client.get("/api/v1/query", params=params)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", {}).get("result", []):
            values = (
                [item["value"]] if "value" in item else item.get("values", [])
            )
            results.append(
                QueryResult(metric=item.get("metric", {}), values=values)
            )
        logger.info("瞬时查询完成 | query={} count={}", query, len(results))
        return results

    async def label_values(self, label: str) -> list[str]:
        """查询指定 label 的所有可选值。

        向 ``GET /api/v1/label/{label}/values`` 发送请求，返回该 label 在
        所有时间序列中出现过的取值列表。常用于发现可用指标名
        （``label="__name__"``）或实例列表。

        Args:
            label: 标签名（如 ``__name__``、``instance``、``job``）。

        Returns:
            该标签的所有可选值字符串列表。

        Raises:
            httpx.HTTPStatusError: 远端返回非 2xx 状态码时抛出。
        """
        resp = await self.client.get(f"/api/v1/label/{label}/values")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
