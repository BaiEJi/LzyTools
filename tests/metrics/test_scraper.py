"""
Scraper generate_exposition 便捷函数测试。
"""

from basic_tool.metrics.collector import MetricsCollector
from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.scraper import generate_exposition


class TestScraper:
    """generate_exposition 函数测试。"""

    def test_generate_exposition(self):
        """generate_exposition 应委托调用 collector.prometheus_exposition()。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), endpoint="http://localhost:9999"
        )
        collector.counter("test_metric", value=5)
        output = generate_exposition(collector)
        assert "test_metric" in output
        assert "5" in output

    def test_generate_exposition_empty(self):
        """空 collector 应返回仅换行符。"""
        collector = MetricsCollector(
            MetricsConfig(service_name="test"), endpoint="http://localhost:9999"
        )
        output = generate_exposition(collector)
        assert output == "\n"
