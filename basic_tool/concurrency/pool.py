"""Concurrency pool for limiting simultaneous async tasks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar

from loguru import logger

T = TypeVar("T")


@dataclass(frozen=True)
class PoolStats:
    """Snapshot of pool state.

    Attributes:
        total: Maximum concurrent tasks allowed.
        used: Currently running tasks.
        waiting: Tasks waiting to acquire a semaphore slot.
        available: Slots available for new tasks.
    """

    total: int
    used: int
    waiting: int
    available: int


class ConcurrencyPool:
    """Limits concurrent execution of coroutines using a semaphore.

    请求上下文传播: 协程通过 ``await coro`` 直接执行，保留当前 ContextVar；
    若需在新 Task 中运行，asyncio.Task 会自动复制当前上下文快照（Python 3.11+），
    使 ``ctx.get("trace_id")`` 等值在子任务中可见。上下文为快照拷贝，跨任务互不影响。

    Args:
        max_concurrency: Maximum number of concurrent tasks. Must be >= 1.

    Raises:
        ValueError: If max_concurrency < 1.
    """

    def __init__(self, max_concurrency: int) -> None:
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency}")
        self._max = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._used = 0
        self._waiting = 0
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> PoolStats:
        """Return current pool statistics."""
        return PoolStats(
            total=self._max,
            used=self._used,
            waiting=self._waiting,
            available=self._max - self._used,
        )

    async def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine within the pool's concurrency limit.

        Args:
            coro: The coroutine to execute.

        Returns:
            The coroutine's return value.
        """
        # Track waiting BEFORE acquiring semaphore
        async with self._lock:
            self._waiting += 1
        try:
            async with self._semaphore:
                # Acquired semaphore — no longer waiting, now running
                async with self._lock:
                    self._waiting -= 1
                    self._used += 1
                try:
                    logger.debug("pool task started | used={}/{}", self._used, self._max)
                    return await coro
                finally:
                    async with self._lock:
                        self._used -= 1
                    logger.debug("pool task finished | used={}/{}", self._used, self._max)
        except BaseException:
            # If we were waiting but got cancelled before acquiring
            async with self._lock:
                if self._waiting > 0:
                    self._waiting -= 1
            raise

    async def gather(self, *coros: Coroutine[Any, Any, T]) -> list[T]:
        """Execute multiple coroutines concurrently within pool limits.

        Args:
            *coros: Coroutines to execute.

        Returns:
            List of results in the same order as input.
        """
        return list(await asyncio.gather(*(self.run(c) for c in coros)))
