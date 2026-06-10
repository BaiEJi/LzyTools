"""
JSON 序列化快捷操作 Mixin。

提供基于 orjson 的 JSON 序列化/反序列化缓存操作。
包括 get_json/set_json。
"""

from typing import Any

import orjson


class JsonMixin:
    """
    JSON 序列化操作 Mixin，由 Cache 继承。

    依赖 self.get/set 方法（由 StringMixin 提供）。
    """

    async def get_json(self, key: str) -> Any:
        """
        获取 key 的值并反序列化为 Python 对象。

        使用 orjson 解析存储的 JSON 字符串。

        Args:
            key: Redis key

        Returns:
            Any: 反序列化后的 Python 对象（dict / list / ...）
                 key 不存在时返回 None
        """
        raw = await self.get(key)
        if raw is None:
            return None
        return orjson.loads(raw)

    async def set_json(
        self,
        key: str,
        value: Any,
        *,
        ex: int | None = None,
    ) -> bool | None:
        """
        将 Python 对象序列化为 JSON 并存储。

        使用 orjson 序列化，支持 datetime、UUID 等类型。

        Args:
            key: Redis key
            value: 要存储的 Python 对象
            ex: 过期时间（秒），None 表示永不过期

        Returns:
            bool | None: 设置成功返回 True
        """
        raw = orjson.dumps(value).decode("utf-8")
        return await self.set(key, raw, ex=ex)
