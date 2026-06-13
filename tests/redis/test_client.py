"""
Cache 客户端核心操作测试。

覆盖 String / Hash / Set / List / Scan / JSON / Pipeline 等全部 API。
"""

import pytest


class TestCacheLifecycle:
    """Cache 生命周期测试。"""

    async def test_client_property_raises_before_init(self):
        """未初始化时访问 client 应抛出 RuntimeError。"""
        from basic_tool.redis import Cache, RedisConfig

        c = Cache(RedisConfig(url="redis://localhost:6379/0"))
        with pytest.raises(RuntimeError, match="未初始化"):
            _ = c.client

    async def test_init_idempotent(self, cache):
        """重复调用 init() 不应报错。"""
        await cache.init()


class TestCacheLifecycleLogging:
    """Cache 生命周期日志测试。"""

    async def test_init_and_close_logging(self, monkeypatch):
        """init() 和 close() 应输出生命周期日志。"""
        import fakeredis.aioredis
        from loguru import logger
        from redis.asyncio import ConnectionPool

        from basic_tool.redis import Cache, RedisConfig

        logs: list[str] = []

        def _sink(message) -> None:
            logs.append(str(message))

        handler_id = logger.add(_sink, format="{message}", level="DEBUG")

        try:
            fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
            monkeypatch.setattr(
                ConnectionPool,
                "from_url",
                lambda *a, **kw: fake.connection_pool,
            )

            config = RedisConfig(
                url="redis://localhost:6379/0", max_connections=10
            )
            cache = Cache(config)
            await cache.init()

            log_text = "\n".join(logs)
            assert "Redis 连接池已创建" in log_text
            assert "Cache 初始化" in log_text
            assert "redis_url=redis://localhost:6379/0" in log_text
            assert "max_connections=10" in log_text

            await cache.close()

            log_text = "\n".join(logs)
            assert "Cache 已关闭" in log_text
        finally:
            logger.remove(handler_id)


class TestStringOps:
    """String 操作测试。"""

    async def test_set_and_get(self, cache):
        await cache.set("foo", "bar")
        assert await cache.get("foo") == "bar"

    async def test_get_nonexistent(self, cache):
        assert await cache.get("no_such_key") is None

    async def test_set_with_ex(self, cache):
        result = await cache.set("temp", "val", ex=60)
        assert result is True
        ttl = await cache.ttl("temp")
        assert 0 < ttl <= 60

    async def test_set_nx(self, cache):
        await cache.set("nx_key", "first", nx=True)
        result = await cache.set("nx_key", "second", nx=True)
        assert result is None
        assert await cache.get("nx_key") == "first"

    async def test_delete(self, cache):
        await cache.set("del_me", "val")
        deleted = await cache.delete("del_me")
        assert deleted == 1
        assert await cache.get("del_me") is None

    async def test_exists(self, cache):
        await cache.set("exist_key", "val")
        assert await cache.exists("exist_key") == 1
        assert await cache.exists("nope") == 0

    async def test_expire_and_ttl(self, cache):
        await cache.set("ttl_key", "val")
        assert await cache.expire("ttl_key", 100) is True
        ttl = await cache.ttl("ttl_key")
        assert 0 < ttl <= 100

    async def test_incr_decr(self, cache):
        assert await cache.incr("counter") == 1
        assert await cache.incr("counter", 5) == 6
        assert await cache.decr("counter", 2) == 4

    async def test_mget_mset(self, cache):
        await cache.mset({"a": "1", "b": "2", "c": "3"})
        result = await cache.mget("a", "b", "c", "missing")
        assert result == ["1", "2", "3", None]


class TestHashOps:
    """Hash 操作测试。"""

    async def test_hset_hget(self, cache):
        await cache.hset("user:1", "name", "Alice")
        assert await cache.hget("user:1", "name") == "Alice"
        assert await cache.hget("user:1", "missing") is None

    async def test_hgetall(self, cache):
        await cache.hset("user:2", "name", "Bob")
        await cache.hset("user:2", "age", "30")
        result = await cache.hgetall("user:2")
        assert result == {"name": "Bob", "age": "30"}

    async def test_hdel(self, cache):
        await cache.hset("user:3", "name", "Charlie")
        await cache.hset("user:3", "email", "c@test.com")
        deleted = await cache.hdel("user:3", "email")
        assert deleted == 1
        assert await cache.hget("user:3", "email") is None


class TestSetOps:
    """Set 操作测试。"""

    async def test_sadd_smembers_srem(self, cache):
        added = await cache.sadd("tags", "python", "redis", "python")
        assert added == 2

        members = await cache.smembers("tags")
        assert members == {"python", "redis"}

        removed = await cache.srem("tags", "redis")
        assert removed == 1
        assert await cache.smembers("tags") == {"python"}


class TestListOps:
    """List 操作测试。"""

    async def test_lpush_rpush_lrange(self, cache):
        await cache.rpush("queue", "a", "b", "c")
        assert await cache.lrange("queue", 0, -1) == ["a", "b", "c"]

        await cache.lpush("queue", "z")
        assert await cache.lrange("queue", 0, -1) == ["z", "a", "b", "c"]

    async def test_lpop_rpop(self, cache):
        await cache.rpush("q", "a", "b", "c")
        assert await cache.lpop("q") == "a"
        assert await cache.rpop("q") == "c"
        assert await cache.lrange("q", 0, -1) == ["b"]

    async def test_llen(self, cache):
        await cache.rpush("q", "a", "b", "c")
        assert await cache.llen("q") == 3

    async def test_lindex(self, cache):
        await cache.rpush("q", "a", "b", "c")
        assert await cache.lindex("q", 0) == "a"
        assert await cache.lindex("q", -1) == "c"
        assert await cache.lindex("q", 99) is None

    async def test_lset(self, cache):
        await cache.rpush("q", "a", "b", "c")
        await cache.lset("q", 1, "B")
        assert await cache.lrange("q", 0, -1) == ["a", "B", "c"]

    async def test_lrem(self, cache):
        await cache.rpush("q", "a", "b", "a", "c", "a")
        removed = await cache.lrem("q", 2, "a")
        assert removed == 2
        assert await cache.lrange("q", 0, -1) == ["b", "c", "a"]

    async def test_lmove(self, cache):
        await cache.rpush("src", "a", "b", "c")
        val = await cache.lmove("src", "dst", "LEFT", "RIGHT")
        assert val == "a"
        assert await cache.lrange("src", 0, -1) == ["b", "c"]
        assert await cache.lrange("dst", 0, -1) == ["a"]

    async def test_blpop_immediate(self, cache):
        await cache.rpush("q", "hello")
        result = await cache.blpop("q", timeout=1)
        assert result is not None
        assert result == ("q", "hello")

    async def test_blpop_empty_timeout(self, cache):
        result = await cache.blpop("empty_q", timeout=1)
        assert result is None

    async def test_brpop_immediate(self, cache):
        await cache.rpush("q", "world")
        result = await cache.brpop("q", timeout=1)
        assert result == ("q", "world")

    async def test_brpop_empty_timeout(self, cache):
        result = await cache.brpop("empty_q", timeout=1)
        assert result is None

    async def test_blmove_immediate(self, cache):
        pytest.skip("fakeredis 不支持 BLMOVE，需真实 Redis 环境")


class TestScanOps:
    """Scan 操作测试。"""

    async def test_scan(self, cache):
        await cache.mset({"user:1": "a", "user:2": "b", "post:1": "c"})

        all_keys = []
        cursor = 0
        while True:
            cursor, keys = await cache.scan(cursor, match="user:*", count=10)
            all_keys.extend(keys)
            if cursor == 0:
                break

        assert set(all_keys) == {"user:1", "user:2"}


class TestJsonOps:
    """JSON 序列化操作测试。"""

    async def test_set_json_get_json(self, cache):
        data = {"name": "Alice", "tags": [1, 2, 3]}
        await cache.set_json("json_key", data, ex=60)

        result = await cache.get_json("json_key")
        assert result == data

    async def test_get_json_nonexistent(self, cache):
        assert await cache.get_json("nope") is None


class TestPipeline:
    """Pipeline 操作测试。"""

    async def test_pipeline(self, cache):
        pipe = cache.pipeline()
        pipe.set("p1", "v1")
        pipe.set("p2", "v2")
        pipe.get("p1")
        results = await pipe.execute()

        assert results[0] is True
        assert results[1] is True
        assert results[2] == "v1"
