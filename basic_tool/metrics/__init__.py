"""
Metrics 子模块：指标采集、Redis Streams 缓冲、VictoriaMetrics 持久化、PromQL 查询、告警评估、健康检查。

提供完整的指标可观测性能力：
- MetricsCollector：内存采集器，支持 counter/gauge/histogram + Prometheus exposition 输出
- MetricsWriter：双写 Redis Streams（缓冲）和 VictoriaMetrics（持久化）
- MetricsReader：PromQL 范围查询、瞬时查询、标签值查询
- AlertEvaluator：告警状态机（OK → PENDING → FIRING → OK），支持冷却
- MetricsHealth：VictoriaMetrics + Redis 连接健康检查

使用方式::

    from basic_tool.metrics import MetricsCollector, MetricsConfig

    collector = MetricsCollector(
        MetricsConfig(service_name="my_app"),
        endpoint="http://vm:8428/api/v1/import/prometheus",
    )
    await collector.init()
    collector.counter("http_requests_total", labels={"method": "GET"})
    collector.gauge("queue_depth", 42)
    text = collector.prometheus_exposition()
    await collector.close()
"""

from basic_tool.metrics.alerter import AlertEvaluator
from basic_tool.metrics.collector import MetricsCollector
from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.health import MetricsHealth
from basic_tool.metrics.models import (
    AlertEvent,
    AlertRule,
    AlertState,
    MetricBatch,
    MetricPoint,
    MetricType,
    QueryResult,
    TimeRange,
)
from basic_tool.metrics.reader import MetricsReader
from basic_tool.metrics.writer import MetricsWriter

__all__ = [
    "MetricsCollector",
    "MetricsConfig",
    "MetricsWriter",
    "MetricsReader",
    "AlertEvaluator",
    "MetricsHealth",
    "MetricPoint",
    "MetricBatch",
    "MetricType",
    "TimeRange",
    "QueryResult",
    "AlertRule",
    "AlertState",
    "AlertEvent",
]
