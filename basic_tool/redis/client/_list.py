"""
List 操作 Mixin。

提供 Redis List 类型的全部操作方法，包括：
- 基本操作: lpush/rpush/lpop/rpop/lrange/llen/lindex/lset/lrem
- 阻塞操作: blpop/brpop/blmove
- 移动操作: lmove
"""

from typing import Any


class ListMixin:
    """
    List 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def lpush(self, name: str, *values: str) -> int:
        """
        从左侧插入一个或多个值到列表。

        Args:
            name: list 的 key
            *values: 要插入的值列表

        Returns:
            int: 插入后列表的长度
        """
        return await self.client.lpush(name, *values)

    async def rpush(self, name: str, *values: str) -> int:
        """
        从右侧插入一个或多个值到列表。

        Args:
            name: list 的 key
            *values: 要插入的值列表

        Returns:
            int: 插入后列表的长度
        """
        return await self.client.rpush(name, *values)

    async def lpop(self, name: str, count: int | None = None) -> str | list[str] | None:
        """
        从左侧弹出一个或多个元素。

        Args:
            name: list 的 key
            count: 弹出数量，None 时弹出一个（返回 str），指定时返回 list

        Returns:
            str | list[str] | None: 弹出的元素，列表为空时返回 None
        """
        return await self.client.lpop(name, count)

    async def rpop(self, name: str, count: int | None = None) -> str | list[str] | None:
        """
        从右侧弹出一个或多个元素。

        Args:
            name: list 的 key
            count: 弹出数量，None 时弹出一个（返回 str），指定时返回 list

        Returns:
            str | list[str] | None: 弹出的元素，列表为空时返回 None
        """
        return await self.client.rpop(name, count)

    async def lrange(self, name: str, start: int, end: int) -> list[str]:
        """
        获取列表指定范围的元素。

        Args:
            name: list 的 key
            start: 起始索引（0-based）
            end: 结束索引（-1 表示到末尾）

        Returns:
            list[str]: 范围内的元素列表
        """
        return await self.client.lrange(name, start, end)

    async def llen(self, name: str) -> int:
        """
        获取列表长度。

        Args:
            name: list 的 key

        Returns:
            int: 列表元素数量
        """
        return await self.client.llen(name)

    async def lindex(self, name: str, index: int) -> str | None:
        """
        获取列表中指定索引的元素。

        Args:
            name: list 的 key
            index: 元素索引（0-based，负数表示从末尾计数）

        Returns:
            str | None: 元素值，索引越界时返回 None
        """
        return await self.client.lindex(name, index)

    async def lset(self, name: str, index: int, value: str) -> bool:
        """
        设置列表中指定索引的元素值。

        Args:
            name: list 的 key
            index: 元素索引
            value: 新值

        Returns:
            bool: 设置成功返回 True

        Raises:
            redis.exceptions.ResponseError: 索引越界时抛出
        """
        return await self.client.lset(name, index, value)

    async def lrem(self, name: str, count: int, value: str) -> int:
        """
        从列表中移除指定数量的匹配元素。

        Args:
            name: list 的 key
            count: 移除数量和方向:
                count > 0: 从头到尾移除最多 count 个
                count < 0: 从尾到头移除最多 |count| 个
                count = 0: 移除所有匹配项
            value: 要匹配的元素值

        Returns:
            int: 实际移除的数量
        """
        return await self.client.lrem(name, count, value)

    async def lmove(
        self, src: str, dst: str, src_side: str = "LEFT", dst_side: str = "RIGHT"
    ) -> str | None:
        """
        原子性地从一个列表弹出元素并推入另一个列表。

        Args:
            src: 源列表 key
            dst: 目标列表 key
            src_side: 从源列表哪端弹出，"LEFT" 或 "RIGHT"
            dst_side: 推入目标列表哪端，"LEFT" 或 "RIGHT"

        Returns:
            str | None: 移动的元素，源列表为空时返回 None
        """
        return await self.client.lmove(src, dst, src_side, dst_side)

    # ── 阻塞操作 ─────────────────────────────────────────────────

    async def blpop(self, *keys: str, timeout: int = 0) -> tuple[str, str] | None:
        """
        阻塞式从左侧弹出元素。

        当任意一个 key 对应的列表有元素时立即弹出，否则阻塞等待。
        多个 key 时按顺序检查，返回第一个非空列表的元素。

        Args:
            *keys: 一个或多个列表 key
            timeout: 阻塞超时秒数，0 表示无限等待

        Returns:
            tuple[str, str] | None: (key, value) 元组，超时或无数据时返回 None
        """
        return await self.client.blpop(keys, timeout)

    async def brpop(self, *keys: str, timeout: int = 0) -> tuple[str, str] | None:
        """
        阻塞式从右侧弹出元素。

        行为同 blpop，但从右侧弹出。

        Args:
            *keys: 一个或多个列表 key
            timeout: 阻塞超时秒数，0 表示无限等待

        Returns:
            tuple[str, str] | None: (key, value) 元组，超时或无数据时返回 None
        """
        return await self.client.brpop(keys, timeout)

    async def blmove(
        self,
        src: str,
        dst: str,
        src_side: str = "LEFT",
        dst_side: str = "RIGHT",
        timeout: int = 0,
    ) -> str | None:
        """
        阻塞式原子移动元素：从源列表弹出并推入目标列表。

        源列表为空时阻塞等待，直到有元素或超时。

        Args:
            src: 源列表 key
            dst: 目标列表 key
            src_side: 从源列表哪端弹出，"LEFT" 或 "RIGHT"
            dst_side: 推入目标列表哪端，"LEFT" 或 "RIGHT"
            timeout: 阻塞超时秒数，0 表示无限等待

        Returns:
            str | None: 移动的元素，超时时返回 None
        """
        return await self.client.blmove(src, dst, src_side, dst_side, timeout)
