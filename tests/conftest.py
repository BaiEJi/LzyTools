"""
测试公共 fixtures。

为所有测试提供 fakeredis 异步客户端，避免依赖真实 Redis 服务。
"""

import pytest
import fakeredis.aioredis

from basic_tool.redis import Cache, RedisConfig, CacheHealth, DistributedLock


@pytest.fixture
async def cache():
    """创建基于 fakeredis 的 Cache 实例，自动初始化和关闭。"""
    config = RedisConfig(url="redis://localhost:6379/0")
    c = Cache(config)

    fake_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    c._client = fake_client
    c._pool = fake_client.connection_pool

    yield c

    await c.close()


@pytest.fixture
def health(cache):
    """CacheHealth 实例。"""
    return CacheHealth(cache)


@pytest.fixture
def dist_lock(cache):
    """DistributedLock 实例。"""
    return DistributedLock(cache)
