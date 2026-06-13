"""
MetricsConfig 配置测试。

覆盖默认值、自定义值、类型校验。
"""

import pytest
from pydantic import ValidationError

from basic_tool.metrics.config import MetricsConfig


class TestMetricsConfig:
    """MetricsConfig 配置测试。"""

    def test_defaults(self):
        """默认构造应返回所有预定义默认值。"""
        config = MetricsConfig()
        assert config.vm_url == "http://localhost:8428"
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.flush_interval == 5.0
        assert config.flush_batch_size == 1000
        assert config.stream_prefix == "metrics"
        assert config.stream_max_len == 100_000
        assert config.alert_interval == 30.0

    def test_custom_values(self):
        """传入自定义值应覆盖对应默认值。"""
        config = MetricsConfig(
            vm_url="http://vm:8428",
            service_name="agent",
            flush_interval=10.0,
        )
        assert config.vm_url == "http://vm:8428"
        assert config.service_name == "agent"
        assert config.flush_interval == 10.0

    def test_invalid_type(self):
        """非法类型应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            MetricsConfig(flush_interval="not_a_number")
