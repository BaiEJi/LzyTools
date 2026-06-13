"""TaskGroup for managed concurrent task execution with error aggregation."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

from basic_tool.concurrency.exceptions import CompositeError

T = TypeVar("T")


class TaskGroup:
    """Wraps asyncio.TaskGroup with CompositeError conversion.

    Provides a managed context for creating and awaiting concurrent tasks.
    On exit, if any tasks failed, raises CompositeError instead of
    BaseExceptionGroup.
    """

    def __init__(self) -> None:
        self._tg: asyncio.TaskGroup | None = None

    async def __aenter__(self) -> TaskGroup:
        """Enter the task group context."""
        self._tg = asyncio.TaskGroup()
        await self._tg.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit the task group, converting errors to CompositeError."""
        if self._tg is None:
            return False

        try:
            await self._tg.__aexit__(exc_type, exc_val, exc_tb)
        except BaseExceptionGroup as eg:
            errors: list[BaseException] = []
            for exc in eg.exceptions:
                errors.append(exc)
            raise CompositeError(errors) from None

        return False

    def create(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        """Create a task within the group.

        Args:
            coro: The coroutine to schedule.

        Returns:
            An asyncio.Task that will complete within the group context.
        """
        assert self._tg is not None, "TaskGroup must be used as async context manager"
        return self._tg.create_task(coro)
