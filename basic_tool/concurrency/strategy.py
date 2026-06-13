"""Error handling strategy enum for concurrent task execution."""

from enum import Enum


class ErrorStrategy(str, Enum):
    """Strategy for handling errors in concurrent task execution.

    Values:
        FAIL_FAST: Cancel remaining tasks on first error.
        COLLECT_ALL: Wait for all tasks, then raise CompositeError with all failures.
        SKIP_FAILED: Skip failed tasks, return successful results only.
    """

    FAIL_FAST = "fail_fast"
    COLLECT_ALL = "collect_all"
    SKIP_FAILED = "skip_failed"
