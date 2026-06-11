"""@task 装饰器和任务注册表。

通过装饰器注册异步函数为 ARQ 任务，消除字符串引用风险。
Worker 启动时自动从注册表收集所有任务函数。
"""

import functools
from typing import Any, Callable

from loguru import logger

_REGISTRY: dict[str, Callable] = {}
_TASK_META: dict[str, dict] = {}


def task(
    *,
    name: str | None = None,
    max_tries: int | None = None,
    job_timeout: int | None = None,
) -> Callable:
    """注册异步函数为 ARQ 任务。

    被装饰的函数自动加入注册表，Worker 启动时自动发现。
    函数签名第一个参数必须是 ctx（Worker 上下文）。

    Args:
        name: 任务名称，默认使用函数名。
        max_tries: 此任务的最大重试次数，None 使用全局默认值。
        job_timeout: 此任务的超时秒数，None 使用全局默认值。

    使用示例::

        @task(max_tries=3)
        async def send_email(ctx, to: str, subject: str):
            ...

        # 入队时使用函数名字符串（注册表保证一致性）
        await queue.enqueue("send_email", "user@example.com", "Hello")
    """

    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__

        if task_name in _REGISTRY:
            logger.warning("任务名重复注册 | name={} existing={} new={}", task_name, _REGISTRY[task_name], func)

        _REGISTRY[task_name] = func
        _TASK_META[task_name] = {
            "max_tries": max_tries,
            "job_timeout": job_timeout,
        }

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        wrapper._task_name = task_name
        return wrapper

    return decorator


def get_registry() -> dict[str, Callable]:
    """返回当前任务注册表的副本。

    Returns:
        任务名到函数的映射。
    """
    return dict(_REGISTRY)


def get_task_meta(name: str) -> dict | None:
    """返回指定任务的元数据。

    Args:
        name: 任务名称。

    Returns:
        任务元数据字典，任务不存在时返回 None。
    """
    return _TASK_META.get(name)


def validate_task_name(name: str) -> bool:
    """校验任务名是否在注册表中。

    Args:
        name: 任务名称。

    Returns:
        True 表示任务已注册，False 表示未注册。
    """
    if name not in _REGISTRY:
        logger.warning("任务未注册 | name={}", name)
        return False
    return True
