"""Concurrency module configuration."""

from pydantic import BaseModel


class ConcurrencyConfig(BaseModel):
    """Configuration for concurrency operations.

    Attributes:
        max_concurrency: Maximum number of concurrent tasks.
        default_timeout: Default timeout in seconds for operations.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base delay for exponential backoff (seconds).
        backoff_cap: Maximum backoff delay (seconds).
    """

    max_concurrency: int = 10
    default_timeout: float = 30.0
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_cap: float = 60.0
