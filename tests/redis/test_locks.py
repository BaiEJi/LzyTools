"""
DistributedLock 分布式锁测试。
"""

import pytest
import asyncio

from basic_tool.redis import DistributedLock


class TestDistributedLock:
    """DistributedLock 测试。"""

    async def test_get_lock_acquire_and_release(self, dist_lock):
        """通过 get_lock 获取独立 Lock 对象，手动获取和释放。"""
        lk = dist_lock.get_lock("test:1")
        acquired = await lk.acquire(timeout=10, retry_count=0)
        assert acquired is True
        released = await lk.release()
        assert released is True

    async def test_acquire_fails_when_held(self, dist_lock):
        """同一 key 被持有时，另一个 Lock 获取失败。"""
        lk1 = dist_lock.get_lock("test:2")
        acquired = await lk1.acquire(timeout=10, retry_count=0)
        assert acquired is True

        lk2 = dist_lock.get_lock("test:2")
        acquired2 = await lk2.acquire(timeout=10, retry_count=0)
        assert acquired2 is False

        await lk1.release()

    async def test_context_manager(self, dist_lock):
        """async with 方式获取和释放锁。"""
        async with dist_lock.lock("test:3", timeout=10) as lk:
            val = await lk._cache.get("lock:test:3")
            assert val is not None

        val_after = await lk._cache.get("lock:test:3")
        assert val_after is None

    async def test_extend(self, dist_lock):
        """锁续期。"""
        lk = dist_lock.get_lock("test:4")
        acquired = await lk.acquire(timeout=10, retry_count=0)
        assert acquired is True
        extended = await lk.extend(60)
        assert extended is True
        await lk.release()

    async def test_release_without_acquire(self, dist_lock):
        """未获取锁时释放返回 False。"""
        lk = dist_lock.get_lock("test:5")
        released = await lk.release()
        assert released is False

    async def test_concurrent_different_keys(self, dist_lock):
        """不同 key 的锁互不干扰（并发安全）。"""
        lk1 = dist_lock.get_lock("test:a")
        lk2 = dist_lock.get_lock("test:b")

        acq1 = await lk1.acquire(timeout=10, retry_count=0)
        acq2 = await lk2.acquire(timeout=10, retry_count=0)

        assert acq1 is True
        assert acq2 is True

        # 释放 lk1 不影响 lk2
        await lk1.release()
        lk2_check = dist_lock.get_lock("test:b")
        # lk2 的 key 应该还存在
        val = await lk2._cache.get("lock:test:b")
        assert val is not None

        await lk2.release()

    async def test_context_manager_raises_on_failure(self, dist_lock):
        """获取锁失败时 async with 抛出 RuntimeError。"""
        # 先占住锁
        lk = dist_lock.get_lock("test:occupied")
        await lk.acquire(timeout=10, retry_count=0)

        with pytest.raises(RuntimeError, match="获取锁失败"):
            async with dist_lock.lock("test:occupied", timeout=1, retry_count=0):
                pass

        await lk.release()
