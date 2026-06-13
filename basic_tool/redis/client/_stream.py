"""
Stream 操作 Mixin。

提供 Redis Stream 类型的全部操作方法，包括：
- 写入: xadd
- 读取: xread / xrange / xrevrange
- 管理: xlen / xtrim / xdel / xinfo_stream
- 消费者组: xgroup_create / xgroup_destroy / xgroup_delconsumer
- 消费者组读取: xreadgroup / xack / xpending / xpending_range / xclaim
- 消费者组信息: xinfo_groups / xinfo_consumers
"""

from __future__ import annotations

from typing import Any


class StreamMixin:
    """
    Stream 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    # ── 写入 ──────────────────────────────────────────────────────

    async def xadd(
        self,
        name: str,
        fields: dict[str, Any],
        id: str = "*",
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        """
        向 Stream 追加一条消息，返回生成的 entry ID。

        Args:
            name: Stream 名称
            fields: 消息字段键值对
            id: entry ID，默认 "*" 表示由 Redis 自动生成（格式 "时间戳-序号"）
            maxlen: Stream 最大长度，超过时自动裁剪旧 entry
            approximate: 是否使用近似裁剪（~ 标志，性能更好）

        Returns:
            str: 生成的 entry ID（如 "1234567890-0"）
        """
        return await self.client.xadd(
            name, fields, id=id, maxlen=maxlen, approximate=approximate
        )

    # ── 读取 ──────────────────────────────────────────────────────

    async def xrange(
        self,
        name: str,
        min: str = "-",
        max: str = "+",
        count: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        按 ID 范围读取 Stream 条目（正序）。

        Args:
            name: Stream 名称
            min: 起始 ID，"-" 表示最小
            max: 结束 ID，"+" 表示最大
            count: 最多返回条数

        Returns:
            list[tuple[str, dict[str, str]]]: [(entry_id, {field: value}), ...]
        """
        return await self.client.xrange(name, min=min, max=max, count=count)

    async def xrevrange(
        self,
        name: str,
        max: str = "+",
        min: str = "-",
        count: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        按 ID 范围读取 Stream 条目（倒序）。

        Args:
            name: Stream 名称
            max: 起始 ID（倒序从最大开始），"+" 表示最大
            min: 结束 ID，"-" 表示最小
            count: 最多返回条数

        Returns:
            list[tuple[str, dict[str, str]]]: [(entry_id, {field: value}), ...]
        """
        return await self.client.xrevrange(name, max=max, min=min, count=count)

    async def xread(
        self,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]] | None:
        """
        从一个或多个 Stream 读取新条目。

        Args:
            streams: {stream_name: last_id} 字典，last_id 为 "$" 表示只读新消息
            count: 每个 Stream 最多返回条数
            block: 阻塞等待毫秒数，None 表示不阻塞，0 表示无限等待

        Returns:
            list[tuple[str, list]] | None: [(stream_name, [(entry_id, fields), ...]), ...]
                无新数据时返回 None
        """
        return await self.client.xread(
            streams=streams, count=count, block=block
        )

    # ── 管理 ──────────────────────────────────────────────────────

    async def xlen(self, name: str) -> int:
        """
        获取 Stream 中的条目总数。

        Args:
            name: Stream 名称

        Returns:
            int: 条目数量
        """
        return await self.client.xlen(name)

    async def xtrim(
        self,
        name: str,
        maxlen: int,
        approximate: bool = True,
    ) -> int:
        """
        裁剪 Stream 到指定最大长度。

        Args:
            name: Stream 名称
            maxlen: 保留的最大条目数
            approximate: 是否使用近似裁剪（性能更好）

        Returns:
            int: 被删除的条目数
        """
        return await self.client.xtrim(
            name, maxlen=maxlen, approximate=approximate
        )

    async def xdel(self, name: str, *ids: str) -> int:
        """
        删除 Stream 中的指定条目。

        Args:
            name: Stream 名称
            *ids: 要删除的 entry ID 列表

        Returns:
            int: 成功删除的条目数
        """
        return await self.client.xdel(name, *ids)

    async def xinfo_stream(self, name: str, full: bool = False) -> dict[str, Any]:
        """
        获取 Stream 的元信息。

        Args:
            name: Stream 名称
            full: 是否返回完整信息（包含消费者组和消费者详情）

        Returns:
            dict: Stream 信息，包含 length、first-entry、last-entry 等
        """
        return await self.client.xinfo_stream(name, full=full)

    # ── 消费者组 ──────────────────────────────────────────────────

    async def xgroup_create(
        self,
        name: str,
        groupname: str,
        id: str = "$",
        mkstream: bool = False,
    ) -> bool:
        """
        创建消费者组。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            id: 起始消费位置，"$" 表示从最新消息开始，"0" 表示从头开始
            mkstream: Stream 不存在时是否自动创建

        Returns:
            bool: 创建成功返回 True
        """
        return await self.client.xgroup_create(
            name, groupname, id=id, mkstream=mkstream
        )

    async def xgroup_destroy(self, name: str, groupname: str) -> bool:
        """
        销毁消费者组。

        Args:
            name: Stream 名称
            groupname: 消费者组名称

        Returns:
            bool: 销毁成功返回 True
        """
        return await self.client.xgroup_destroy(name, groupname)

    async def xgroup_delconsumer(
        self, name: str, groupname: str, consumername: str
    ) -> int:
        """
        从消费者组中删除消费者。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            consumername: 消费者名称

        Returns:
            int: 被删除消费者的 pending 消息数
        """
        return await self.client.xgroup_delconsumer(
            name, groupname, consumername
        )

    async def xgroup_setid(
        self, name: str, groupname: str, id: str = "$"
    ) -> bool:
        """
        设置消费者组的最后交付 ID。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            id: 新的 last delivered ID

        Returns:
            bool: 设置成功返回 True
        """
        return await self.client.xgroup_setid(name, groupname, id=id)

    # ── 消费者组读取 ──────────────────────────────────────────────

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
        noack: bool = False,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]] | None:
        """
        以消费者组身份读取 Stream 条目。

        读取的条目会进入该消费者的 pending 列表，需要 xack 确认。

        Args:
            groupname: 消费者组名称
            consumername: 消费者名称
            streams: {stream_name: last_id} 字典，">" 表示读取未分配的新消息
            count: 每次最多返回条数
            block: 阻塞等待毫秒数，None 不阻塞，0 无限等待
            noack: 是否自动确认（不推荐，会丢失消息追踪）

        Returns:
            list[tuple[str, list]] | None: [(stream_name, [(entry_id, fields), ...]), ...]
        """
        return await self.client.xreadgroup(
            groupname,
            consumername,
            streams=streams,
            count=count,
            block=block,
            noack=noack,
        )

    async def xack(self, name: str, groupname: str, *ids: str) -> int:
        """
        确认消费者组中的消息。

        确认后消息从消费者的 pending 列表中移除。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            *ids: 要确认的 entry ID 列表

        Returns:
            int: 成功确认的消息数
        """
        return await self.client.xack(name, groupname, *ids)

    # ── Pending 消息管理 ──────────────────────────────────────────

    async def xpending(self, name: str, groupname: str) -> dict[str, Any]:
        """
        获取消费者组的 pending 消息摘要。

        Args:
            name: Stream 名称
            groupname: 消费者组名称

        Returns:
            dict: 包含 pending 消息数、最小/最大 ID、消费者列表
        """
        return await self.client.xpending(name, groupname)

    async def xpending_range(
        self,
        name: str,
        groupname: str,
        min: str,
        max: str,
        count: int,
        consumername: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取消费者组中指定范围的 pending 消息详情。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            min: 起始 ID，"-" 表示最小
            max: 结束 ID，"+" 表示最大
            count: 最多返回条数
            consumername: 过滤指定消费者，None 表示所有消费者

        Returns:
            list[dict]: 每条 pending 消息的详情（entry_id、consumer、idle_time、delivery_count）
        """
        return await self.client.xpending_range(
            name, groupname, min=min, max=max, count=count,
            consumername=consumername,
        )

    async def xclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        *ids: str,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        认领超过指定空闲时间的 pending 消息。

        用于处理消费者崩溃后遗留的未确认消息。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            consumername: 认领者（消费者）名称
            min_idle_time: 最小空闲时间（毫秒），超过此时间的消息才会被认领
            *ids: 要认领的 entry ID 列表

        Returns:
            list[tuple[str, dict[str, str]]]: 认领到的消息 [(entry_id, fields), ...]
        """
        return await self.client.xclaim(
            name, groupname, consumername, min_idle_time, list(ids)
        )

    async def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start: str = "0-0",
        count: int | None = None,
    ) -> tuple[str, list[tuple[str, dict[str, str]]]]:
        """
        自动认领超过指定空闲时间的 pending 消息。

        与 xclaim 不同，xautoclaim 自动扫描并返回下一批待认领的位置。

        Args:
            name: Stream 名称
            groupname: 消费者组名称
            consumername: 认领者名称
            min_idle_time: 最小空闲时间（毫秒）
            start: 扫描起始 ID，"0-0" 从头开始
            count: 单次最多认领条数

        Returns:
            tuple[str, list]: (next_start_id, [(entry_id, fields), ...])
                next_start_id 用于下次调用的 start 参数，实现分页扫描
        """
        return await self.client.xautoclaim(
            name, groupname, consumername, min_idle_time,
            start=start, count=count,
        )

    # ── 消费者组信息 ──────────────────────────────────────────────

    async def xinfo_groups(self, name: str) -> list[dict[str, Any]]:
        """
        获取 Stream 的所有消费者组信息。

        Args:
            name: Stream 名称

        Returns:
            list[dict]: 每个消费者组的信息（name、consumers、pending、last-delivered-id 等）
        """
        return await self.client.xinfo_groups(name)

    async def xinfo_consumers(self, name: str, groupname: str) -> list[dict[str, Any]]:
        """
        获取消费者组中所有消费者的信息。

        Args:
            name: Stream 名称
            groupname: 消费者组名称

        Returns:
            list[dict]: 每个消费者的信息（name、pending、idle 等）
        """
        return await self.client.xinfo_consumers(name, groupname)
