"""
Redis 分布式锁模块。

基于 Redis SET NX EX 实现分布式锁，支持:
- 原子获取/释放锁
- 自动过期防死锁
- 上下文管理器（async with）
- 锁续期
- 并发安全（每个锁独立状态，不在实例上共享）

核心组件:
- DistributedLock: 锁工厂，通过 lock(key) 返回独立的 Lock 对象
- Lock: 单个锁实例，持有独立的 token 和 key

使用方式:
    dist_lock = DistributedLock(cache)

    # 上下文管理器方式（推荐）
    async with dist_lock.lock("order:123"):
        ...

    # 手动控制方式
    lk = dist_lock.get_lock("order:123")
    acquired = await lk.acquire(timeout=60)
    if acquired:
        try:
            ...
        finally:
            await lk.release()
"""

import asyncio
import uuid

from loguru import logger

from basic_tool.redis.client import Cache

_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

_EXTEND_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class Lock:
    """
    单个分布式锁实例。

    每个 Lock 对象持有独立的 token 和 key，可在并发场景下安全使用。
    不直接创建，通过 DistributedLock.get_lock() 或 DistributedLock.lock() 获取。
    """

    def __init__(self, cache: Cache, key: str) -> None:
        """
        初始化锁实例。

        Args:
            cache: 已初始化的 Cache 实例
            key: 锁的完整 Redis key（已含 lock: 前缀）
        """
        self._cache = cache
        self._key = key
        self._token: str | None = None

    async def acquire(
        self,
        *,
        timeout: int = 30,
        retry_interval: float = 0.1,
        retry_count: int = 50,
    ) -> bool:
        """
        获取分布式锁。

        使用 SET NX EX 原子操作获取锁，失败时按指定策略重试。
        每次获取锁时生成唯一 token，用于安全释放（防止误删他人的锁）。

        Args:
            timeout: 锁自动过期秒数，防止死锁
            retry_interval: 重试间隔秒数
            retry_count: 最大重试次数

        Returns:
            bool: 是否成功获取锁
        """
        token = str(uuid.uuid4())

        for i in range(retry_count + 1):
            result = await self._cache.client.set(
                self._key, token, nx=True, ex=timeout
            )
            if result:
                self._token = token
                logger.debug("获取锁成功 | key={}", self._key)
                return True

            if i < retry_count:
                await asyncio.sleep(retry_interval)

        logger.warning("获取锁超时 | key={} retries={}", self._key, retry_count)
        return False

    async def release(self) -> bool:
        """
        释放分布式锁。

        使用 Lua 脚本保证原子性：
        只有当 key 的值等于当前持锁者的 token 时才删除。
        防止误删其他进程已获取的锁。

        Returns:
            bool: 是否成功释放（锁不存在或 token 不匹配时返回 False）
        """
        if self._token is None:
            return False

        result = await self._cache.client.eval(
            _RELEASE_LUA, 1, self._key, self._token
        )
        released = result == 1

        if released:
            logger.debug("释放锁成功 | key={}", self._key)
        else:
            logger.warning(
                "释放锁失败（锁已过期或被他人持有） | key={}", self._key
            )

        self._token = None
        return released

    async def extend(self, timeout: int) -> bool:
        """
        续期锁（重置 TTL）。

        使用 Lua 脚本保证原子性：
        只有当 key 的值等于当前持锁者的 token 时才续期。

        Args:
            timeout: 新的 TTL 秒数（绝对值，不是增量）

        Returns:
            bool: 是否成功续期
        """
        if self._token is None:
            return False

        result = await self._cache.client.eval(
            _EXTEND_LUA, 1, self._key, self._token, str(timeout)
        )
        return result == 1


class DistributedLock:
    """
    分布式锁工厂。

    通过 lock(key) 返回独立的 Lock 对象，每个 Lock 持有独立状态，
    可在并发场景下安全使用（不同 key 的锁互不干扰）。

    用法:
        dist_lock = DistributedLock(cache)

        async with dist_lock.lock("resource:123"):
            # 临界区逻辑
            pass
    """

    def __init__(self, cache: Cache) -> None:
        """
        初始化分布式锁工厂。

        Args:
            cache: 已初始化的 Cache 实例
        """
        self._cache = cache

    def get_lock(self, key: str) -> Lock:
        """
        获取一个独立的 Lock 对象（不自动获取锁）。

        Args:
            key: 锁的标识，建议加前缀如 "lock:order:123"

        Returns:
            Lock: 独立的锁实例
        """
        return Lock(self._cache, f"lock:{key}")

    def lock(
        self,
        key: str,
        *,
        timeout: int = 30,
        retry_interval: float = 0.1,
        retry_count: int = 50,
    ) -> "_LockContext":
        """
        返回一个异步上下文管理器，用于 async with 语法。

        Args:
            key: 锁的标识
            timeout: 锁自动过期秒数
            retry_interval: 重试间隔秒数
            retry_count: 最大重试次数

        Returns:
            _LockContext: 异步上下文管理器

        用法:
            async with dist_lock.lock("order:123", timeout=60):
                # 临界区逻辑
                pass
        """
        return _LockContext(self._cache, key, timeout, retry_interval, retry_count)


class _LockContext:
    """
    DistributedLock 的异步上下文管理器。

    不直接使用，通过 DistributedLock.lock() 获取实例。
    内部创建独立的 Lock 对象，确保并发安全。
    """

    def __init__(
        self,
        cache: Cache,
        key: str,
        timeout: int,
        retry_interval: float,
        retry_count: int,
    ) -> None:
        self._cache = cache
        self._key = key
        self._timeout = timeout
        self._retry_interval = retry_interval
        self._retry_count = retry_count
        self._lock: Lock | None = None

    async def __aenter__(self) -> Lock:
        """
        进入上下文时获取锁。

        Returns:
            Lock: 独立的锁实例

        Raises:
            RuntimeError: 获取锁失败时抛出
        """
        self._lock = Lock(self._cache, f"lock:{self._key}")
        acquired = await self._lock.acquire(
            timeout=self._timeout,
            retry_interval=self._retry_interval,
            retry_count=self._retry_count,
        )
        if not acquired:
            raise RuntimeError(f"获取锁失败 | key=lock:{self._key}")
        return self._lock

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文时释放锁。"""
        if self._lock is not None:
            await self._lock.release()
