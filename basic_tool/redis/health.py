"""
Redis 健康检查与连接池监控模块。

提供连接池运行时状态读取和 Redis 服务健康状态综合检查，
用于 /health 接口和问题排查。

核心组件:
- CacheHealth: 封装连接池状态读取和 PING 探活

使用方式:
    health = CacheHealth(cache)
    stats = health.pool_stats()
    result = await health.check()
"""

import time

from loguru import logger

from basic_tool.redis.client import Cache


class CacheHealth:
    """
    Redis 健康检查器。

    读取连接池内部状态并提供综合健康检查结果，
    适合接入 FastAPI /health 端点。

    用法:
        health = CacheHealth(cache)
        result = await health.check()
        # {"ok": True, "pool": {...}, "ping_ms": 1.23}
    """

    def __init__(self, cache: Cache) -> None:
        """
        初始化健康检查器。

        Args:
            cache: 已初始化的 Cache 实例
        """
        self._cache = cache

    def pool_stats(self) -> dict:
        """
        获取连接池实时状态。

        通过读取 ConnectionPool 内部属性计算各项指标。

        Returns:
            dict: 连接池状态字典，结构:
                - created (int): 已创建的 TCP 连接总数
                - in_use (int): 正在被占用的连接数
                - idle (int): 空闲可用的连接数
                - max (int): 连接池上限
                - status (str): "ok" 或 "not_initialized"
        """
        pool = self._cache._pool
        if pool is None:
            return {
                "created": 0,
                "in_use": 0,
                "idle": 0,
                "max": 0,
                "status": "not_initialized",
            }

        idle = len(pool._available_connections)
        in_use = len(pool._in_use_connections)
        created = idle + in_use

        return {
            "created": created,
            "in_use": in_use,
            "idle": idle,
            "max": self._cache._config.max_connections,
            "status": "ok",
        }

    async def check(self) -> dict:
        """
        综合健康检查（PING + 连接池状态）。

        执行流程:
        1. 读取连接池状态
        2. 向 Redis 发送 PING 并计算往返时间
        3. 汇总为综合健康结果

        Returns:
            dict: 健康检查结果，结构:
                - ok (bool): 综合健康状态
                - pool (dict): 连接池状态（同 pool_stats）
                - ping_ms (float): PING 往返毫秒数，-1 表示失败
                - error (str | None): 失败时的错误信息
        """
        stats = self.pool_stats()

        try:
            client = self._cache.client
            start = time.monotonic()
            await client.ping()
            ping_ms = round((time.monotonic() - start) * 1000, 2)
        except Exception as e:
            logger.error("Redis PING 失败: {}", e)
            return {
                "ok": False,
                "pool": {**stats, "status": "connection_error"},
                "ping_ms": -1,
                "error": str(e),
            }

        return {
            "ok": stats["status"] == "ok",
            "pool": stats,
            "ping_ms": ping_ms,
            "error": None,
        }
