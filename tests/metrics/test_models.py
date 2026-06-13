"""
Metrics 数据模型测试。

覆盖 MetricPoint、MetricBatch、枚举、AlertRule、AlertEvent、TimeRange、QueryResult。
"""

from datetime import datetime

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


class TestMetricPoint:
    """MetricPoint 数据点测试。"""

    def test_creation_defaults(self):
        """使用必填字段构造时应返回默认类型、空标签和 None 时间戳。"""
        p = MetricPoint(name="test_metric", value=42.0)
        assert p.name == "test_metric"
        assert p.value == 42.0
        assert p.type == MetricType.GAUGE
        assert p.labels == {}
        assert p.timestamp is None

    def test_with_labels(self):
        """传入 type 和 labels 应正确覆盖默认值。"""
        p = MetricPoint(
            name="req",
            value=1.0,
            type=MetricType.COUNTER,
            labels={"method": "GET"},
        )
        assert p.labels == {"method": "GET"}
        assert p.type == MetricType.COUNTER

    def test_with_timestamp(self):
        """传入 timestamp 应正确保存。"""
        p = MetricPoint(name="ts", value=1.0, timestamp=datetime(2024, 1, 1))
        assert p.timestamp == datetime(2024, 1, 1)


class TestMetricBatch:
    """MetricBatch 批次测试。"""

    def test_creation(self):
        """构造带 source 的批次应正确保存点和来源。"""
        b = MetricBatch(
            points=[
                MetricPoint(name="a", value=1),
                MetricPoint(name="b", value=2),
            ],
            source="test",
        )
        assert len(b.points) == 2
        assert b.source == "test"

    def test_empty_points(self):
        """空点列表且未传 source 时应使用默认 unknown。"""
        b = MetricBatch(points=[])
        assert len(b.points) == 0
        assert b.source == "unknown"


class TestEnums:
    """枚举值测试。"""

    def test_metric_type_values(self):
        """MetricType 各成员值应符合预期。"""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"

    def test_alert_state_values(self):
        """AlertState 各成员值应符合预期。"""
        assert AlertState.OK.value == "ok"
        assert AlertState.PENDING.value == "pending"
        assert AlertState.FIRING.value == "firing"


class TestAlertRule:
    """AlertRule 告警规则测试。"""

    def test_defaults(self):
        """仅传必填字段时应使用默认 duration/cooldown/enabled/channels。"""
        r = AlertRule(name="high_cpu", metric="cpu_usage", condition="> 80")
        assert r.duration == "5m"
        assert r.cooldown == "10m"
        assert r.enabled is True
        assert r.channels == []

    def test_custom_values(self):
        """传入自定义 duration 和 cooldown 应正确覆盖。"""
        r = AlertRule(
            name="x",
            metric="y",
            condition="> 1",
            duration="1m",
            cooldown="2m",
        )
        assert r.duration == "1m"
        assert r.cooldown == "2m"


class TestAlertEvent:
    """AlertEvent 告警事件测试。"""

    def test_creation(self):
        """构造告警事件应正确保存字段，且时间戳默认为 None。"""
        e = AlertEvent(
            rule_name="r",
            state=AlertState.FIRING,
            value=95.0,
            threshold=80.0,
        )
        assert e.rule_name == "r"
        assert e.state == AlertState.FIRING
        assert e.value == 95.0
        assert e.threshold == 80.0
        assert e.fired_at is None
        assert e.resolved_at is None


class TestTimeRange:
    """TimeRange 查询时间范围测试。"""

    def test_creation(self):
        """构造时应正确保存 start/end 并使用默认 step。"""
        tr = TimeRange(start=datetime(2024, 1, 1), end=datetime(2024, 1, 2))
        assert tr.step == "1m"
        assert tr.start == datetime(2024, 1, 1)
        assert tr.end == datetime(2024, 1, 2)


class TestQueryResult:
    """QueryResult 查询结果测试。"""

    def test_creation(self):
        """构造应正确保存 metric 和 values 字段。"""
        qr = QueryResult(metric={"__name__": "up"}, values=[[1, "1"]])
        assert qr.metric == {"__name__": "up"}
        assert qr.values == [[1, "1"]]
