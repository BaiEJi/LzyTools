"""basic_tool.concurrency — 异步并发工具集。

提供批量并发执行、并发限流、超时保护、重试和错误聚合能力。

典型用法:
    from basic_tool.concurrency import gather_with_limit, with_timeout, ConcurrencyPool

    results = await gather_with_limit(fetch(1), fetch(2), max_concurrency=2)

请求上下文传播:
    所有并发工具（ConcurrencyPool / gather_with_limit / gather_with_retry / TaskGroup）
    均基于 asyncio.Task 调度协程。Python 3.11+ 的 asyncio.Task 在创建时会自动复制
    当前 ContextVar 快照，因此 ``basic_tool.context.ctx`` 中保存的 trace_id、user_id
    等键值会自动传播到子任务中。注意：上下文是 **快照拷贝**（snapshot），而非跨任务
    共享——子任务内的修改不会影响其他任务或父任务。
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
