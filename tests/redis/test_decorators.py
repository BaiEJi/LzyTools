"""
缓存装饰器测试。
"""

import pytest
import asyncio
import time

from basic_tool.redis import Cache


class TestCached:
    """@cached 装饰器测试。"""

    async def test_caches_result(self, cache):
        call_count = 0

        from basic_tool.redis.decorators import cached

        @cached(prefix="test", ttl=60)
        async def get_data(c: Cache, key: str):
            nonlocal call_count
            call_count += 1
            return {"key": key, "call": call_count}

        result1 = await get_data(cache, key="abc")
        result2 = await get_data(cache, key="abc")

        assert result1 == {"key": "abc", "call": 1}
        assert result2 == {"key": "abc", "call": 1}
        assert call_count == 1

    async def test_different_args_different_cache(self, cache):
        call_count = 0

        from basic_tool.redis.decorators import cached

        @cached(prefix="test2", ttl=60)
        async def get_item(c: Cache, item_id: int):
            nonlocal call_count
            call_count += 1
            return {"id": item_id, "call": call_count}

        r1 = await get_item(cache, item_id=1)
        r2 = await get_item(cache, item_id=2)

        assert r1["call"] == 1
        assert r2["call"] == 2
        assert call_count == 2

    async def test_caches_none_value(self, cache):
        """None 返回值也应该被缓存。"""
        call_count = 0

        from basic_tool.redis.decorators import cached

        @cached(prefix="test_none", ttl=60)
        async def get_none(c: Cache, key: str):
            nonlocal call_count
            call_count += 1
            return None

        r1 = await get_none(cache, key="x")
        r2 = await get_none(cache, key="x")

        assert r1 is None
        assert r2 is None
        assert call_count == 1  # 第二次应该走缓存


class TestRateLimit:
    """@rate_limit 装饰器测试。"""

    async def test_allows_within_limit(self, cache):
        from basic_tool.redis.decorators import rate_limit

        call_count = 0

        @rate_limit(key="test:rl", max_requests=3, window=60, cache=cache)
        async def do_thing():
            nonlocal call_count
            call_count += 1
            return "ok"

        for _ in range(3):
            result = await do_thing()
            assert result == "ok"

        assert call_count == 3

    async def test_rejects_over_limit(self, cache):
        from basic_tool.redis.decorators import rate_limit, RateLimitError

        @rate_limit(key="test:rl2", max_requests=2, window=60, cache=cache)
        async def do_thing():
            return "ok"

        await do_thing()
        await do_thing()

        with pytest.raises(RateLimitError, match="请求频率超限"):
            await do_thing()

    async def test_dynamic_key(self, cache):
        """动态 key 限流：不同用户独立计数。"""
        from basic_tool.redis.decorators import rate_limit, RateLimitError

        @rate_limit(key="user:{user_id}", max_requests=1, window=60, cache=cache)
        async def do_action(user_id: str):
            return "ok"

        # user A 第一次
        assert await do_action(user_id="alice") == "ok"
        # user B 第一次（不同 key，不受 user A 影响）
        assert await do_action(user_id="bob") == "ok"
        # user A 第二次（超限）
        with pytest.raises(RateLimitError):
            await do_action(user_id="alice")

    async def test_rate_limit_error_attributes(self, cache):
        """RateLimitError 包含限流详情。"""
        from basic_tool.redis.decorators import rate_limit, RateLimitError

        @rate_limit(key="test:attr", max_requests=1, window=60, cache=cache)
        async def do_thing():
            return "ok"

        await do_thing()

        with pytest.raises(RateLimitError) as exc_info:
            await do_thing()

        assert exc_info.value.key == "test:attr"
        assert exc_info.value.max_requests == 1
        assert exc_info.value.window == 60


class TestSynchronized:
    """@synchronized 装饰器测试。"""

    async def test_executes_with_lock(self, cache):
        from basic_tool.redis.decorators import synchronized

        executed = False

        @synchronized(lock_key="test:sync:1", timeout=10, cache=cache)
        async def do_work():
            nonlocal executed
            executed = True
            return "done"

        result = await do_work()
        assert result == "done"
        assert executed is True

    async def test_key_formatting(self, cache):
        from basic_tool.redis.decorators import synchronized

        @synchronized(lock_key="import:{user_id}", timeout=10, cache=cache)
        async def import_data(user_id: int):
            return f"imported_{user_id}"

        result = await import_data(user_id=42)
        assert result == "imported_42"
