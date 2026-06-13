"""Concurrency module exception types."""

from __future__ import annotations


class CompositeError(Exception):
    """Aggregates multiple task errors into a single exception.

    Attributes:
        errors: List of exceptions from failed tasks.
        failed_indices: Original indices of failed tasks.
    """

    def __init__(
        self,
        errors: list[BaseException],
        failed_indices: list[int] | None = None,
    ) -> None:
        self.errors = errors
        self.failed_indices = failed_indices if failed_indices is not None else list(range(len(errors)))
        super().__init__(f"{len(self.errors)} task(s) failed")

    def __str__(self) -> str:
        lines = [f"{len(self.errors)} task(s) failed:"]
        for i in range(len(self.errors)):
            idx = self.failed_indices[i] if i < len(self.failed_indices) else i
            err = self.errors[i]
            lines.append(f"  [{idx}] {type(err).__name__}: {err}")
        return "\n".join(lines)
