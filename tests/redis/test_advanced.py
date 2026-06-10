"""
Lua 脚本、原始命令、Sorted Set、Pub/Sub 测试。
"""

import pytest


class TestSortedSet:
    """Sorted Set 操作测试。"""

    async def test_zadd_zrange(self, cache):
        added = await cache.zadd("scores", {"alice": 90, "bob": 85, "carol": 95})
        assert added == 3

        members = await cache.zrange("scores", 0, -1, withscores=True)
        assert members == [("bob", 85.0), ("alice", 90.0), ("carol", 95.0)]

    async def test_zrange_desc(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85, "carol": 95})
        members = await cache.zrange("scores", 0, -1, desc=True)
        assert members == ["carol", "alice", "bob"]

    async def test_zrangebyscore(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85, "carol": 95})
        members = await cache.zrangebyscore("scores", 85, 90)
        assert members == ["bob", "alice"]

    async def test_zrem(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85})
        removed = await cache.zrem("scores", "alice")
        assert removed == 1
        members = await cache.zrange("scores", 0, -1)
        assert members == ["bob"]

    async def test_zcard(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85})
        assert await cache.zcard("scores") == 2

    async def test_zscore(self, cache):
        await cache.zadd("scores", {"alice": 90})
        assert await cache.zscore("scores", "alice") == 90.0
        assert await cache.zscore("scores", "missing") is None

    async def test_zrank(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85, "carol": 95})
        assert await cache.zrank("scores", "bob") == 0
        assert await cache.zrank("scores", "carol") == 2

    async def test_zremrangebyscore(self, cache):
        await cache.zadd("scores", {"alice": 90, "bob": 85, "carol": 95})
        removed = await cache.zremrangebyscore("scores", 80, 90)
        assert removed == 2
        members = await cache.zrange("scores", 0, -1)
        assert members == ["carol"]

    async def test_zadd_nx_xx(self, cache):
        await cache.zadd("scores", {"alice": 90})
        added = await cache.zadd("scores", {"alice": 100}, nx=True)
        assert added == 0
        assert await cache.zscore("scores", "alice") == 90.0

        added = await cache.zadd("scores", {"alice": 100}, xx=True)
        assert added == 0
        assert await cache.zscore("scores", "alice") == 100.0


class TestLuaScript:
    """Lua 脚本测试。"""

    async def test_eval(self, cache):
        result = await cache.eval("return 1 + 1", 0)
        assert result == 2

    async def test_eval_with_keys(self, cache):
        await cache.set("mykey", "hello")
        result = await cache.eval(
            'return redis.call("get", KEYS[1])',
            1, "mykey"
        )
        assert result == "hello"

    async def test_eval_with_args(self, cache):
        result = await cache.eval(
            "return ARGV[1] .. ' ' .. ARGV[2]",
            0, "hello", "world"
        )
        assert result == "hello world"

    async def test_eval_atomic_compare_and_delete(self, cache):
        await cache.set("lock:1", "token_abc")
        result = await cache.eval(
            'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end',
            1, "lock:1", "token_abc"
        )
        assert result == 1
        assert await cache.get("lock:1") is None

    async def test_eval_wrong_token(self, cache):
        await cache.set("lock:2", "token_abc")
        result = await cache.eval(
            'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end',
            1, "lock:2", "wrong_token"
        )
        assert result == 0
        assert await cache.get("lock:2") == "token_abc"

    async def test_register_script(self, cache):
        await cache.set("counter", "10")
        incr_by = cache.register_script(
            'local v = tonumber(redis.call("get", KEYS[1])) + tonumber(ARGV[1]); '
            'redis.call("set", KEYS[1], tostring(v)); '
            'return v'
        )
        result = await incr_by(keys=["counter"], args=["5"])
        assert result == 15

        result = await incr_by(keys=["counter"], args=["3"])
        assert result == 18

    async def test_evalsha(self, cache):
        sha = await cache.client.script_load("return ARGV[1] * 2")
        result = await cache.evalsha(sha, 0, "21")
        assert result == 42


class TestExecuteCommand:
    """原始命令执行测试。"""

    async def test_execute_set_get(self, cache):
        await cache.execute_command("SET", "raw_key", "raw_val")
        result = await cache.execute_command("GET", "raw_key")
        assert result == "raw_val"

    async def test_execute_incr(self, cache):
        await cache.execute_command("SET", "raw_counter", "0")
        result = await cache.execute_command("INCRBY", "raw_counter", "7")
        assert result == 7

    async def test_execute_del(self, cache):
        await cache.set("raw_del", "val")
        result = await cache.execute_command("DEL", "raw_del")
        assert result == 1

    async def test_execute_hset_hgetall(self, cache):
        await cache.execute_command("HSET", "raw_hash", "f1", "v1", "f2", "v2")
        result = await cache.execute_command("HGETALL", "raw_hash")
        assert result == {"f1": "v1", "f2": "v2"}


class TestPubSub:
    """Pub/Sub 测试。"""

    async def test_publish_returns_subscriber_count(self, cache):
        count = await cache.publish("test_channel", "hello")
        assert count == 0

    async def test_subscribe_and_publish(self, cache):
        ps = await cache.subscribe("events")
        try:
            await cache.publish("events", "ping")
            msg = await ps.get_message(timeout=1.0)
            assert msg is not None
            assert msg["type"] == "subscribe"
            msg = await ps.get_message(timeout=1.0)
            assert msg is not None
            assert msg["type"] == "message"
            assert msg["data"] == "ping"
        finally:
            await ps.unsubscribe()
            await ps.aclose()

    async def test_psubscribe_pattern(self, cache):
        ps = await cache.psubscribe("user:*")
        try:
            await cache.publish("user:123", "login")
            msg = await ps.get_message(timeout=1.0)
            assert msg is not None
            assert msg["type"] == "psubscribe"
            msg = await ps.get_message(timeout=1.0)
            assert msg is not None
            assert msg["type"] == "pmessage"
            assert msg["data"] == "login"
        finally:
            await ps.punsubscribe()
            await ps.aclose()
