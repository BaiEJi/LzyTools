"""MetricsHealth 健康检查测试。

覆盖全部组件健康、VictoriaMetrics 不可用、无组件三种场景。
使用 unittest.mock.AsyncMock / MagicMock 模拟 writer/reader 内部状态。
"""

from unittest.mock import AsyncMock, MagicMock

from basic_tool.metrics.health import MetricsHealth


class TestMetricsHealth:
    """MetricsHealth 健康检查测试。"""

    async def test_all_healthy(self):
        """当 writer 和 reader 均正常时，check() 应返回 ok=True 且两个组件均健康。"""
        # mock reader
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_reader = MagicMock()
        mock_reader._http = MagicMock()
        mock_reader._http.get = AsyncMock(return_value=mock_resp)
        # mock writer
        mock_cache = MagicMock()
        mock_cache.client.ping = AsyncMock(return_value=True)
        mock_writer = MagicMock()
        mock_writer._initialized = True
        mock_writer._cache = mock_cache
        mock_writer.cache = mock_cache  # property returns cache

        health = MetricsHealth(writer=mock_writer, reader=mock_reader)
        result = await health.check()

        assert result["ok"] is True
        assert result["components"]["victoriametrics"]["ok"] is True
        assert result["components"]["redis"]["ok"] is True

    async def test_vm_down(self):
        """当 reader 的 http 请求抛异常时，VictoriaMetrics 组件不可用，ok=False。"""
        # mock reader — http.get 抛异常
        mock_reader = MagicMock()
        mock_reader._http = MagicMock()
        mock_reader._http.get = AsyncMock(side_effect=Exception("connection refused"))
        # mock writer — 正常
        mock_cache = MagicMock()
        mock_cache.client.ping = AsyncMock(return_value=True)
        mock_writer = MagicMock()
        mock_writer._initialized = True
        mock_writer._cache = mock_cache
        mock_writer.cache = mock_cache

        health = MetricsHealth(writer=mock_writer, reader=mock_reader)
        result = await health.check()

        assert result["ok"] is False
        assert result["components"]["victoriametrics"]["ok"] is False

    async def test_no_components(self):
        """未传入 writer 和 reader 时，check() 应返回 ok=True 且 components 为空。"""
        health = MetricsHealth()
        result = await health.check()

        assert result["ok"] is True
        assert result["components"] == {}
