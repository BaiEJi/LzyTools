"""
Stream 操作 Mixin。

提供 Redis Stream 写入能力。
当前仅包含 xadd，是 metrics 模块的前置依赖。
"""

from typing import Any


class StreamMixin:
    """
    Stream 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

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
        return await self.client.xadd(name, fields, id=id, maxlen=maxlen, approximate=approximate)
