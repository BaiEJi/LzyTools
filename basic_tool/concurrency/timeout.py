"""Timeout utilities for async operations."""

import asyncio
from typing import TypeVar

T = TypeVar("T")


async def with_timeout(
    coro: object,
    timeout: float,
    *,
    message: str = "",
) -> T:
    """Execute a coroutine with a timeout.

    Args:
        coro: The coroutine to execute.
        timeout: Maximum time in seconds to wait. Must be > 0.
        message: Custom message for TimeoutError. Defaults to empty string.

    Returns:
        The coroutine's return value.

    Raises:
        ValueError: If timeout <= 0.
        TimeoutError: If the coroutine exceeds the timeout.
    """
    if timeout <= 0:
        raise ValueError(f"timeout must be > 0, got {timeout}")

    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        msg = message or f"Operation timed out after {timeout}s"
        raise TimeoutError(msg) from None
