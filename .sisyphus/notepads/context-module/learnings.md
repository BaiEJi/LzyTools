# Context Module - Learnings

## Codebase Patterns
- Tests: class-based, Chinese docstrings, plain `assert`, `async def test_xxx(self)` (pytest-asyncio auto mode)
- `__init__.py`: Chinese module docstring + absolute imports + `__all__` list (no grouped comments in redis, but design doc specifies grouped)
- `basic_tool/__init__.py`: docstring-only, lists subpackages — NO imports
- Logger: loguru-based, custom logfmt format `level||file:line||k1=v1||message`
- Logger test: uses `io.StringIO()` for capturing log output

## Design Doc Reference
- Full verbatim code provided in `doc/basic_tool_context_design.md`
- CRITICAL BUG in log_extra.py: `logger.patch()` returns new logger, original unchanged
  - Fix: `patched = logger.patch(_inject_context); logger._options = patched._options`
- `_context_tokens` ContextVar in design doc appears unused — design doc has it but ctx.py only uses single token per context level

## TDD RED Phase Test Patterns (Task 1)
- Deferred imports (method-level `from basic_tool.context.xxx import ...`) are REQUIRED for --collect-only to work when modules don't exist yet
- Top-level imports limited to installed deps: `asyncio`, `StringIO`, `FastAPI`, `TestClient`, `loguru.logger`
- Inner route handler functions in middleware tests must NOT have `test_` prefix (would inflate `grep -c "def test_"` count)
- Used `get_ctx` as inner route handler name in TestMiddleware tests
- Async tests: `async def test_xxx(self)` — no decorator needed (pyproject.toml has `asyncio_mode = "auto"`)
- Log injection test uses StringIO sink with `format="{extra[request_id]}|{message}"` to verify injected extras
- All 25 tests fail on ModuleNotFoundError at runtime (expected RED phase behavior)
- File structure: 7 test classes (TestContextBasic, TestContextNesting, TestContextAsync, TestContextUtilities, TestLogInjection, TestPropagation, TestMiddleware, TestConcurrency)

## Task 4: ctx.py GREEN Phase (2026-06-13)
- Implementation: 140 lines total. Clean, no comments beyond docstrings.
- `ContextVar[dict]` with `default={}` is safe for tests because:
  - All `ctx.set()`/`ctx.clear()` calls happen inside `request_context()` (where ContextVar has been set to a fresh dict)
  - The shared default `{}` is never mutated in test scenarios
  - Production code calling `ctx.set()` outside `request_context` would mutate the shared default — known footgun but out of scope for ctx.py (would need `_SENTINEL` default + `get()` returning fresh dict, but spec explicitly uses `default={}`)
- Nesting works via copy-on-enter: `{**current, **self._data}` creates NEW dict per level; `reset(token)` restores outer dict reference
- `ctx.set()` mutates current dict in place — mutations discarded on exit because outer dict reference is restored
- Type annotation `self._token: Any = None` needed to silence Pyright's `reportArgumentType` on `_context_data.reset(self._token)` (token lifecycle: set in `__enter__` before `__exit__` calls reset)
- TestConcurrency::test_concurrent_isolation ALSO passes (bonus) — only needs ctx + request_context, doesn't need middleware
- Evidence saved: `.sisyphus/evidence/task-4-ctx-green.txt` (13 passed, 12 deselected)

## Task 6: propagation.py (2026-06-13)
- Implementation: 113 lines. No comments beyond required docstrings.
- Spec provided verbatim in task prompt — implementation matches exactly
- `_DEFAULT_HEADER_MAP` is module-level constant dict (4 keys)
- `get_propagation_headers`: iterates header_map, only includes keys PRESENT in context, str() conversion for values
- `inject_headers_to_httpx`: `{**ctx_headers, **headers}` — user headers win (dict merge right-to-left overwrite)
- `serialize_context`: delegates to `_context_data.get().copy()` (shallow copy, same as ctx.getall)
- `deserialize_context`: delegates to `request_context(**data)` — reuses existing context manager factory, so cleanup/exit semantics are automatic
- deserialize_context test_deserialize_context_cleanup works because _RequestContext.__exit__ calls `_context_data.reset(token)`, restoring the previous (empty) dict reference
- All 7 Propagation tests pass (14-20): evidence at `.sisyphus/evidence/task-6-propagation.txt`

## Task 5: log_extra.py (2026-06-13)
- Implementation: 70 lines. Clean, docstrings only (required by CLAUDE.md).
- `_inject_context(record: dict) -> None`: iterates `_context_data.get().items()`, skips keys already in `record["extra"]` (user extras win).
- `enable_log_injection() -> None`: BUG FIX — `loguru.logger.patch()` returns NEW Core instance; naive call is no-op. Fix: copy `patched._options` back to `loguru.logger._options`.
- `import loguru` placed INSIDE `enable_log_injection()` (function-level) — matches task spec, avoids module-level side-effect concerns.
- Verified: `pytest -k LogInjection` passes; no regression on ctx.py tests (21 pass, 4 TestMiddleware failures are pre-existing — middleware.py not yet implemented).
- Evidence: `.sisyphus/evidence/task-5-log-injection.txt`

## Task 7: middleware.py
- `request_context()` (sync `with`) works correctly inside `async def dispatch` — no need for `async with`.
- `BaseHTTPMiddleware` already handles `__init__`; only override `dispatch`.
- TestClient sets `request.client.host` to "testclient" → client_ip is non-None as expected.
- Import path: `from basic_tool.context.ctx import request_context`.
- Single goal completed: 4 Middleware + 1 Concurrency tests pass.
