# Learnings — concurrency-module

## Project Conventions
- Exception classes: simple class definitions with docstrings (see `crypto/exceptions.py`)
- Config classes: Pydantic BaseModel with field-level comments (see `crypto/config.py`)
- `__init__.py`: docstring → imports → `__all__` pattern (see `crypto/__init__.py`)
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed
- No conftest.py for tests/concurrency/
- Code comments in English only
- File-level docstrings required for all modules
- Method docstrings required for all public methods

## Design Bug Fixes
1. `gather_with_retry`: Change from `*coros: Coroutine` to `*coro_factories: Callable[[], Coroutine]` to avoid re-await crash
2. `pool.py`: Implement `_waiting` counter — increment before semaphore.acquire(), decrement after acquire
3. `CompositeError.__str__`: Guard against `failed_indices` shorter than `errors`
