"""Batch execution utilities for concurrent async operations."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Coroutine, TypeVar

from basic_tool.concurrency.exceptions import CompositeError
from basic_tool.concurrency.strategy import ErrorStrategy

T = TypeVar("T")


async def gather_with_limit(
    *coros: Coroutine[Any, Any, T],
    max_concurrency: int,
    strategy: ErrorStrategy = ErrorStrategy.FAIL_FAST,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[T]:
    """Execute coroutines with a concurrency limit.

    Args:
        *coros: Coroutines to execute.
        max_concurrency: Maximum concurrent tasks. Must be >= 1.
        strategy: Error handling strategy.
        on_progress: Optional callback(completed, total) called after each task completes.

    Returns:
        List of results in input order.

    Raises:
        ValueError: If max_concurrency < 1.
    """
    if max_concurrency < 1:
        raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency}")

    if not coros:
        return []

    total = len(coros)
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[Any] = [None] * total
    errors: list[tuple[int, BaseException]] = []
    completed = 0
    lock = asyncio.Lock()

    async def run_one(index: int, coro: Coroutine[Any, Any, T]) -> None:
        nonlocal completed
        async with semaphore:
            try:
                results[index] = await coro
            except BaseException as e:
                async with lock:
                    errors.append((index, e))
                if strategy == ErrorStrategy.FAIL_FAST:
                    raise
            finally:
                async with lock:
                    completed += 1
                    if on_progress is not None:
                        on_progress(completed, total)

    if strategy == ErrorStrategy.FAIL_FAST:
        # Use asyncio.TaskGroup for automatic cancellation
        try:
            async with asyncio.TaskGroup() as tg:
                for i, coro in enumerate(coros):
                    tg.create_task(run_one(i, coro))
        except BaseExceptionGroup as eg:
            # Extract the first real error (not from our re-raise)
            for exc in eg.exceptions:
                if isinstance(exc, BaseException) and not isinstance(exc, BaseExceptionGroup):
                    raise exc from None
            raise eg.exceptions[0] from None
    else:
        # COLLECT_ALL or SKIP_FAILED — run all tasks
        tasks = [asyncio.create_task(run_one(i, coro)) for i, coro in enumerate(coros)]
        await asyncio.gather(*tasks, return_exceptions=True)

    if errors:
        if strategy == ErrorStrategy.SKIP_FAILED:
            # Return only successful results, maintaining order
            error_indices = {idx for idx, _ in errors}
            return [results[i] for i in range(total) if i not in error_indices]
        else:
            # COLLECT_ALL — raise CompositeError
            indices = [idx for idx, _ in errors]
            errs = [err for _, err in errors]
            raise CompositeError(errs, indices)

    return results


async def run_in_batches(
    fn: Callable[[Any], Coroutine[Any, Any, T]],
    items: list[Any],
    batch_size: int,
    inter_batch_delay: float = 0.0,
) -> list[T]:
    """Execute a function over items in sequential batches.

    Args:
        fn: Async function to apply to each item.
        items: Items to process.
        batch_size: Items per batch. Must be >= 1.
        inter_batch_delay: Delay in seconds between batches.

    Returns:
        List of results in original item order.

    Raises:
        ValueError: If batch_size < 1.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")

    if not items:
        return []

    results: list[T] = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_results = await asyncio.gather(*(fn(item) for item in batch))
        results.extend(batch_results)
        if inter_batch_delay > 0 and i + batch_size < len(items):
            await asyncio.sleep(inter_batch_delay)

    return results


async def gather_with_retry(
    *coro_factories: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_cap: float = 60.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    strategy: ErrorStrategy = ErrorStrategy.COLLECT_ALL,
) -> list[T]:
    """Execute coroutines with retry support using factory functions.

    Each coro_factory is called to create a fresh coroutine for each attempt,
    avoiding the "coroutine already awaited" error on retry.

    Args:
        *coro_factories: Callables that return fresh coroutines.
        max_retries: Maximum number of retry attempts per task.
        backoff_base: Base delay for exponential backoff (seconds).
        backoff_cap: Maximum backoff delay (seconds).
        retryable_exceptions: Exception types that trigger a retry.
        strategy: Error handling strategy for final failures.

    Returns:
        List of results.

    Raises:
        CompositeError: If tasks fail after all retries.
    """
    if not coro_factories:
        return []

    async def _run_with_retry(
        idx: int, factory: Callable[[], Coroutine[Any, Any, T]]
    ) -> tuple[int, T | None, BaseException | None]:
        last_error: BaseException | None = None
        for attempt in range(max_retries):
            coro = factory()  # Create fresh coroutine each attempt
            try:
                result = await coro
                return (idx, result, None)
            except retryable_exceptions as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = min(backoff_base * (2 ** attempt), backoff_cap)
                    delay *= (0.5 + random.random() * 0.5)  # jitter
                    await asyncio.sleep(delay)
            except BaseException as e:
                # Non-retryable exception
                return (idx, None, e)

        return (idx, None, last_error)

    tasks = [
        asyncio.create_task(_run_with_retry(i, factory))
        for i, factory in enumerate(coro_factories)
    ]
    outcomes = await asyncio.gather(*tasks)

    errors = [(idx, err) for idx, _, err in outcomes if err is not None]
    if errors:
        if strategy == ErrorStrategy.SKIP_FAILED:
            error_indices = {idx for idx, _ in errors}
            return [result for idx, result, _ in outcomes if idx not in error_indices and result is not None]
        else:
            indices = [idx for idx, _ in errors]
            errs = [err for _, err in errors]
            raise CompositeError(errs, indices)

    return [result for _, result, _ in outcomes if result is not None]
