"""basic_tool.concurrency — 异步并发工具集。

提供批量并发执行、并发限流、超时保护、重试和错误聚合能力。

典型用法:
    from basic_tool.concurrency import gather_with_limit, with_timeout, ConcurrencyPool

    results = await gather_with_limit(fetch(1), fetch(2), max_concurrency=2)
"""

from basic_tool.concurrency.config import ConcurrencyConfig
from basic_tool.concurrency.exceptions import CompositeError
from basic_tool.concurrency.strategy import ErrorStrategy
from basic_tool.concurrency.pool import ConcurrencyPool, PoolStats
from basic_tool.concurrency.batch import gather_with_limit, gather_with_retry, run_in_batches
from basic_tool.concurrency.timeout import with_timeout
from basic_tool.concurrency.task_group import TaskGroup

__all__ = [
    "ConcurrencyConfig",
    "CompositeError",
    "ErrorStrategy",
    "ConcurrencyPool",
    "PoolStats",
    "gather_with_limit",
    "gather_with_retry",
    "run_in_batches",
    "with_timeout",
    "TaskGroup",
]
