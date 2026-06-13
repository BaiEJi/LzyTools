# Learnings — id-generator-module

## 2026-06-12 Session Start

### Codebase Conventions
- Pydantic BaseModel for config classes (see `basic_tool/task_queue/config.py`)
- `__init__.py` pattern: module-level docstring (Chinese) + absolute imports + `__all__` (see `basic_tool/task_queue/__init__.py`)
- Tests: class-based grouping, plain assert, pytest fixtures (see `tests/task_queue/test_queue.py`)
- pytest config: `asyncio_mode = "auto"` in `pyproject.toml`

### Key Findings
- pyproject.toml version already `0.5.0` — no upgrade needed
- Design doc at `doc/basic_tool_id_generator_design.md` provides near-complete reference code
- 4 bug fixes from Metis review:
  1. Remove `import os` from generator.py (unused)
  2. Remove duplicate worker_id validation in IDGenerator.__init__ (Pydantic handles it)
  3. Fix `new()` docstring — remove `Raises: RuntimeError` (code uses spin-wait, not exception)
  4. Add hex format validation to `from_traceparent` (design doc missing)

### Task 2 — generator.py Creation
- Snowflake constants use module-level `_UPPER_CASE` convention (not class-level)
- `_next_id_unlocked()` is called inside lock; public methods (`new`, `batch`) acquire the lock
- `batch()` acquires lock once for all IDs — much more efficient than N calls to `new()`
- Clock drift protection: spin-wait (`_wait_next_ms`) instead of raising exception
- TraceGenerator is stateless — just delegates to `TraceContext` and `secrets.token_hex`
- `_MAX_WORKER_ID` constant exists but is NOT used in `__init__` — Pydantic validates via `IDConfig`
