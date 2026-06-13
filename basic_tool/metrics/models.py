"""
Metrics 数据模型。

定义指标点、批次、查询参数、查询结果、告警规则和告警事件等数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class MetricType(str, Enum):
    """指标类型枚举。"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class MetricPoint(BaseModel):
    """
    单个指标数据点。

    Attributes:
        name: 指标名称
        value: 指标值
        type: 指标类型，默认 GAUGE
        labels: 标签键值对，默认空字典
        timestamp: 时间戳，默认 None（写入时由后端补全）
    """
    name: str
    value: float
    type: MetricType = MetricType.GAUGE
    labels: dict[str, str] = {}
    timestamp: datetime | None = None


class MetricBatch(BaseModel):
    """
    一批指标数据点。

    Attributes:
        points: 数据点列表
        source: 数据来源标识
    """
    points: list[MetricPoint]
    source: str = "unknown"


class TimeRange(BaseModel):
    """
    查询时间范围。

    Attributes:
        start: 起始时间
        end: 结束时间
        step: 步长（PromQL 格式，如 "1m"）
    """
    start: datetime
    end: datetime
    step: str = "1m"


class QueryResult(BaseModel):
    """
    查询返回的单条结果。

    Attributes:
        metric: 指标名及标签（如 {"__name__": "up", "job": "node"}）
        values: 时间序列数据点列表，每项为 [timestamp, value]
    """
    metric: dict[str, str]
    values: list[list[Any]]


class AlertRule(BaseModel):
    """
    告警规则。

    Attributes:
        name: 规则名称
        metric: 监控的指标名
        condition: 触发条件（如 "> 80", "<= 0.1"）
        duration: 持续时间阈值（如 "5m"）
        cooldown: 冷却时间（避免重复告警，如 "10m"）
        enabled: 是否启用
        channels: 通知渠道列表
    """
    name: str
    metric: str
    condition: str
    duration: str = "5m"
    cooldown: str = "10m"
    enabled: bool = True
    channels: list[str] = []


class AlertState(str, Enum):
    """告警状态枚举。"""
    OK = "ok"
    PENDING = "pending"
    FIRING = "firing"


class AlertEvent(BaseModel):
    """
    告警事件。

    Attributes:
        rule_name: 触发的规则名
        state: 当前告警状态
        value: 触发时的指标值
        threshold: 规则阈值
        fired_at: 告警触发时间
        resolved_at: 告警恢复时间（未恢复时为 None）
    """
    rule_name: str
    state: AlertState
    value: float
    threshold: float
    fired_at: datetime | None = None
    resolved_at: datetime | None = None
