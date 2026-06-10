"""
Pub/Sub 操作 Mixin。

提供 Redis Pub/Sub 消息通信能力。
包括 publish/pubsub/subscribe/psubscribe。
"""

from typing import Any


class PubSubMixin:
    """
    Pub/Sub 操作 Mixin，由 Cache 继承。

    依赖 self.client 属性（由 Cache 基类提供）。
    """

    async def publish(self, channel: str, message: str) -> int:
        """
        向指定频道发布消息。

        Args:
            channel: 频道名
            message: 消息内容

        Returns:
            int: 接收到该消息的订阅者数量
        """
        return await self.client.publish(channel, message)

    def pubsub(self, **kwargs: Any) -> Any:
        """
        获取 Pub/Sub 对象，用于订阅频道并接收消息。

        返回的 PubSub 对象需要手动管理生命周期。

        Args:
            **kwargs: 传递给 redis-py PubSub 的参数

        Returns:
            PubSub: redis-py 的 PubSub 对象

        用法:
            ps = cache.pubsub()
            await ps.subscribe("channel_name")
            async for message in ps.listen():
                if message["type"] == "message":
                    print(message["data"])
        """
        return self.client.pubsub(**kwargs)

    async def subscribe(self, *channels: str) -> Any:
        """
        订阅一个或多个频道，返回 PubSub 对象。

        内部创建 PubSub 实例并订阅指定频道。
        返回的 PubSub 对象通过 listen() 或 get_message() 接收消息。

        Args:
            *channels: 要订阅的频道名列表

        Returns:
            PubSub: 已订阅的 PubSub 对象

        用法:
            ps = await cache.subscribe("events", "logs")
            async for message in ps.listen():
                if message["type"] == "message":
                    print(f"[{message['channel']}] {message['data']}")
            await ps.unsubscribe()
            await ps.aclose()
        """
        ps = self.client.pubsub()
        await ps.subscribe(*channels)
        return ps

    async def psubscribe(self, *patterns: str) -> Any:
        """
        按模式订阅频道，返回 PubSub 对象。

        支持通配符: * 任意多个字符, ? 单个字符, [...] 字符集。

        Args:
            *patterns: 频道模式列表，如 "user:*", "log:??"

        Returns:
            PubSub: 已订阅的 PubSub 对象

        用法:
            ps = await cache.psubscribe("user:*", "system:*")
            async for message in ps.listen():
                if message["type"] == "pmessage":
                    print(f"[{message['channel']}] {message['data']}")
            await ps.punsubscribe()
            await ps.aclose()
        """
        ps = self.client.pubsub()
        await ps.psubscribe(*patterns)
        return ps
