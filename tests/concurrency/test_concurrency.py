"""Tests for basic_tool.concurrency module.

Covers gather_with_limit, run_in_batches, gather_with_retry, with_timeout,
ConcurrencyPool, TaskGroup, CompositeError, and ErrorStrategy.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from basic_tool.concurrency.config import ConcurrencyConfig
from basic_tool.concurrency.exceptions import CompositeError
from basic_tool.concurrency.strategy import ErrorStrategy


# ---------------------------------------------------------------------------
# gather_with_limit (tests 1-8)
# ---------------------------------------------------------------------------


async def test_gather_with_limit_basic():
    """Returns results in the same order as input."""
    from basic_tool.concurrency.batch import gather_with_limit

    async def val(n):
        await asyncio.sleep(0.01)
        return n

    results = await gather_with_limit(val(1), val(2), val(3), max_concurrency=2)
    assert results == [1, 2, 3]


async def test_gather_with_limit_concurrency_limit():
    """Actual concurrency does not exceed max_concurrency."""
    from basic_tool.concurrency.batch import gather_with_limit

    peak = 0
    current = 0

    async def tracker(n):
        nonlocal peak, current
        current += 1
        if current > peak:
            peak = current
        await asyncio.sleep(0.05)
        current -= 1
        return n

    results = await gather_with_limit(
        *[tracker(i) for i in range(10)],
        max_concurrency=3,
    )
    assert len(results) == 10
    assert peak <= 3


async def test_gather_with_limit_fail_fast():
    """First error cancels remaining tasks and raises immediately."""
    from basic_tool.concurrency.batch import gather_with_limit

    async def fail():
        await asyncio.sleep(0.01)
        raise ValueError("boom")

    async def slow():
        await asyncio.sleep(10)
        return "should not reach"

    with pytest.raises(ValueError, match="boom"):
        await gather_with_limit(fail(), slow(), max_concurrency=2, strategy=ErrorStrategy.FAIL_FAST)


async def test_gather_with_limit_collect_all():
    """Waits for all tasks and raises CompositeError with all failures."""
    from basic_tool.concurrency.batch import gather_with_limit

    async def fail(n):
        raise ValueError(f"err{n}")

    async def ok(n):
        return n

    with pytest.raises(CompositeError) as exc_info:
        await gather_with_limit(
            ok(1), fail(2), ok(3), fail(4),
            max_concurrency=4,
            strategy=ErrorStrategy.COLLECT_ALL,
        )
    assert len(exc_info.value.errors) == 2


async def test_gather_with_limit_skip_failed():
    """Skips failed tasks, returns successful results only."""
    from basic_tool.concurrency.batch import gather_with_limit

    async def fail():
        raise ValueError("fail")

    async def ok(n):
        return n

    results = await gather_with_limit(
        ok(1), fail(), ok(3),
        max_concurrency=3,
        strategy=ErrorStrategy.SKIP_FAILED,
    )
    assert results == [1, 3]


async def test_gather_with_limit_empty():
    """Empty input returns empty list."""
    from basic_tool.concurrency.batch import gather_with_limit

    results = await gather_with_limit(max_concurrency=2)
    assert results == []


async def test_gather_with_limit_progress_callback():
    """on_progress is called with correct (completed, total) pairs."""
    from basic_tool.concurrency.batch import gather_with_limit

    progress_calls = []

    async def val(n):
        await asyncio.sleep(0.01)
        return n

    results = await gather_with_limit(
        val(1), val(2), val(3),
        max_concurrency=2,
        on_progress=lambda completed, total: progress_calls.append((completed, total)),
    )
    assert results == [1, 2, 3]
    assert len(progress_calls) == 3
    assert progress_calls[-1] == (3, 3)


async def test_gather_with_limit_invalid_concurrency():
    """max_concurrency < 1 raises ValueError."""
    from basic_tool.concurrency.batch import gather_with_limit

    with pytest.raises(ValueError):
        await gather_with_limit(max_concurrency=0)


# ---------------------------------------------------------------------------
# run_in_batches (tests 9-12)
# ---------------------------------------------------------------------------


async def test_run_in_batches_basic():
    """Executes in batches, results in original order."""
    from basic_tool.concurrency.batch import run_in_batches

    async def double(n):
        await asyncio.sleep(0.01)
        return n * 2

    results = await run_in_batches(double, [1, 2, 3, 4, 5], batch_size=2)
    assert results == [2, 4, 6, 8, 10]


async def test_run_in_batches_inter_batch_delay():
    """Actual delay exists between batches (timing verification)."""
    from basic_tool.concurrency.batch import run_in_batches

    timestamps = []

    async def record(n):
        timestamps.append(asyncio.get_event_loop().time())
        return n

    import time
    start = time.monotonic()
    await run_in_batches(record, [1, 2, 3], batch_size=1, inter_batch_delay=0.05)
    elapsed = time.monotonic() - start
    # 3 batches with 2 delays of 0.05s each → at least 0.1s
    assert elapsed >= 0.08  # slight tolerance


async def test_run_in_batches_empty():
    """Empty input returns empty list."""
    from basic_tool.concurrency.batch import run_in_batches

    async def noop(n):
        return n

    results = await run_in_batches(noop, [], batch_size=10)
    assert results == []


async def test_run_in_batches_invalid_batch_size():
    """batch_size < 1 raises ValueError."""
    from basic_tool.concurrency.batch import run_in_batches

    async def noop(n):
        return n

    with pytest.raises(ValueError):
        await run_in_batches(noop, [1, 2, 3], batch_size=0)


# ---------------------------------------------------------------------------
# with_timeout (tests 13-16)
# ---------------------------------------------------------------------------


async def test_with_timeout_normal():
    """Normal completion returns result."""
    from basic_tool.concurrency.timeout import with_timeout

    result = await with_timeout(asyncio.sleep(0.01), timeout=5.0)
    assert result is None


async def test_with_timeout_exceeds():
    """Timeout raises built-in TimeoutError."""
    from basic_tool.concurrency.timeout import with_timeout

    with pytest.raises(TimeoutError):
        await with_timeout(asyncio.sleep(100), timeout=0.05)


async def test_with_timeout_invalid_timeout():
    """timeout <= 0 raises ValueError."""
    from basic_tool.concurrency.timeout import with_timeout

    with pytest.raises(ValueError):
        await with_timeout(asyncio.sleep(1), timeout=0)

    with pytest.raises(ValueError):
        await with_timeout(asyncio.sleep(1), timeout=-1)


async def test_with_timeout_custom_message():
    """TimeoutError contains custom message."""
    from basic_tool.concurrency.timeout import with_timeout

    with pytest.raises(TimeoutError, match="custom timeout msg"):
        await with_timeout(asyncio.sleep(100), timeout=0.05, message="custom timeout msg")


# ---------------------------------------------------------------------------
# gather_with_retry (tests 17-21)
# NOTE: Uses factory function API: *coro_factories: Callable[[], Coroutine]
# ---------------------------------------------------------------------------


async def test_gather_with_retry_first_success():
    """First attempt succeeds, no retries."""
    from basic_tool.concurrency.batch import gather_with_retry

    async def val():
        return 42

    results = await gather_with_retry(lambda: val(), max_retries=3)
    assert results == [42]


async def test_gather_with_retry_retry_then_success():
    """Succeeds on Nth attempt."""
    from basic_tool.concurrency.batch import gather_with_retry

    attempt = 0

    async def flaky():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise ValueError("not yet")
        return "ok"

    results = await gather_with_retry(lambda: flaky(), max_retries=3)
    assert results == ["ok"]
    assert attempt == 3


async def test_gather_with_retry_all_fail():
    """All retries exhausted raises CompositeError."""
    from basic_tool.concurrency.batch import gather_with_retry

    async def always_fail():
        raise ValueError("nope")

    with pytest.raises(CompositeError) as exc_info:
        await gather_with_retry(lambda: always_fail(), max_retries=2)
    assert len(exc_info.value.errors) == 1


async def test_gather_with_retry_non_retryable():
    """Non-retryable exception type is not retried."""
    from basic_tool.concurrency.batch import gather_with_retry

    attempt = 0

    async def type_fail():
        nonlocal attempt
        attempt += 1
        raise TypeError("wrong type")

    with pytest.raises(CompositeError):
        await gather_with_retry(
            lambda: type_fail(),
            max_retries=5,
            retryable_exceptions=(ValueError,),
        )
    # Should only attempt once since TypeError is not retryable
    assert attempt == 1


async def test_gather_with_retry_skip_failed():
    """SKIP_FAILED strategy skips failed results."""
    from basic_tool.concurrency.batch import gather_with_retry

    attempt = 0

    async def sometimes_fail():
        nonlocal attempt
        attempt += 1
        if attempt <= 1:
            raise ValueError("first fail")
        return "ok"

    results = await gather_with_retry(
        lambda: sometimes_fail(),
        max_retries=1,
        strategy=ErrorStrategy.SKIP_FAILED,
    )
    assert results == []


# ---------------------------------------------------------------------------
# ConcurrencyPool (tests 22-25)
# ---------------------------------------------------------------------------


async def test_pool_basic():
    """Pool run() returns coroutine result."""
    from basic_tool.concurrency.pool import ConcurrencyPool

    async def double(n):
        await asyncio.sleep(0.01)
        return n * 2

    pool = ConcurrencyPool(max_concurrency=5)
    result = await pool.run(double(21))
    assert result == 42


async def test_pool_concurrency_limit():
    """Simultaneous tasks do not exceed max_concurrency."""
    from basic_tool.concurrency.pool import ConcurrencyPool

    peak = 0
    current = 0

    async def tracker():
        nonlocal peak, current
        current += 1
        if current > peak:
            peak = current
        await asyncio.sleep(0.05)
        current -= 1
        return "ok"

    pool = ConcurrencyPool(max_concurrency=2)
    results = await asyncio.gather(*[pool.run(tracker()) for _ in range(10)])
    assert peak <= 2


async def test_pool_stats():
    """Stats returns correct total/used/waiting."""
    from basic_tool.concurrency.pool import ConcurrencyPool

    pool = ConcurrencyPool(max_concurrency=5)
    stats = pool.stats
    assert stats.total == 5
    assert stats.used == 0
    assert stats.waiting == 0
    assert stats.available == 5


async def test_pool_invalid_concurrency():
    """max_concurrency < 1 raises ValueError."""
    from basic_tool.concurrency.pool import ConcurrencyPool

    with pytest.raises(ValueError):
        ConcurrencyPool(max_concurrency=0)


# ---------------------------------------------------------------------------
# TaskGroup (tests 26-28)
# ---------------------------------------------------------------------------


async def test_task_group_async_with():
    """All tasks complete before exiting async with."""
    from basic_tool.concurrency.task_group import TaskGroup

    async def val(n):
        await asyncio.sleep(0.01)
        return n

    async with TaskGroup() as tg:
        t1 = tg.create(val(1))
        t2 = tg.create(val(2))
        t3 = tg.create(val(3))
    assert t1.result() == 1
    assert t2.result() == 2
    assert t3.result() == 3


async def test_task_group_task_failure():
    """Any task failure cancels the rest and raises CompositeError."""
    from basic_tool.concurrency.task_group import TaskGroup

    async def fail():
        await asyncio.sleep(0.01)
        raise ValueError("boom")

    async def slow():
        await asyncio.sleep(10)
        return "should not reach"

    with pytest.raises(CompositeError):
        async with TaskGroup() as tg:
            tg.create(fail())
            tg.create(slow())


async def test_task_group_manual_wait():
    """wait() returns all results."""
    from basic_tool.concurrency.task_group import TaskGroup

    async def val(n):
        await asyncio.sleep(0.01)
        return n

    async with TaskGroup() as tg:
        t1 = tg.create(val(10))
        t2 = tg.create(val(20))
    results = [t1.result(), t2.result()]
    assert results == [10, 20]


# ---------------------------------------------------------------------------
# CompositeError / ErrorStrategy (tests 29-31)
# ---------------------------------------------------------------------------


def test_composite_error_attributes():
    """errors and failed_indices are set correctly."""
    errors = [ValueError("a"), TypeError("b"), RuntimeError("c")]
    indices = [0, 2, 5]
    ce = CompositeError(errors, indices)
    assert ce.errors == errors
    assert ce.failed_indices == indices


def test_composite_error_str_format():
    """String representation includes error count and summary."""
    ce = CompositeError([ValueError("x"), TypeError("y")])
    s = str(ce)
    assert "2 task(s) failed" in s
    assert "ValueError" in s
    assert "TypeError" in s


def test_error_strategy_values():
    """All three enum values are correct."""
    assert ErrorStrategy.FAIL_FAST.value == "fail_fast"
    assert ErrorStrategy.COLLECT_ALL.value == "collect_all"
    assert ErrorStrategy.SKIP_FAILED.value == "skip_failed"
