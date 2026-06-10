"""
Hash 操作 Mixin。

提供 Redis Hash 类型的操作方法。
包括 hget/hset/hgetall/hdel/hmget/hkeys/hvals/hlen/hexists/hincrby。
"""


class HashMixin:
    """
    Hash 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def hget(self, name: str, key: str) -> str | None:
        """
        获取 hash 中指定字段的值。

        Args:
            name: hash 的 key
            key: hash 中的字段名

        Returns:
            str | None: 字段值，不存在时返回 None
        """
        return await self.client.hget(name, key)

    async def hset(
        self, name: str, key: str | None = None, value: str | None = None, *, mapping: dict | None = None
    ) -> int:
        """
        设置 hash 中字段的值。

        支持两种用法:
        - hset("hash", "field", "value") — 设置单个字段
        - hset("hash", mapping={"f1": "v1", "f2": "v2"}) — 设置多个字段

        Args:
            name: hash 的 key
            key: hash 中的字段名（单字段模式）
            value: 要设置的值（单字段模式）
            mapping: 字段字典（多字段模式）

        Returns:
            int: 新增字段数（0 表示更新已有字段）
        """
        return await self.client.hset(name, key=key, value=value, mapping=mapping)

    async def hgetall(self, name: str) -> dict[str, str]:
        """
        获取 hash 中所有字段和值。

        Args:
            name: hash 的 key

        Returns:
            dict[str, str]: 所有字段和值的字典
        """
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """
        删除 hash 中的一个或多个字段。

        Args:
            name: hash 的 key
            *keys: 要删除的字段名列表

        Returns:
            int: 实际删除的字段数
        """
        return await self.client.hdel(name, *keys)

    async def hmget(self, name: str, *keys: str) -> list[str | None]:
        """
        批量获取 hash 中多个字段的值。

        Args:
            name: hash 的 key
            *keys: 要获取的字段名列表

        Returns:
            list[str | None]: 值列表，不存在的字段对应位置为 None
        """
        return await self.client.hmget(name, *keys)

    async def hkeys(self, name: str) -> list[str]:
        """
        获取 hash 中所有字段名。

        Args:
            name: hash 的 key

        Returns:
            list[str]: 所有字段名列表
        """
        return await self.client.hkeys(name)

    async def hvals(self, name: str) -> list[str]:
        """
        获取 hash 中所有字段的值。

        Args:
            name: hash 的 key

        Returns:
            list[str]: 所有值列表
        """
        return await self.client.hvals(name)

    async def hlen(self, name: str) -> int:
        """
        获取 hash 中字段的数量。

        Args:
            name: hash 的 key

        Returns:
            int: 字段数量
        """
        return await self.client.hlen(name)

    async def hexists(self, name: str, key: str) -> bool:
        """
        检查 hash 中指定字段是否存在。

        Args:
            name: hash 的 key
            key: hash 中的字段名

        Returns:
            bool: 字段存在返回 True
        """
        return await self.client.hexists(name, key)

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """
        将 hash 中指定字段的值递增。

        Args:
            name: hash 的 key
            key: hash 中的字段名
            amount: 递增量，默认 1

        Returns:
            int: 递增后的值
        """
        return await self.client.hincrby(name, key, amount)
