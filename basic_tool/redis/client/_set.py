"""
Set 操作 Mixin。

提供 Redis Set 类型的操作方法。
包括 sadd/srem/smembers/sismmember/smismember/scard/sinter/sunion/sdiff/srandmember。
"""

from typing import Set as TSet


class SetMixin:
    """
    Set 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def sadd(self, name: str, *values: str) -> int:
        """
        向集合中添加一个或多个成员。

        Args:
            name: set 的 key
            *values: 要添加的成员列表

        Returns:
            int: 实际新增的成员数（已存在的不计）
        """
        return await self.client.sadd(name, *values)

    async def srem(self, name: str, *values: str) -> int:
        """
        从集合中移除一个或多个成员。

        Args:
            name: set 的 key
            *values: 要移除的成员列表

        Returns:
            int: 实际移除的成员数
        """
        return await self.client.srem(name, *values)

    async def smembers(self, name: str) -> TSet[str]:
        """
        获取集合中的所有成员。

        Args:
            name: set 的 key

        Returns:
            set[str]: 所有成员的集合
        """
        return await self.client.smembers(name)

    async def sismember(self, name: str, value: str) -> bool:
        """
        检查成员是否在集合中。

        Args:
            name: set 的 key
            value: 要检查的成员

        Returns:
            bool: 成员存在返回 True
        """
        return await self.client.sismember(name, value)

    async def smismember(self, name: str, *values: str) -> list[bool]:
        """
        批量检查多个成员是否在集合中。

        Args:
            name: set 的 key
            *values: 要检查的成员列表

        Returns:
            list[bool]: 对应位置的成员是否存在
        """
        return await self.client.smismember(name, *values)

    async def scard(self, name: str) -> int:
        """
        获取集合的成员数量。

        Args:
            name: set 的 key

        Returns:
            int: 成员总数
        """
        return await self.client.scard(name)

    async def sinter(self, *names: str) -> TSet[str]:
        """
        获取多个集合的交集。

        Args:
            *names: set 的 key 列表

        Returns:
            set[str]: 交集成员
        """
        return await self.client.sinter(*names)

    async def sunion(self, *names: str) -> TSet[str]:
        """
        获取多个集合的并集。

        Args:
            *names: set 的 key 列表

        Returns:
            set[str]: 并集成员
        """
        return await self.client.sunion(*names)

    async def sdiff(self, *names: str) -> TSet[str]:
        """
        获取多个集合的差集（第一个集合相对于其他集合的差集）。

        Args:
            *names: set 的 key 列表

        Returns:
            set[str]: 差集成员
        """
        return await self.client.sdiff(*names)

    async def srandmember(self, name: str, count: int | None = None) -> str | list[str] | None:
        """
        随机获取集合中的一个或多个成员（不移除）。

        Args:
            name: set 的 key
            count: 获取数量。None 时返回单个成员，正数不重复，负数可重复

        Returns:
            str | list[str] | None: 随机成员，集合为空时返回 None
        """
        return await self.client.srandmember(name, count)
