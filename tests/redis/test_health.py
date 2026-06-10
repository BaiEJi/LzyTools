"""
CacheHealth 健康检查测试。
"""

import pytest


class TestCacheHealth:
    """CacheHealth 测试。"""

    def test_pool_stats_ok(self, health):
        stats = health.pool_stats()
        assert stats["status"] == "ok"
        assert stats["max"] == 50
        assert "created" in stats
        assert "in_use" in stats
        assert "idle" in stats

    async def test_check_ok(self, health):
        result = await health.check()
        assert result["ok"] is True
        assert result["ping_ms"] >= 0
        assert result["error"] is None
        assert result["pool"]["status"] == "ok"

    def test_pool_stats_not_initialized(self):
        """未初始化时应返回 not_initialized 状态。"""
        from basic_tool.redis import Cache, RedisConfig, CacheHealth

        c = Cache(RedisConfig(url="redis://localhost:6379/0"))
        h = CacheHealth(c)
        stats = h.pool_stats()
        assert stats["status"] == "not_initialized"
        assert stats["created"] == 0
