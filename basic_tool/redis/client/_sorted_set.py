"""
Sorted Set 操作 Mixin。

提供 Redis Sorted Set 类型的操作方法。
包括 zadd/zrem/zrange/zrangebyscore/zcard/zscore/zrank/zremrangebyscore。
"""


class SortedSetMixin:
    """
    Sorted Set 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def zadd(
        self, name: str, mapping: dict[str, float], *, nx: bool = False, xx: bool = False, ch: bool = False
    ) -> int:
        """
        向有序集合添加成员及其分数。

        Args:
            name: sorted set 的 key
            mapping: {member: score} 字典
            nx: 仅添加新成员，不更新已有成员的分数
            xx: 仅更新已有成员，不添加新成员
            ch: 返回值包含被修改的成员数（新增 + 更新）

        Returns:
            int: 新增成员数（ch=True 时包含更新数）
        """
        return await self.client.zadd(name, mapping, nx=nx, xx=xx, ch=ch)

    async def zrem(self, name: str, *values: str) -> int:
        """
        从有序集合中移除成员。

        Args:
            name: sorted set 的 key
            *values: 要移除的成员列表

        Returns:
            int: 实际移除的成员数
        """
        return await self.client.zrem(name, *values)

    async def zrange(
        self, name: str, start: int, end: int, *, withscores: bool = False, desc: bool = False
    ) -> list:
        """
        按索引范围获取有序集合成员。

        Args:
            name: sorted set 的 key
            start: 起始索引（0-based）
            end: 结束索引（-1 表示到末尾）
            withscores: 是否同时返回分数
            desc: 是否按分数降序排列

        Returns:
            list: 成员列表（withscores=True 时为 [(member, score), ...]）
        """
        return await self.client.zrange(name, start, end, withscores=withscores, desc=desc)

    async def zrangebyscore(
        self, name: str, min_score: float | str, max_score: float | str, *, withscores: bool = False, offset: int = 0, count: int | None = None
    ) -> list:
        """
        按分数范围获取有序集合成员。

        Args:
            name: sorted set 的 key
            min_score: 最小分数（用 "-inf" 表示无下界）
            max_score: 最大分数（用 "+inf" 表示无上界）
            withscores: 是否同时返回分数
            offset: 偏移量
            count: 返回数量上限

        Returns:
            list: 成员列表
        """
        return await self.client.zrangebyscore(
            name, min_score, max_score, withscores=withscores,
            start=offset, num=count if count is not None else -1,
        )

    async def zcard(self, name: str) -> int:
        """
        获取有序集合的成员数量。

        Args:
            name: sorted set 的 key

        Returns:
            int: 成员总数
        """
        return await self.client.zcard(name)

    async def zscore(self, name: str, value: str) -> float | None:
        """
        获取有序集合中指定成员的分数。

        Args:
            name: sorted set 的 key
            value: 成员

        Returns:
            float | None: 分数值，成员不存在时返回 None
        """
        return await self.client.zscore(name, value)

    async def zrank(self, name: str, value: str) -> int | None:
        """
        获取有序集合中指定成员的排名（按分数升序，0-based）。

        Args:
            name: sorted set 的 key
            value: 成员

        Returns:
            int | None: 排名，成员不存在时返回 None
        """
        return await self.client.zrank(name, value)

    async def zremrangebyscore(self, name: str, min_score: float | str, max_score: float | str) -> int:
        """
        按分数范围移除有序集合成员。

        Args:
            name: sorted set 的 key
            min_score: 最小分数
            max_score: 最大分数

        Returns:
            int: 实际移除的成员数
        """
        return await self.client.zremrangebyscore(name, min_score, max_score)

    async def zrevrange(self, name: str, start: int, end: int, *, withscores: bool = False) -> list:
        """
        按索引范围获取有序集合成员（按分数降序）。

        Args:
            name: sorted set 的 key
            start: 起始索引（0-based）
            end: 结束索引（-1 表示到末尾）
            withscores: 是否同时返回分数

        Returns:
            list: 成员列表（withscores=True 时为 [(member, score), ...]）
        """
        return await self.client.zrevrange(name, start, end, withscores=withscores)

    async def zrevrank(self, name: str, value: str) -> int | None:
        """
        获取有序集合中指定成员的排名（按分数降序，0-based）。

        Args:
            name: sorted set 的 key
            value: 成员

        Returns:
            int | None: 排名，成员不存在时返回 None
        """
        return await self.client.zrevrank(name, value)

    async def zincrby(self, name: str, amount: float, value: str) -> float:
        """
        将有序集合中指定成员的分数递增。

        Args:
            name: sorted set 的 key
            amount: 递增量（可为负数）
            value: 成员

        Returns:
            float: 递增后的分数
        """
        return await self.client.zincrby(name, amount, value)

    async def zcount(self, name: str, min_score: float | str, max_score: float | str) -> int:
        """
        统计分数范围内的成员数量。

        Args:
            name: sorted set 的 key
            min_score: 最小分数（用 "-inf" 表示无下界）
            max_score: 最大分数（用 "+inf" 表示无上界）

        Returns:
            int: 成员数量
        """
        return await self.client.zcount(name, min_score, max_score)

    async def zlexcount(self, name: str, min_val: str, max_val: str) -> int:
        """
        统计字典序范围内的成员数量（所有成员分数相同时使用）。

        Args:
            name: sorted set 的 key
            min_val: 最小值（用 "-" 表示无下界，"(" 表示不包含）
            max_val: 最大值（用 "+" 表示无上界，"(" 表示不包含）

        Returns:
            int: 成员数量
        """
        return await self.client.zlexcount(name, min_val, max_val)
