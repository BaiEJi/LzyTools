"""
原始命令与 Pipeline 操作 Mixin。

提供直接执行 Redis 原始命令和 Pipeline 批量操作能力。
包括 execute_command/pipeline。
"""

from typing import Any


class RawMixin:
    """
    原始命令操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    def pipeline(self, transaction: bool = True) -> Any:
        """
        获取 Redis Pipeline 对象，用于批量原子操作。

        用法:
            pipe = cache.pipeline()
            pipe.set("a", "1")
            pipe.set("b", "2")
            results = await pipe.execute()

        Args:
            transaction: 是否用 MULTI/EXEC 包裹，默认 True

        Returns:
            Pipeline: Redis Pipeline 对象
        """
        return self.client.pipeline(transaction=transaction)

    async def execute_command(self, *args: Any, **kwargs: Any) -> Any:
        """
        直接执行 Redis 原始命令。

        当 Cache 未封装某个 Redis 命令时使用。
        参数按 Redis 命令行格式传入。

        Args:
            *args: 命令和参数，如 ("XADD", "stream", "*", "field", "value")
            **kwargs: 额外参数传递给 redis-py

        Returns:
            Any: Redis 返回值

        用法:
            result = await cache.execute_command("XADD", "mystream", "*", "name", "Alice")
            info = await cache.execute_command("CLUSTER", "INFO")
            result = await cache.execute_command("FT.SEARCH", "idx", "hello")
        """
        return await self.client.execute_command(*args, **kwargs)
