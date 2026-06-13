"""
Redis 缓存装饰器模块。

提供三个核心装饰器:
- cached: 缓存异步函数返回值
- rate_limit: 滑动窗口限流
- synchronized: 分布式锁，防止重复执行

使用方式:
    from basic_tool.redis.decorators import cached, rate_limit, synchronized

    @cached(prefix="user", ttl=600)
    async def get_user(user_id: int):
        return await db.query(...)

    @rate_limit(key="ip:{client_ip}", max_requests=5, window=60, cache=cache)
    async def login(client_ip: str):
        ...

    @synchronized(lock_key="import:{user_id}", timeout=60, cache=cache)
    async def import_data(user_id: int):
        ...
"""

import asyncio
import functools
import hashlib
import inspect
import random
import time
from typing import Any, Callable

from loguru import logger

from basic_tool.errors import AppError
from basic_tool.redis.client import Cache
from basic_tool.redis.locks import Lock

# Sentinel 用于区分 "缓存未命中" 和 "缓存值为 None"
_MISSING = object()


class RateLimitError(AppError):
    """请求频率超限异常。

    继承自 AppError，携带 http_status=429，可被 FastAPI 全局异常处理器
    自动转换为标准 JSON 响应。同时保留 key/count/max_requests/window 属性
    以保持向后兼容。

    Attributes:
        key: 触发限流的维度标识。
        count: 当前窗口内已发生的请求数。
        max_requests: 窗口内允许的最大请求数。
        window: 时间窗口秒数。
    """

    def __init__(self, key: str, count: int, max_requests: int, window: int) -> None:
        """初始化 RateLimitError。

        Args:
            key: 触发限流的维度标识。
            count: 当前窗口内已发生的请求数。
            max_requests: 窗口内允许的最大请求数。
            window: 时间窗口秒数。
        """
        self.key = key
        self.count = count
        self.max_requests = max_requests
        self.window = window
        super().__init__(
            code="RATE_LIMITED",
            message=f"请求频率超限 | key={key} "
            f"count={count} max={max_requests} window={window}s",
            http_status=429,
            context={
                "key": key,
                "count": count,
                "max_requests": max_requests,
                "window": window,
            },
        )


def _build_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """
    根据函数名和参数生成缓存 key。

    策略: prefix:func_name:sha256(args + kwargs)

    Args:
        prefix: key 前缀
        func_name: 函数名
        args: 位置参数（已过滤 Cache 实例）
        kwargs: 关键字参数（已过滤 Cache 实例）

    Returns:
        str: 生成的缓存 key
    """
    sig = f"{args}:{sorted(kwargs.items())}"
    digest = hashlib.sha256(sig.encode()).hexdigest()[:16]
    return f"{prefix}:{func_name}:{digest}"


def _filter_cache_args(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    """从 args/kwargs 中过滤掉 Cache 实例。"""
    filtered_args = tuple(a for a in args if not isinstance(a, Cache))
    filtered_kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, Cache)}
    return filtered_args, filtered_kwargs


def cached(
    *,
    prefix: str,
    ttl: int = 300,
    ttl_jitter: int = 0,
    key_builder: Callable[..., str] | None = None,
    on_cache_hit: Callable[[str], None] | None = None,
    on_cache_miss: Callable[[str], None] | None = None,
) -> Callable:
    """
    缓存异步函数返回值的装饰器。

    缓存策略:
    - 首次调用: 执行函数，将结果存入 Redis
    - 后续调用: 从 Redis 读取，命中则直接返回
    - 过期后: 重新执行函数并更新缓存
    - None 值也会被缓存（通过 exists 检查区分缓存未命中）

    注意: 被装饰函数的第一个参数必须是 Cache 实例（用于访问 Redis）。

    Args:
        prefix: 缓存 key 前缀，如 "user"、"post"
        ttl: 缓存过期秒数，默认 300
        ttl_jitter: TTL 随机抖动上限秒数，防止缓存雪崩。
                    实际 TTL = ttl + random(0, ttl_jitter)
        key_builder: 自定义 key 生成函数。
                    签名 (func_name, filtered_args, filtered_kwargs) -> str
                    注意: args/kwargs 已过滤掉 Cache 实例
        on_cache_hit: 缓存命中时的回调函数，签名 (cache_key: str) -> None。
                     通过回调协议实现外部指标采集（如缓存命中率统计），
                     避免 redis 模块直接依赖 metrics 模块造成循环导入。
                     回调中的异常会被静默吞掉，不影响缓存逻辑。
        on_cache_miss: 缓存未命中时的回调函数，签名 (cache_key: str) -> None。
                      行为与 on_cache_hit 相同，在缓存未命中、执行被装饰函数前调用。

    使用示例:
        @cached(prefix="user", ttl=600)
        async def get_user(cache: Cache, user_id: int):
            return await db.query(...)

        # 调用时自动缓存
        result = await get_user(cache, user_id=123)

        # 通过回调采集缓存命中率（避免 redis 依赖 metrics）
        @cached(
            prefix="user",
            ttl=600,
            on_cache_hit=lambda k: metrics.incr("cache.hit"),
            on_cache_miss=lambda k: metrics.incr("cache.miss"),
        )
        async def get_user_tracked(cache: Cache, user_id: int):
            return await db.query(...)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache: Cache | None = None
            for arg in args:
                if isinstance(arg, Cache):
                    cache = arg
                    break
            if cache is None:
                for v in kwargs.values():
                    if isinstance(v, Cache):
                        cache = v
                        break

            if cache is None:
                logger.warning("cached 装饰器未找到 Cache 参数，跳过缓存")
                return await func(*args, **kwargs)

            filtered_args, filtered_kwargs = _filter_cache_args(args, kwargs)

            if key_builder:
                key = key_builder(func.__name__, filtered_args, filtered_kwargs)
            else:
                key = _build_key(prefix, func.__name__, filtered_args, filtered_kwargs)

            # 用 exists 检查区分 "缓存未命中" 和 "缓存值为 None"
            cached_val = await cache.get_json(key)
            if cached_val is not _MISSING and await cache.exists(key):
                if on_cache_hit is not None:
                    try:
                        on_cache_hit(key)
                    except Exception:
                        pass
                return cached_val

            if on_cache_miss is not None:
                try:
                    on_cache_miss(key)
                except Exception:
                    pass

            result = await func(*args, **kwargs)

            actual_ttl = ttl + (random.randint(0, ttl_jitter) if ttl_jitter else 0)
            await cache.set_json(key, result, ex=actual_ttl)
            return result

        return wrapper

    return decorator


def rate_limit(
    *,
    key: str,
    max_requests: int = 10,
    window: int = 60,
    cache: Cache,
) -> Callable:
    """
    滑动窗口限流装饰器。

    使用 Redis Sorted Set 实现滑动窗口:
    - 每次请求将当前时间戳作为 score 加入 sorted set
    - 清除窗口外的旧记录
    - 统计窗口内请求数，超过限制则拒绝

    key 支持格式化占位符，会从被装饰函数的参数中取值:
    - key="ip:{client_ip}" → 从函数参数 client_ip 取值
    - key="user:{user_id}" → 从函数参数 user_id 取值
    - key="global" → 静态 key，不做格式化

    Args:
        key: 限流维度标识，支持 {param} 格式化占位符
        max_requests: 时间窗口内允许的最大请求数
        window: 时间窗口秒数
        cache: Cache 实例

    Raises:
        RateLimitError: 请求频率超限时抛出

    使用示例:
        @rate_limit(key="ip:{client_ip}", max_requests=5, window=60, cache=cache)
        async def login(client_ip: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 解析动态 key
            actual_key = key
            if "{" in key:
                try:
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    actual_key = key.format(**bound.arguments)
                except (KeyError, TypeError):
                    pass

            now = time.time()
            window_start = now - window
            rate_key = f"rate_limit:{actual_key}"

            pipe = cache.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zadd(rate_key, {str(now): now})
            pipe.zcard(rate_key)
            pipe.expire(rate_key, window)
            results = await pipe.execute()

            count = results[2]
            if count > max_requests:
                raise RateLimitError(
                    key=actual_key,
                    count=count,
                    max_requests=max_requests,
                    window=window,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def synchronized(
    *,
    lock_key: str,
    timeout: int = 30,
    retry_interval: float = 0.1,
    retry_count: int = 50,
    cache: Cache,
) -> Callable:
    """
    分布式锁装饰器，防止同一操作被并发重复执行。

    使用 DistributedLock 实现，支持格式化占位符。

    Args:
        lock_key: 锁的标识，支持格式化占位符，如 "import:{user_id}"
        timeout: 锁自动过期秒数
        retry_interval: 获取锁重试间隔秒数
        retry_count: 获取锁最大重试次数
        cache: Cache 实例

    使用示例:
        @synchronized(lock_key="import:{user_id}", timeout=60, cache=cache)
        async def import_data(user_id: int):
            # 同一时间只有一个实例在执行
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            actual_key = lock_key
            try:
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                actual_key = lock_key.format(**bound.arguments)
            except (KeyError, TypeError):
                pass

            lk = Lock(cache, f"lock:{actual_key}")
            acquired = await lk.acquire(
                timeout=timeout,
                retry_interval=retry_interval,
                retry_count=retry_count,
            )

            if not acquired:
                raise RuntimeError(
                    f"获取分布式锁超时 | key=lock:{actual_key} retries={retry_count}"
                )

            try:
                return await func(*args, **kwargs)
            finally:
                await lk.release()

        return wrapper

    return decorator
