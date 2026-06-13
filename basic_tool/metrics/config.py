"""
Metrics 模块配置。

定义 VictoriaMetrics / Redis 连接地址、采集服务名、刷新参数等配置。
"""

from pydantic import BaseModel


class MetricsConfig(BaseModel):
    """
    Metrics 模块配置。

    Attributes:
        vm_url: VictoriaMetrics 写入/查询地址
        redis_url: Redis 连接地址（用于 Stream 缓冲）
        service_name: 当前服务名（作为指标 label）
        flush_interval: 自动刷新间隔（秒）
        flush_batch_size: 每批最大刷新点数
        stream_prefix: Redis Stream key 前缀
        stream_max_len: Redis Stream 最大长度
        alert_interval: 告警评估间隔（秒）
    """

    vm_url: str = "http://localhost:8428"
    redis_url: str = "redis://localhost:6379/0"
    service_name: str = "default"
    flush_interval: float = 5.0
    flush_batch_size: int = 1000
    stream_prefix: str = "metrics"
    stream_max_len: int = 100_000
    alert_interval: float = 30.0
