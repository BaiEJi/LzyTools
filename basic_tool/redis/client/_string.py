"""
String 操作 Mixin。

提供 Redis String 类型的全部操作方法。
包括 get/set/delete/incr/decr/mget/mset 等。
"""

from typing import Any


class StringMixin:
    """
    String 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def get(self, key: str) -> str | None:
        """
        获取 key 的值。

        Args:
            key: Redis key

        Returns:
            str | None: key 对应的值，不存在时返回 None
        """
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool | None:
        """
        设置 key 的值。

        Args:
            key: Redis key
            value: 要设置的值
            ex: 过期时间（秒）
            px: 过期时间（毫秒），与 ex 互斥
            nx: 仅当 key 不存在时设置
            xx: 仅当 key 已存在时设置

        Returns:
            bool | None: 设置成功返回 True；nx/xx 模式下未设置返回 None
        """
        return await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)

    async def delete(self, *keys: str) -> int:
        """
        删除一个或多个 key。

        Args:
            *keys: 要删除的 key 列表

        Returns:
            int: 实际删除的 key 数量
        """
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """
        检查 key 是否存在。

        Args:
            *keys: 要检查的 key 列表

        Returns:
            int: 存在的 key 数量
        """
        return await self.client.exists(*keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置 key 的过期时间。

        Args:
            key: Redis key
            seconds: 过期秒数

        Returns:
            bool: 设置成功返回 True，key 不存在返回 False
        """
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """
        获取 key 的剩余过期时间。

        Args:
            key: Redis key

        Returns:
            int: 剩余秒数，-1 表示永不过期，-2 表示 key 不存在
        """
        return await self.client.ttl(key)

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        将 key 的值递增。

        Args:
            key: Redis key
            amount: 递增量，默认 1

        Returns:
            int: 递增后的值
        """
        return await self.client.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        将 key 的值递减。

        Args:
            key: Redis key
            amount: 递减量，默认 1

        Returns:
            int: 递减后的值
        """
        return await self.client.decr(key, amount)

    async def mget(self, *keys: str) -> list[str | None]:
        """
        批量获取多个 key 的值。

        Args:
            *keys: 要获取的 key 列表

        Returns:
            list[str | None]: 值列表，不存在的 key 对应位置为 None
        """
        return await self.client.mget(*keys)

    async def mset(self, mapping: dict[str, str]) -> bool:
        """
        批量设置多个 key-value 对。

        Args:
            mapping: key-value 字典

        Returns:
            bool: 始终返回 True
        """
        return await self.client.mset(mapping)

    async def scan(
        self,
        cursor: int = 0,
        *,
        match: str | None = None,
        count: int = 100,
    ) -> tuple[int, list[str]]:
        """
        增量迭代 key（不阻塞 Redis）。

        Args:
            cursor: 迭代游标，首次调用传 0
            match: key 匹配模式，如 "user:*"
            count: 每次迭代建议返回的数量（实际数量可能不同）

        Returns:
            tuple[int, list[str]]: (下一次的游标, 本次匹配到的 key 列表)
                游标为 0 表示迭代结束
        """
        return await self.client.scan(cursor, match=match, count=count)

    async def scan_iter(self, match: str | None = None, count: int = 100):
        """
        异步迭代器，自动处理 cursor 循环。

        Args:
            match: key 匹配模式，如 "user:*"
            count: 每次迭代建议返回的数量

        Yields:
            str: 匹配到的 key

        用法:
            async for key in cache.scan_iter(match="user:*"):
                print(key)
        """
        cursor = 0
        while True:
            cursor, keys = await self.scan(cursor, match=match, count=count)
            for key in keys:
                yield key
            if cursor == 0:
                break

    async def append(self, key: str, value: str) -> int:
        """
        将值追加到 key 的末尾。key 不存在时先创建。

        Args:
            key: Redis key
            value: 要追加的值

        Returns:
            int: 追加后字符串的总长度
        """
        return await self.client.append(key, value)

    async def strlen(self, key: str) -> int:
        """
        获取 key 对应字符串的长度。

        Args:
            key: Redis key

        Returns:
            int: 字符串长度，key 不存在时返回 0
        """
        return await self.client.strlen(key)

    async def getdel(self, key: str) -> str | None:
        """
        获取 key 的值并删除 key。

        Args:
            key: Redis key

        Returns:
            str | None: key 的值，不存在时返回 None
        """
        return await self.client.getdel(key)

    async def getex(self, key: str, *, ex: int | None = None, px: int | None = None) -> str | None:
        """
        获取 key 的值并可选地设置过期时间。

        Args:
            key: Redis key
            ex: 过期时间（秒）
            px: 过期时间（毫秒）

        Returns:
            str | None: key 的值，不存在时返回 None
        """
        return await self.client.getex(key, ex=ex, px=px)

    async def pttl(self, key: str) -> int:
        """
        获取 key 的剩余过期时间（毫秒）。

        Args:
            key: Redis key

        Returns:
            int: 剩余毫秒数，-1 表示永不过期，-2 表示 key 不存在
        """
        return await self.client.pttl(key)

    async def persist(self, key: str) -> bool:
        """
        移除 key 的过期时间，使其永不过期。

        Args:
            key: Redis key

        Returns:
            bool: 成功移除返回 True，key 不存在或无过期时间返回 False
        """
        return await self.client.persist(key)

    async def pexpire(self, key: str, milliseconds: int) -> bool:
        """
        设置 key 的过期时间（毫秒）。

        Args:
            key: Redis key
            milliseconds: 过期毫秒数

        Returns:
            bool: 设置成功返回 True，key 不存在返回 False
        """
        return await self.client.pexpire(key, milliseconds)

    async def type(self, key: str) -> str:
        """
        获取 key 的数据类型。

        Args:
            key: Redis key

        Returns:
            str: 类型名称（string/list/set/zset/hash/none）
        """
        return await self.client.type(key)
