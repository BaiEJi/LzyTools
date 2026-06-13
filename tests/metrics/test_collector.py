"""MetricsCollector 采集器测试。

覆盖 counter/gauge/histogram 记录、Prometheus exposition 格式输出、
刷新成功/失败行为、init/close 生命周期。
"""

import asyncio
import subprocess

import httpx
import pytest

from basic_tool.metrics.collector import MetricsCollector
from basic_tool.metrics.config import MetricsConfig


def make_collector(transport_handler):
    """创建带 MockTransport 的采集器（不启动 flush loop）。

    Args:
        transport_handler: httpx.MockTransport 的请求处理函数。

    Returns:
        配置好 _http 的 MetricsCollector 实例。
    """
    transport = httpx.MockTransport(transport_handler)
    config = MetricsConfig(service_name="test")
    collector = MetricsCollector(config, endpoint="http://localhost:9999/ingest")
    collector._http = httpx.AsyncClient(transport=transport)
    return collector


class TestMetricsCollector:
    """MetricsCollector 采集器测试。"""

    def test_counter_gauge_histogram(self):
        """counter/gauge/histogram 应各自写入对应名称的缓冲区。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), "http://localhost:9999/ingest"
        )
        collector.counter("req_total", 1.0, {"method": "GET"})
        collector.gauge("queue_depth", 42)
        collector.histogram("latency_seconds", 0.5)

        assert len(collector._buffers["req_total"]) == 1
        assert len(collector._buffers["queue_depth"]) == 1
        assert len(collector._buffers["latency_seconds"]) == 1

    def test_prometheus_exposition(self):
        """Prometheus 格式应包含 HELP/TYPE 头和标签行。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), "http://localhost:9999/ingest"
        )
        collector.counter("http_requests_total", 1.0, {"method": "GET"})
        collector.counter("http_requests_total", 1.0, {"method": "POST"})
        collector.gauge("queue_depth", 42)

        output = collector.prometheus_exposition()
        assert "# HELP http_requests_total http_requests_total" in output
        assert "# TYPE http_requests_total counter" in output
        assert 'method="GET"' in output
        assert 'method="POST"' in output
        assert "queue_depth 42" in output

    def test_prometheus_exposition_empty(self):
        """空缓冲区应返回换行符。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), "http://localhost:9999/ingest"
        )
        assert collector.prometheus_exposition() == "\n"

    def test_prometheus_exposition_counter_aggregation(self):
        """相同标签的多个 counter 点应聚合成一行。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), "http://localhost:9999/ingest"
        )
        collector.counter("requests", 1.0, {"path": "/"})
        collector.counter("requests", 1.0, {"path": "/"})

        output = collector.prometheus_exposition()
        # 同标签集应只出现一行
        assert output.count('path="/"') == 1
        assert 'requests{path="/"}' in output

    def test_prometheus_exposition_no_labels(self):
        """无标签的指标应输出 name value 格式（无花括号）。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), "http://localhost:9999/ingest"
        )
        collector.gauge("temperature", 25)

        output = collector.prometheus_exposition()
        assert "temperature 25" in output

    def test_prometheus_exposition_no_eval(self):
        """collector.py 中不应包含 eval() 调用。"""
        result = subprocess.run(
            ["grep", "-c", "eval(", "basic_tool/metrics/collector.py"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "0"

    async def test_flush_failure_preserves_data(self):
        """刷新失败（远端 500）时应保留缓冲区数据。"""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        collector = make_collector(handler)
        collector.counter("test_metric", 1.0, {"env": "test"})
        try:
            await collector._do_flush()
        except Exception:
            pass
        assert len(collector._buffers["test_metric"]) > 0
        await collector.close()

    async def test_flush_success_clears_data(self):
        """刷新成功（远端 200）后应清空缓冲区。"""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        collector = make_collector(handler)
        collector.counter("test_metric", 1.0, {"env": "test"})
        await collector._do_flush()
        assert len(collector._buffers["test_metric"]) == 0
        await collector.close()

    async def test_init_creates_http_client(self):
        """init() 应创建 httpx 客户端并启动 flush 后台任务。"""
        config = MetricsConfig(service_name="test", flush_interval=999)
        collector = MetricsCollector(config, endpoint="http://localhost:9999/ingest")
        await collector.init()
        assert collector._http is not None
        await collector.close()
