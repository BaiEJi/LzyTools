"""
Redis 连接配置模块。

定义 Cache 客户端所需的所有连接参数。
业务方创建 RedisConfig 实例后传给 Cache，不自行读取 .env。
"""

from pydantic import BaseModel


class RedisConfig(BaseModel):
    """
    Redis 连接配置。

    Attributes:
        url: Redis 连接串，格式 redis://:password@host:port/db
        max_connections: 连接池上限，防止耗尽 Redis 服务端连接
        socket_connect_timeout: TCP 建连超时秒数
        socket_timeout: 读写超时秒数，防止慢查询卡住连接
        socket_keepalive: 是否启用 TCP keepalive
        retry_on_timeout: 超时时是否自动重试
        health_check_interval: 空闲连接探活间隔秒数
        decode_responses: 是否自动将 bytes 转为 str
    """

    url: str
    max_connections: int = 50
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    socket_keepalive: bool = True
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    decode_responses: bool = True
