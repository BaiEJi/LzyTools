# Learnings

## Project Conventions
- `basic_tool/` packages use Pydantic BaseModel for configs (but LogConfig uses dataclass)
- File-level docstrings in Chinese are standard
- Method docstrings include Args/Returns/Raises sections
- Re-export pattern: `__init__.py` flat imports + `__all__` list
- Test framework: pytest + pytest-asyncio (asyncio_mode="auto")
- Loguru `logger.bind(**extra)` pattern for structured logging
- Mixin pattern for organizing class methods by category

## Key Files
- `basic_tool/fastapi/middleware.py` — OLD AppError (positional args: status_code, detail)
- `basic_tool/fastapi/__init__.py:41` — re-exports AppError from middleware
- `basic_tool/fastapi/app.py:18` — imports setup_error_handlers from middleware
- `basic_tool/fastapi/app.py:163-164` — call site for setup_error_handlers

## Design Decisions
- NEW AppError: keyword args (code, message, http_status, context)
- `.detail` property → returns `.message` (backward compat)
- `.status_code` property → returns `.http_status` (backward compat, Metis catch)
- registry.py uses delayed import of AppError at bottom of file (avoid circular dep)
- `clear_registry()` required as autouse fixture in all test files
- `log_error` is internal — not exported from __init__.py

## [Session: errors package regeneration] — 2026-06-13

### Implementation Completed
- 7 files created under `basic_tool/errors/`: config.py, app_error.py, registry.py, codes.py, log.py, handler.py, __init__.py
- ErrorConfig uses Pydantic BaseModel (unlike LogConfig which uses dataclass — spec-driven choice)
- ErrorEntry is a frozen dataclass with `__post_init__` auto-registration (raises ValueError on duplicate code)
- ErrorEntry is callable: `CommonErrors.PARAM_MISSING(param='username')` returns an AppError with kwargs as context
- CommonErrors has exactly 15 entries: 3×400, 3×401, 2×403, 3×resource(404/409/409), 1×429, 3×5xx(500/503/504)
- handler.py uses delayed import of CommonErrors inside the nested handler functions (avoids import-time dependency)
- `__init__.py` does NOT export `log_error` (internal) or `_global_registry` (private)

### Verification Results
- All 4 verification commands passed (imports, 15 codes count, alias properties, template rendering)
- LSP diagnostics: 0 errors across 7 files
- Key invariant: importing `basic_tool.errors` triggers codes.py which populates the global registry with 15 entries

### Convention Confirmed
- File-level docstrings in Chinese (triple-quote)
- Method docstrings include Args/Returns/Raises sections
- `__all__` in `__init__.py` uses flat list matching re-export names
- Delayed imports used to break circular deps: registry.py (AppError at bottom), log.py + handler.py (AppError/CommonErrors inside functions)
