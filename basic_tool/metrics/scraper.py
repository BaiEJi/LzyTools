"""
Metrics Prometheus exposition 便捷函数。

提供 generate_exposition() 函数，委托给 MetricsCollector.prometheus_exposition()，
便于 Prometheus scraper 直接调用。
"""

from basic_tool.metrics.collector import MetricsCollector


def generate_exposition(collector: MetricsCollector) -> str:
    """生成 Prometheus exposition 格式文本。

    委托给 collector.prometheus_exposition()，返回当前缓冲区中所有指标的文本输出。
    适用于 Prometheus pull 模式抓取。

    Args:
        collector: MetricsCollector 实例。

    Returns:
        Prometheus text exposition 格式字符串。
    """
    return collector.prometheus_exposition()
