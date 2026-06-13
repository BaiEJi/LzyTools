"""MetricsWriter 写入器测试。

覆盖 write_batch 写入 Redis Stream、flush_to_vm 刷新到 VictoriaMetrics、
以及 init/close 生命周期管理。
"""

import httpx

from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.models import MetricBatch, MetricPoint, MetricType
from basic_tool.metrics.writer import MetricsWriter


class TestMetricsWriter:
    """MetricsWriter 写入器测试。"""

    async def test_write_batch(self, cache):
        """write_batch 应将指标点写入 Redis Stream 并返回写入数量。"""
        writer = MetricsWriter(MetricsConfig(), cache=cache)
        await writer.init()

        batch = MetricBatch(
            points=[MetricPoint(name="cpu", value=80.5)], source="test_svc"
        )
        count = await writer.write_batch(batch)

        assert count == 1
        entries = await cache.client.xrange("metrics:test_svc")
        assert len(entries) == 1

        await writer.close()

    async def test_write_batch_empty(self, cache):
        """空批次的 write_batch 应返回 0 且不写入任何数据。"""
        writer = MetricsWriter(MetricsConfig(), cache=cache)
        await writer.init()

        batch = MetricBatch(points=[], source="test")
        count = await writer.write_batch(batch)

        assert count == 0

        await writer.close()

    async def test_flush_to_vm(self):
        """flush_to_vm 应以 Prometheus 格式将指标 POST 到 VictoriaMetrics。"""
        captured = {}

        def handler(req):
            captured["body"] = req.content
            return httpx.Response(204)

        transport = httpx.MockTransport(handler)
        writer = MetricsWriter(MetricsConfig())
        writer._http = httpx.AsyncClient(base_url="http://test", transport=transport)

        batch = MetricBatch(
            points=[
                MetricPoint(
                    name="req",
                    value=100,
                    labels={"method": "GET"},
                    type=MetricType.COUNTER,
                )
            ],
            source="test",
        )
        count = await writer.flush_to_vm(batch)

        assert count == 1
        assert b"req" in captured["body"]
        assert b"100" in captured["body"]

        await writer.close()

    async def test_flush_to_vm_client_reuse(self):
        """init() 应创建复用的 httpx 客户端，close() 应安全关闭。"""
        writer = MetricsWriter(MetricsConfig())
        await writer.init()

        assert writer._http is not None

        await writer.close()
