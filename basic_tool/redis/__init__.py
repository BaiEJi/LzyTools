"""
basic_tool.redis 包的初始化模块。

统一导出缓存相关组件，方便外部使用:
    from basic_tool.redis import Cache, RedisConfig
    from basic_tool.redis import CacheHealth, DistributedLock
    from basic_tool.redis import cached, rate_limit, synchronized
"""

from basic_tool.redis.client import Cache
from basic_tool.redis.config import RedisConfig
from basic_tool.redis.decorators import RateLimitError, cached, rate_limit, synchronized
from basic_tool.redis.health import CacheHealth
from basic_tool.redis.locks import DistributedLock, Lock

__all__ = [
    "Cache",
    "RedisConfig",
    "CacheHealth",
    "DistributedLock",
    "Lock",
    "cached",
    "rate_limit",
    "synchronized",
    "RateLimitError",
]
