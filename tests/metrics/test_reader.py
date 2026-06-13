"""MetricsReader 查询器测试。

覆盖 query_range 范围查询、query_instant 瞬时查询、label_values 标签值查询，
以及未初始化访问 client 的错误处理。使用 httpx.MockTransport 模拟 VictoriaMetrics 响应。
"""

from datetime import datetime

import httpx
import pytest

from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.models import QueryResult, TimeRange
from basic_tool.metrics.reader import MetricsReader


class TestMetricsReader:
    """MetricsReader 查询器测试。"""

    async def test_query_range(self):
        """query_range 应解析 VictoriaMetrics matrix 响应为 QueryResult 列表。"""

        def handler(req):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "resultType": "matrix",
                        "result": [
                            {
                                "metric": {"__name__": "up"},
                                "values": [
                                    [1700000000, "1"],
                                    [1700000060, "1"],
                                ],
                            }
                        ],
                    },
                },
            )

        transport = httpx.MockTransport(handler)
        reader = MetricsReader(MetricsConfig())
        reader._http = httpx.AsyncClient(
            transport=transport, base_url="http://localhost:8428"
        )

        results = await reader.query_range(
            "up",
            TimeRange(
                start=datetime(2023, 11, 14),
                end=datetime(2023, 11, 15),
                step="1m",
            ),
        )

        assert len(results) > 0
        assert isinstance(results[0], QueryResult)
        assert results[0].metric["__name__"] == "up"

        await reader.close()

    async def test_query_instant(self):
        """query_instant 应解析 vector 响应并将单个 value 包装为单元素 values。"""

        def handler(req):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {"__name__": "up"},
                                "value": [1700000000, "1"],
                            }
                        ],
                    },
                },
            )

        transport = httpx.MockTransport(handler)
        reader = MetricsReader(MetricsConfig())
        reader._http = httpx.AsyncClient(
            transport=transport, base_url="http://localhost:8428"
        )

        results = await reader.query_instant("up")

        assert len(results) > 0
        assert len(results[0].values) == 1

        await reader.close()

    async def test_label_values(self):
        """label_values 应返回 label 的所有可选值列表。"""

        def handler(req):
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": ["up", "go_goroutines", "cpu_usage"],
                },
            )

        transport = httpx.MockTransport(handler)
        reader = MetricsReader(MetricsConfig())
        reader._http = httpx.AsyncClient(
            transport=transport, base_url="http://localhost:8428"
        )

        values = await reader.label_values("__name__")

        assert "up" in values

        await reader.close()

    def test_not_initialized_raises(self):
        """未调用 init() 访问 client 应抛出 RuntimeError。"""
        reader = MetricsReader(MetricsConfig())

        with pytest.raises(RuntimeError, match="未初始化"):
            _ = reader.client
