# Implement basic_tool.errors Module

## TL;DR

> **Quick Summary**: Create `basic_tool/errors/` package providing standardized error codes, `AppError` exception base class, error registry with IDE auto-completion, FastAPI global exception handlers, and loguru-based log integration. Replace the existing simple `AppError` in `basic_tool/fastapi/middleware.py`.
> 
> **Deliverables**:
> - `basic_tool/errors/` package (7 source files)
> - `tests/errors/` test suite (5 test files, 25 test cases)
> - `basic_tool/errors/README.md` documentation
> - Deprecated shim in `middleware.py` + import path update in `app.py`
> - Updated `tests/test_fastapi/test_middleware.py` for new API
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8

---

## Context

### Original Request
User provided a complete 973-line design doc (`doc/basic_tool_errors_design.md`) specifying the entire `basic_tool/errors/` module: source code, tests, integration points, API reference, and migration guide.

### Interview Summary
**Key Discussions**:
- No interview needed — design doc is implementation-ready
- Intent classification: Build from Scratch with bounded migration

**Research Findings**:
- Existing `AppError` in `basic_tool/fastapi/middleware.py` is simple: `status_code` + `detail` positional args
- `setup_error_handlers(app)` already exists in middleware.py, registers 3 handlers
- `app.py` line 164 calls `setup_error_handlers(app)` gated by `config.enable_error_handlers`
- `basic_tool/fastapi/__init__.py` re-exports `AppError` — backward compat required
- Test framework: pytest + pytest-asyncio (asyncio_mode="auto")
- Dependencies confirmed: fastapi>=0.100.0, pydantic>=2.0.0, loguru>=0.7.0
- Zero new dependencies needed

### Metis Review
**Identified Gaps** (addressed):
- **Missing `.status_code` property alias**: Design doc only added `.detail` alias. Added `.status_code` alias to new `AppError` for backward compat.
- **AppError constructor breaking change**: Old `AppError(404, "msg")` positional args → new `AppError(code="...", message="...", http_status=400)` keyword args. Resolution: update existing `test_middleware.py` call sites (only 3 occurrences in the entire repo).
- **Response format change**: `{"detail": "..."}` → `{"code": "...", "message": "..."}`. This is **intentional** — the whole point of the module.
- **Global registry test pollution**: Added `clear_registry()` autouse fixture requirement to all test files.
- **Deprecated shim must be same class object**: `middleware.py` uses `from basic_tool.errors import AppError` (same identity, not a copy).
- **Circular import risk in registry.py**: Verified import chain is safe, but add explicit verification in Task 4.

---

## Work Objectives

### Core Objective
Implement the `basic_tool/errors/` module as specified in the design doc, with all source files, tests, documentation, and migration of existing code.

### Concrete Deliverables
- `basic_tool/errors/__init__.py` — flat re-exports
- `basic_tool/errors/config.py` — `ErrorConfig` pydantic model
- `basic_tool/errors/app_error.py` — `AppError` exception class (with `.detail` + `.status_code` aliases)
- `basic_tool/errors/registry.py` — `ErrorEntry`, `ErrorRegistry`, `check_conflicts()`, `get_all_entries()`, `clear_registry()`
- `basic_tool/errors/codes.py` — `CommonErrors` predefined codes
- `basic_tool/errors/log.py` — `log_error()` with loguru integration
- `basic_tool/errors/handler.py` — `setup_error_handlers()` FastAPI integration
- `basic_tool/errors/README.md` — module documentation
- `tests/errors/__init__.py`
- `tests/errors/test_app_error.py` — AppError tests (cases 1-5)
- `tests/errors/test_registry.py` — Registry tests (cases 6-13)
- `tests/errors/test_codes.py` — CommonErrors tests (cases 14-17)
- `tests/errors/test_handler.py` — Handler tests (cases 18-21)
- `tests/errors/test_log.py` — Log tests (cases 22-23)
- Updated `basic_tool/fastapi/middleware.py` — deprecated shim
- Updated `basic_tool/fastapi/app.py` — import path change
- Updated `basic_tool/fastapi/__init__.py` — re-export from errors
- Updated `tests/test_fastapi/test_middleware.py` — new API compatibility

### Definition of Done
- [ ] `pytest tests/errors/ -v` → 25 passed, 0 failed
- [ ] `pytest tests/ -v` → all tests pass (full regression)
- [x] `python -c "from basic_tool.errors import AppError, ErrorRegistry, ErrorEntry, CommonErrors, ErrorConfig, setup_error_handlers, check_conflicts"` succeeds
- [x] `from basic_tool.fastapi import AppError as A; from basic_tool.errors import AppError as B; assert A is B` passes

### Must Have
- All 7 source files matching design doc sections 3.1–3.7
- All 25 test cases passing per design doc section 7
- `.detail` AND `.status_code` property aliases on new `AppError` (Metis catch)
- `clear_registry()` autouse fixture in every test file under `tests/errors/`
- Deprecated `middleware.py` exports same class object as `basic_tool.errors.AppError`
- `README.md` documenting all public APIs per project convention
- All methods have docstrings per CLAUDE.md project constraints

### Must NOT Have (Guardrails)
- NO new dependencies (zero — only fastapi, pydantic, loguru already in project)
- NO changes to `FastApiConfig` (no `ErrorConfig` field — out of scope)
- NO changes to `basic_tool/fastapi/README.md` (flag for follow-up, not this plan)
- NO changes to files under `basic_tool/` other than `middleware.py`, `app.py`, `__init__.py` in fastapi package
- NO wrapper class or factory function for backward compat — direct import alias only
- NO AI slop: excessive comments, over-abstraction, generic variable names
- Every modified file must still have file-level docstring

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio)
- **Automated tests**: YES (TDD not needed — design doc provides exact test cases)
- **Framework**: pytest with asyncio_mode="auto"

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Python modules**: Use Bash — import, instantiate, call methods, assert output
- **FastAPI handlers**: Use Bash (pytest + httpx TestClient) — send requests, assert status + JSON
- **Tests**: Use Bash — run pytest, verify pass/fail counts

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation, no cross-deps):
├── Task 1: config.py + app_error.py [quick]
├── Task 2: registry.py [quick]

Wave 2 (After Wave 1 — depends on foundation):
├── Task 3: codes.py (depends: 2) [quick]
├── Task 4: log.py (depends: 1) [quick]
├── Task 5: handler.py (depends: 1, 4) [quick]

Wave 3 (After Wave 2 — integration + tests + migration):
├── Task 6: __init__.py + import chain verification (depends: 1-5) [quick]
├── Task 7: tests/errors/ — all 5 test files (depends: 6) [unspecified-high]
├── Task 8: Migration — middleware.py + app.py + __init__.py + test_middleware.py (depends: 6) [unspecified-high]
├── Task 9: README.md (depends: 6) [writing]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay

Critical Path: Task 1 → Task 2 → Task 3 → Task 5 → Task 6 → Task 7 → Task 8 → FINAL
Parallel Speedup: ~40% faster than sequential
Max Concurrent: 4 (Wave 3)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 4, 5, 6 | 1 |
| 2 | — | 3, 6 | 1 |
| 3 | 2 | 6 | 2 |
| 4 | 1 | 5, 6 | 2 |
| 5 | 1, 4 | 6 | 2 |
| 6 | 1-5 | 7, 8, 9 | 3 |
| 7 | 6 | FINAL | 3 |
| 8 | 6 | FINAL | 3 |
| 9 | 6 | FINAL | 3 |

### Agent Dispatch Summary

- **Wave 1**: 2 tasks — T1 `quick`, T2 `quick`
- **Wave 2**: 3 tasks — T3 `quick`, T4 `quick`, T5 `quick`
- **Wave 3**: 4 tasks — T6 `quick`, T7 `unspecified-high`, T8 `unspecified-high`, T9 `writing`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. Create `config.py` + `app_error.py` — Foundation

  **What to do**:
  - Create directory `basic_tool/errors/`
  - Create `basic_tool/errors/config.py` — `ErrorConfig(BaseModel)` with 3 fields: `include_context: bool = False`, `log_5xx_stack: bool = True`, `log_4xx_summary: bool = True`. Exact code from design doc section 3.1.
  - Create `basic_tool/errors/app_error.py` — `AppError(Exception)` with: `__init__(self, code: str, message: str, http_status: int = 400, context: dict | None = None)`, `@property detail -> str` (returns `self.message`), `@property status_code -> int` (returns `self.http_status` — **Metis catch, not in original design**), `to_dict(include_context: bool = False) -> dict`. Exact code from design doc section 3.2, plus the additional `status_code` property.
  - Both files must have file-level docstrings and all methods must have docstrings per CLAUDE.md.

  **Must NOT do**:
  - Do NOT add any import of `registry.py` or other files — this is a leaf dependency.
  - Do NOT add methods beyond what the design doc specifies (plus `status_code` property).

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Two small files, clear spec, minimal logic.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 5, 6
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `basic_tool/logger/config.py` — Pydantic BaseModel config pattern in this codebase. Note the docstring style and field annotations.
  - `basic_tool/fastapi/middleware.py:18-35` — The OLD `AppError` class being replaced. Note: `status_code` and `detail` attributes that must be aliased in the new class.

  **Design Doc References** (exact code to implement):
  - `doc/basic_tool_errors_design.md:69-96` — Section 3.1 config.py complete code
  - `doc/basic_tool_errors_design.md:98-168` — Section 3.2 app_error.py complete code (add `status_code` property after `detail` property)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Import config and app_error modules successfully
    Tool: Bash
    Preconditions: basic_tool/errors/ directory exists
    Steps:
      1. Run: python -c "from basic_tool.errors.config import ErrorConfig; c = ErrorConfig(); assert c.include_context is False; assert c.log_5xx_stack is True; assert c.log_4xx_summary is True; print('config OK')"
      2. Run: python -c "from basic_tool.errors.app_error import AppError; e = AppError(code='TEST', message='test msg', http_status=404); assert e.code == 'TEST'; assert e.message == 'test msg'; assert e.http_status == 404; assert e.context == {}; print('app_error OK')"
    Expected Result: Both commands print "OK"
    Failure Indicators: ImportError, AssertionError
    Evidence: .sisyphus/evidence/task-1-import-check.txt

  Scenario: Backward compat aliases work
    Tool: Bash
    Preconditions: app_error.py created
    Steps:
      1. Run: python -c "from basic_tool.errors.app_error import AppError; e = AppError(code='TEST', message='hello', http_status=404); assert e.detail == 'hello'; assert e.status_code == 404; print('aliases OK')"
    Expected Result: Prints "aliases OK"
    Failure Indicators: AttributeError on .detail or .status_code
    Evidence: .sisyphus/evidence/task-1-aliases.txt

  Scenario: Error chain preservation
    Tool: Bash
    Preconditions: app_error.py created
    Steps:
      1. Run: python -c "
try:
    raise ValueError('original')
except ValueError as e:
    from basic_tool.errors.app_error import AppError
    ae = AppError(code='CHAIN', message='wrapped', http_status=500)
    raise ae from e
" 2>&1 | head -1
    Expected Result: Shows AppError traceback with "The above exception was the direct cause of the following exception"
    Failure Indicators: Error chain not preserved
    Evidence: .sisyphus/evidence/task-1-error-chain.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add AppError exception class and ErrorConfig`
  - Files: `basic_tool/errors/config.py`, `basic_tool/errors/app_error.py`

- [x] 2. Create `registry.py` — ErrorEntry + ErrorRegistry

  **What to do**:
  - Create `basic_tool/errors/registry.py` containing:
    - Module-level `_global_registry: dict[str, ErrorEntry] = {}`
    - `ErrorEntry` frozen dataclass: `code: str`, `message_template: str`, `http_status: int = 400`. Methods: `__post_init__` (registers to global, detects duplicates), `__call__(**kwargs) -> AppError` (renders message template), `__repr__`.
    - `ErrorRegistry` class: `entries() -> dict[str, ErrorEntry]` (returns class attrs that are ErrorEntry), `codes() -> list[str]`.
    - `check_conflicts() -> None` (scans global registry for duplicates, raises ValueError).
    - `get_all_entries() -> dict[str, ErrorEntry]` (returns copy of global registry).
    - `clear_registry() -> None` (clears global registry, test-only).
    - Bottom-of-file import: `from basic_tool.errors.app_error import AppError` (delayed to avoid circular dep).
  - Must have file-level docstring and all method docstrings.
  - Exact code from design doc section 3.3.

  **Must NOT do**:
  - Do NOT import `AppError` at top of file — use bottom-of-file delayed import.
  - Do NOT add thread-safety mechanisms — not in scope.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, clear spec, straightforward logic.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 3, 6
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `basic_tool/redis/client/__init__.py` — Example of how this codebase organizes class + mixin composition. Note the import style and re-export pattern.

  **Design Doc References**:
  - `doc/basic_tool_errors_design.md:170-320` — Section 3.3 registry.py complete code

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: ErrorEntry creates and registers correctly
    Tool: Bash
    Preconditions: registry.py created, global registry is empty
    Steps:
      1. Run: python -c "
from basic_tool.errors.registry import ErrorEntry, get_all_entries, clear_registry
clear_registry()
entry = ErrorEntry('TEST_CODE', 'test message {name}', 400)
assert entry.code == 'TEST_CODE'
assert 'TEST_CODE' in get_all_entries()
print('entry OK')
"
    Expected Result: Prints "entry OK"
    Failure Indicators: ValueError (duplicate), KeyError
    Evidence: .sisyphus/evidence/task-2-entry.txt

  Scenario: ErrorEntry __call__ renders message
    Tool: Bash
    Preconditions: registry.py created
    Steps:
      1. Run: python -c "
from basic_tool.errors.registry import ErrorEntry, clear_registry
clear_registry()
entry = ErrorEntry('TEST', 'Hello {name}, you are {age}', 200)
err = entry(name='Alice', age=30)
assert err.message == 'Hello Alice, you are 30'
assert err.code == 'TEST'
assert err.http_status == 200
assert err.context == {'name': 'Alice', 'age': 30}
print('call OK')
"
    Expected Result: Prints "call OK"
    Failure Indicators: KeyError (template mismatch), AssertionError
    Evidence: .sisyphus/evidence/task-2-call.txt

  Scenario: Duplicate code detection
    Tool: Bash
    Preconditions: registry.py created
    Steps:
      1. Run: python -c "
from basic_tool.errors.registry import ErrorEntry, clear_registry
clear_registry()
ErrorEntry('DUP', 'first', 400)
try:
    ErrorEntry('DUP', 'second', 400)
    print('FAIL - no error raised')
except ValueError as e:
    assert 'Duplicate error code' in str(e)
    print('dup detection OK')
" 2>&1
    Expected Result: Prints "dup detection OK"
    Failure Indicators: "FAIL" printed, or no error raised
    Evidence: .sisyphus/evidence/task-2-duplicate.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add ErrorEntry and ErrorRegistry`
  - Files: `basic_tool/errors/registry.py`

- [x] 3. Create `codes.py` — CommonErrors Predefined Codes

  **What to do**:
  - Create `basic_tool/errors/codes.py` with `CommonErrors(ErrorRegistry)` class.
  - Define all 15 error entries per design doc section 3.4:
    - PARAM_MISSING, PARAM_INVALID, PARAM_TYPE_ERROR (400)
    - TOKEN_EXPIRED, TOKEN_INVALID, CREDENTIALS_ERROR (401)
    - PERMISSION_DENIED, ACCESS_FORBIDDEN (403)
    - RESOURCE_NOT_FOUND (404)
    - RESOURCE_ALREADY_EXISTS, VERSION_CONFLICT (409)
    - RATE_LIMITED (429)
    - INTERNAL_ERROR (500), SERVICE_UNAVAILABLE (503), UPSTREAM_TIMEOUT (504)
  - Must have file-level docstring and class docstring.

  **Must NOT do**:
  - Do NOT add error codes beyond the 15 specified.
  - Do NOT modify any other file.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, declarative definitions, no logic.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:

  **Design Doc References**:
  - `doc/basic_tool_errors_design.md:322-434` — Section 3.4 codes.py complete code

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All 15 CommonErrors entries exist and are callable
    Tool: Bash
    Preconditions: codes.py created
    Steps:
      1. Run: python -c "
from basic_tool.errors.codes import CommonErrors
from basic_tool.errors.registry import clear_registry
# Don't clear — CommonErrors is already registered at import time
entries = CommonErrors.entries()
expected = ['PARAM_MISSING', 'PARAM_INVALID', 'PARAM_TYPE_ERROR', 'TOKEN_EXPIRED', 'TOKEN_INVALID', 'CREDENTIALS_ERROR', 'PERMISSION_DENIED', 'ACCESS_FORBIDDEN', 'RESOURCE_NOT_FOUND', 'RESOURCE_ALREADY_EXISTS', 'VERSION_CONFLICT', 'RATE_LIMITED', 'INTERNAL_ERROR', 'SERVICE_UNAVAILABLE', 'UPSTREAM_TIMEOUT']
assert len(entries) == 15, f'Expected 15, got {len(entries)}'
for name in expected:
    assert name in entries, f'Missing {name}'
    entry = entries[name]
    assert entry.code == name
print('all 15 entries OK')
"
    Expected Result: Prints "all 15 entries OK"
    Failure Indicators: AssertionError with count or missing name
    Evidence: .sisyphus/evidence/task-3-codes.txt

  Scenario: CommonErrors entries with parameters render correctly
    Tool: Bash
    Preconditions: codes.py created
    Steps:
      1. Run: python -c "
from basic_tool.errors.codes import CommonErrors
err = CommonErrors.PARAM_MISSING(param='username')
assert err.code == 'PARAM_MISSING'
assert 'username' in err.message
assert err.http_status == 400

err2 = CommonErrors.RESOURCE_NOT_FOUND(resource='用户')
assert err2.code == 'RESOURCE_NOT_FOUND'
assert '用户' in err2.message
assert err2.http_status == 404

err3 = CommonErrors.TOKEN_EXPIRED()
assert err3.code == 'TOKEN_EXPIRED'
assert err3.http_status == 401
print('param rendering OK')
"
    Expected Result: Prints "param rendering OK"
    Failure Indicators: KeyError, AssertionError
    Evidence: .sisyphus/evidence/task-3-rendering.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add CommonErrors predefined codes`
  - Files: `basic_tool/errors/codes.py`

- [x] 4. Create `log.py` — Error Log Integration

  **What to do**:
  - Create `basic_tool/errors/log.py` with `log_error()` function.
  - Signature: `log_error(exc: Exception, *, config: ErrorConfig | None = None, request_method: str = "", request_path: str = "", request_id: str = "") -> None`.
  - Logic: AppError 5xx → ERROR + exc_info; AppError 4xx → WARNING; non-AppError → ERROR + exc_info.
  - Uses `loguru.logger.bind(**extra)` for structured context.
  - Exact code from design doc section 3.5.

  **Must NOT do**:
  - Do NOT add log levels beyond ERROR and WARNING.
  - Do NOT import anything from `handler.py` or `codes.py`.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single function, clear logic, straightforward.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 5)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `basic_tool/logger/logger.py` — Loguru usage pattern in this codebase. Note the `logger.bind()` style and `_formatter()` pattern.
  - `basic_tool/logger/config.py` — How log config is structured.

  **Design Doc References**:
  - `doc/basic_tool_errors_design.md:436-513` — Section 3.5 log.py complete code

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: log_error function imports and runs
    Tool: Bash
    Preconditions: log.py created
    Steps:
      1. Run: python -c "
from basic_tool.errors.log import log_error
from basic_tool.errors.app_error import AppError
# Call with 4xx — should not raise
log_error(AppError(code='TEST', message='test', http_status=400))
# Call with 5xx — should not raise
log_error(AppError(code='ERR', message='server err', http_status=500))
# Call with generic exception — should not raise
log_error(ValueError('oops'))
print('log_error OK')
"
    Expected Result: Prints "log_error OK" (loguru may output to stderr, that's fine)
    Failure Indicators: ImportError, unhandled exception
    Evidence: .sisyphus/evidence/task-4-log.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add log integration`
  - Files: `basic_tool/errors/log.py`

- [x] 5. Create `handler.py` — FastAPI Exception Handlers

  **What to do**:
  - Create `basic_tool/errors/handler.py` with `setup_error_handlers(app: FastAPI, config: ErrorConfig | None = None) -> None`.
  - Registers 3 handlers:
    - `AppError` → `JSONResponse(status_code=exc.http_status, content=exc.to_dict(...))`
    - `RequestValidationError` → converts to `PARAM_INVALID` format, returns 422
    - `Exception` → wraps as `INTERNAL_ERROR`, returns 500, logs original exception
  - Each handler calls `log_error()` for structured logging.
  - Extracts `request.state.request_id` for log context.
  - Exact code from design doc section 3.6.

  **Must NOT do**:
  - Do NOT register handlers for other exception types.
  - Do NOT expose internal exception details to client in the global handler.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single function with 3 inner handler definitions, clear spec.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 4)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 1, 4

  **References**:

  **Pattern References**:
  - `basic_tool/fastapi/middleware.py:76-135` — The OLD `setup_error_handlers` being replaced. Note the handler structure, response format, and exception handling approach. This is the code the new handler is replacing.

  **API/Type References**:
  - `basic_tool/fastapi/middleware.py:98` — Old handler accesses `exc.status_code` — confirms why `.status_code` alias is needed.

  **Design Doc References**:
  - `doc/basic_tool_errors_design.md:515-634` — Section 3.6 handler.py complete code

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: setup_error_handlers registers without error
    Tool: Bash
    Preconditions: handler.py created
    Steps:
      1. Run: python -c "
from fastapi import FastAPI
from basic_tool.errors.handler import setup_error_handlers
app = FastAPI()
setup_error_handlers(app)
print('handler setup OK')
"
    Expected Result: Prints "handler setup OK"
    Failure Indicators: ImportError, FastAPI registration error
    Evidence: .sisyphus/evidence/task-5-handler.txt

  Scenario: AppError handler returns correct response
    Tool: Bash
    Preconditions: handler.py created, FastAPI + httpx available
    Steps:
      1. Run: python -c "
from fastapi import FastAPI
from fastapi.testclient import TestClient
from basic_tool.errors.handler import setup_error_handlers
from basic_tool.errors.app_error import AppError

app = FastAPI()
setup_error_handlers(app)

@app.get('/test')
def test_route():
    raise AppError(code='TEST_ERR', message='test error', http_status=400)

client = TestClient(app)
resp = client.get('/test')
assert resp.status_code == 400
data = resp.json()
assert data['code'] == 'TEST_ERR'
assert data['message'] == 'test error'
assert 'context' not in data  # include_context defaults to False
print('app_error handler OK')
"
    Expected Result: Prints "app_error handler OK"
    Failure Indicators: Status mismatch, missing JSON fields
    Evidence: .sisyphus/evidence/task-5-app-error-handler.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add FastAPI exception handlers`
  - Files: `basic_tool/errors/handler.py`

- [x] 6. Create `__init__.py` — Package Exports + Import Chain Verification

  **What to do**:
  - Create `basic_tool/errors/__init__.py` with flat re-exports of all public APIs:
    - `AppError` (from `app_error`)
    - `ErrorConfig` (from `config`)
    - `ErrorRegistry`, `ErrorEntry`, `check_conflicts`, `get_all_entries`, `clear_registry` (from `registry`)
    - `CommonErrors` (from `codes`)
    - `setup_error_handlers` (from `handler`)
  - Define `__all__` list.
  - File-level docstring with usage examples.
  - After creating, **verify the full import chain** works: `python -c "from basic_tool.errors import AppError, ErrorRegistry, ErrorEntry, CommonErrors, ErrorConfig, setup_error_handlers, check_conflicts"`.

  **Must NOT do**:
  - Do NOT export `log_error` — it's internal (used by handler.py).
  - Do NOT export `_global_registry` — it's private.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file of imports + __all__, straightforward.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (depends on all Wave 2 completing)
  - **Blocks**: Tasks 7, 8, 9
  - **Blocked By**: Tasks 1, 2, 3, 4, 5

  **References**:

  **Pattern References**:
  - `basic_tool/fastapi/__init__.py` — Existing pattern for flat re-exports with `__all__`.
  - `basic_tool/redis/__init__.py` — Another example of re-export pattern in this codebase.

  **Design Doc References**:
  - `doc/basic_tool_errors_design.md:636-692` — Section 3.7 __init__.py complete code

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full import chain works
    Tool: Bash
    Preconditions: All source files created (Tasks 1-5 done)
    Steps:
      1. Run: python -c "from basic_tool.errors import AppError, ErrorRegistry, ErrorEntry, CommonErrors, ErrorConfig, setup_error_handlers, check_conflicts; print('all imports OK')"
    Expected Result: Prints "all imports OK"
    Failure Indicators: ImportError, circular import error
    Evidence: .sisyphus/evidence/task-6-import-chain.txt

  Scenario: __all__ exports correct
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python -c "
import basic_tool.errors as err_mod
expected = ['AppError', 'ErrorConfig', 'ErrorRegistry', 'ErrorEntry', 'check_conflicts', 'get_all_entries', 'clear_registry', 'CommonErrors', 'setup_error_handlers']
for name in expected:
    assert name in err_mod.__all__, f'{name} not in __all__'
    assert hasattr(err_mod, name), f'{name} not accessible'
print('__all__ OK')
"
    Expected Result: Prints "__all__ OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-6-all-exports.txt
  ```

  **Commit**: YES
  - Message: `feat(errors): add package exports`
  - Files: `basic_tool/errors/__init__.py`

- [x] 7. Create `tests/errors/` — Full Test Suite (25 test cases)

  **What to do**:
  - Create `tests/errors/__init__.py` (empty).
  - Create a conftest.py with an autouse fixture that calls `clear_registry()` before each test (prevents global registry pollution).
  - Create 5 test files per design doc section 7:

  **`tests/errors/test_app_error.py`** (cases 1-5):
  - Test AppError creation with all fields
  - Test `.detail` property alias
  - Test `.status_code` property alias (not in design doc — added per Metis)
  - Test `to_dict()` without context
  - Test `to_dict()` with context and `include_context=True`
  - Test error chain with `from e`

  **`tests/errors/test_registry.py`** (cases 6-13):
  - Test ErrorEntry creation and global registration
  - Test `__call__` without kwargs (message = template)
  - Test `__call__` with kwargs (message rendered)
  - Test duplicate code detection (ValueError)
  - Test `ErrorRegistry.entries()` returns correct dict
  - Test `ErrorRegistry.codes()` returns correct list
  - Test `check_conflicts()` no conflict → passes
  - Test `check_conflicts()` with conflict → ValueError
  - Test `clear_registry()` empties global registry

  **`tests/errors/test_codes.py`** (cases 14-17):
  - Test all CommonErrors entries are callable
  - Test `PARAM_MISSING` with param
  - Test `TOKEN_EXPIRED` without params
  - Test `RESOURCE_NOT_FOUND` with resource param

  **`tests/errors/test_handler.py`** (cases 18-21):
  - Test `setup_error_handlers` registers without error
  - Test AppError handler returns correct JSON + status
  - Test RequestValidationError handler returns 422 + PARAM_INVALID format
  - Test global Exception handler returns 500 + INTERNAL_ERROR (no leak)

  **`tests/errors/test_log.py`** (cases 22-23):
  - Test 5xx AppError logs at ERROR level (check loguru sink)
  - Test 4xx AppError logs at WARNING level (check loguru sink)

  **Must NOT do**:
  - Do NOT import from `basic_tool.fastapi.middleware` in these tests.
  - Do NOT skip the `clear_registry()` autouse fixture.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 5 test files with 25+ test cases, requires careful test writing following design doc section 7 and existing test patterns.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 8, 9)
  - **Parallel Group**: Wave 3
  - **Blocks**: FINAL
  - **Blocked By**: Task 6

  **References**:

  **Pattern References**:
  - `tests/test_fastapi/test_middleware.py` — Existing test file for the old AppError. Shows how tests are structured in this project: imports, class organization, assertions. Note the `TestClient` usage pattern for FastAPI handler tests.
  - `tests/conftest.py` — Root conftest showing fixture patterns.

  **Test References**:
  - `doc/basic_tool_errors_design.md:895-943` — Section 7 complete test plan with all 25 cases

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All 25 test cases pass
    Tool: Bash
    Preconditions: All 5 test files created
    Steps:
      1. Run: pytest tests/errors/ -v
    Expected Result: "25 passed" in output, 0 failed, 0 errors
    Failure Indicators: Any test FAIL or ERROR
    Evidence: .sisyphus/evidence/task-7-tests.txt

  Scenario: Tests are isolated (no registry pollution)
    Tool: Bash
    Preconditions: tests/errors/ created
    Steps:
      1. Run: pytest tests/errors/ -v --count=2 (or run twice)
      2. Verify both runs produce same results
    Expected Result: Both runs show 25 passed
    Failure Indicators: Second run fails (registry pollution)
    Evidence: .sisyphus/evidence/task-7-isolation.txt
  ```

  **Commit**: YES
  - Message: `test(errors): add test suite for errors module`
  - Files: `tests/errors/__init__.py`, `tests/errors/conftest.py`, `tests/errors/test_app_error.py`, `tests/errors/test_registry.py`, `tests/errors/test_codes.py`, `tests/errors/test_handler.py`, `tests/errors/test_log.py`

- [x] 8. Migration — Update middleware.py, app.py, fastapi/__init__.py, test_middleware.py

  **What to do**:
  This task migrates the existing codebase to use the new `basic_tool.errors` module while maintaining backward compatibility.

  **Step 1: Update `basic_tool/fastapi/middleware.py`**:
  - Replace the `AppError` class definition with: `from basic_tool.errors import AppError` (same class object, not a copy).
  - Replace the old `setup_error_handlers` function body with: `from basic_tool.errors import setup_error_handlers as _setup; _setup(app)`. Keep the function signature `setup_error_handlers(app: FastAPI)` for backward compat.
  - Add deprecation warning in docstrings.
  - Keep `RequestLoggingMiddleware` untouched.

  **Step 2: Update `basic_tool/fastapi/__init__.py`**:
  - Change `AppError` import from `basic_tool.fastapi.middleware` to `basic_tool.errors`. The re-export name stays the same.
  - Keep `RequestLoggingMiddleware` import from middleware unchanged.

  **Step 3: Update `basic_tool/fastapi/app.py`**:
  - Change import: `from basic_tool.fastapi.middleware import setup_error_handlers` → `from basic_tool.errors import setup_error_handlers`.
  - The call site at line 164 remains: `setup_error_handlers(app)` (new function accepts same args with defaults).

  **Step 4: Update `tests/test_fastapi/test_middleware.py`**:
  - Update `AppError` constructor calls from old positional `AppError(422, "Invalid input")` to new keyword `AppError(code="...", message="...", http_status=...)`.
  - Update response assertions from `resp.json()["detail"]` to `resp.json()["message"]` and check for `code` field.
  - All old tests must still pass after migration.

  **Must NOT do**:
  - Do NOT create a separate backward-compat `AppError` wrapper class — use direct import alias.
  - Do NOT modify `RequestLoggingMiddleware` or its tests.
  - Do NOT modify `FastApiConfig` or add `ErrorConfig` field.
  - Do NOT modify `basic_tool/fastapi/README.md`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Touches 4 existing files, requires careful migration to not break backward compatibility. Must verify old tests still pass.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 9)
  - **Parallel Group**: Wave 3
  - **Blocks**: FINAL
  - **Blocked By**: Task 6

  **References**:

  **Pattern References** (files being modified):
  - `basic_tool/fastapi/middleware.py:18-35` — OLD AppError class to be replaced with import
  - `basic_tool/fastapi/middleware.py:76-135` — OLD setup_error_handlers to be replaced with delegation
  - `basic_tool/fastapi/__init__.py:41` — Current import of AppError from middleware
  - `basic_tool/fastapi/app.py:18` — Current import of setup_error_handlers from middleware
  - `basic_tool/fastapi/app.py:163-164` — Call site for setup_error_handlers
  - `tests/test_fastapi/test_middleware.py:7` — Current imports in test file
  - `tests/test_fastapi/test_middleware.py` — All test methods that construct AppError or assert response format

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Backward compat — same class object
    Tool: Bash
    Preconditions: Migration complete
    Steps:
      1. Run: python -c "from basic_tool.fastapi import AppError as A; from basic_tool.errors import AppError as B; assert A is B; print('same class OK')"
    Expected Result: Prints "same class OK"
    Failure Indicators: AssertionError (different class objects)
    Evidence: .sisyphus/evidence/task-8-identity.txt

  Scenario: Old middleware tests still pass
    Tool: Bash
    Preconditions: test_middleware.py updated
    Steps:
      1. Run: pytest tests/test_fastapi/test_middleware.py -v
    Expected Result: All tests pass
    Failure Indicators: Any test FAIL or ERROR
    Evidence: .sisyphus/evidence/task-8-middleware-tests.txt

  Scenario: Full regression — all tests pass
    Tool: Bash
    Preconditions: All changes made
    Steps:
      1. Run: pytest tests/ -v
    Expected Result: All tests pass (0 failed, 0 errors)
    Failure Indicators: Any test FAIL or ERROR
    Evidence: .sisyphus/evidence/task-8-full-regression.txt

  Scenario: Property aliases work via old import path
    Tool: Bash
    Preconditions: Migration complete
    Steps:
      1. Run: python -c "
from basic_tool.fastapi import AppError
e = AppError(code='TEST', message='test', http_status=404)
assert e.detail == 'test'
assert e.status_code == 404
assert e.code == 'TEST'
print('old path aliases OK')
"
    Expected Result: Prints "old path aliases OK"
    Failure Indicators: AttributeError, AssertionError
    Evidence: .sisyphus/evidence/task-8-old-path-aliases.txt
  ```

  **Commit**: YES
  - Message: `refactor(fastapi): migrate to basic_tool.errors`
  - Files: `basic_tool/fastapi/middleware.py`, `basic_tool/fastapi/__init__.py`, `basic_tool/fastapi/app.py`, `tests/test_fastapi/test_middleware.py`

- [x] 9. Create `basic_tool/errors/README.md` — Module Documentation

  **What to do**:
  - Create `basic_tool/errors/README.md` per project convention (every `basic_tool/` sub-package must have one).
  - Document:
    - What the module does (standardized error codes, AppError, FastAPI integration, logging)
    - All public APIs with signatures and descriptions:
      - `AppError(code, message, http_status, context)` — properties: `.detail`, `.status_code`, method: `.to_dict()`
      - `ErrorConfig` — fields: `include_context`, `log_5xx_stack`, `log_4xx_summary`
      - `ErrorEntry(code, message_template, http_status)` — callable with `**kwargs`
      - `ErrorRegistry` — methods: `.entries()`, `.codes()`
      - `CommonErrors` — all 15 predefined entries with params
      - `setup_error_handlers(app, config)` — FastAPI integration
      - `check_conflicts()`, `get_all_entries()`, `clear_registry()` — module functions
    - Usage examples (from design doc section 5)
    - Migration guide (from design doc section 5.5)

  **Must NOT do**:
  - Do NOT include internal APIs (`log_error`, `_global_registry`).
  - Do NOT modify any source files.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation task, requires clear API documentation.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 8)
  - **Parallel Group**: Wave 3
  - **Blocks**: FINAL
  - **Blocked By**: Task 6

  **References**:

  **Pattern References**:
  - `basic_tool/redis/README.md` — Example of how README is structured in this codebase. Follow the same format.
  - `basic_tool/logger/README.md` — Another README example.

  **Content References**:
  - `doc/basic_tool_errors_design.md:694-753` — Section 4 API reference table
  - `doc/basic_tool_errors_design.md:755-880` — Section 5 usage examples and migration guide

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README exists and documents all public APIs
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: python -c "
import os
readme = open('basic_tool/errors/README.md').read()
# Check all public API names are mentioned
for name in ['AppError', 'ErrorConfig', 'ErrorEntry', 'ErrorRegistry', 'CommonErrors', 'setup_error_handlers', 'check_conflicts', 'get_all_entries', 'clear_registry']:
    assert name in readme, f'{name} not in README'
# Check it has sections
assert '## ' in readme or '# ' in readme
print('README OK')
"
    Expected Result: Prints "README OK"
    Failure Indicators: AssertionError (missing API name or sections)
    Evidence: .sisyphus/evidence/task-9-readme.txt
  ```

  **Commit**: YES
  - Message: `docs(errors): add README documentation`
  - Files: `basic_tool/errors/README.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, import check). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v`. Review all changed files for: missing docstrings, `as any`/type ignores, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify every method has docstring per CLAUDE.md constraints. Verify every module has file-level docstring.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | Docstrings [N/N] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration: import from both `basic_tool.errors` and `basic_tool.fastapi`, verify class identity, verify error handler catches both old and new imports. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(errors): add AppError exception class and ErrorConfig` — config.py, app_error.py
- **Wave 1**: `feat(errors): add ErrorEntry and ErrorRegistry` — registry.py
- **Wave 2**: `feat(errors): add CommonErrors predefined codes` — codes.py
- **Wave 2**: `feat(errors): add log integration and FastAPI handlers` — log.py, handler.py
- **Wave 3**: `feat(errors): add package exports and import chain` — __init__.py
- **Wave 3**: `test(errors): add test suite for errors module` — tests/errors/
- **Wave 3**: `refactor(fastapi): migrate to basic_tool.errors` — middleware.py, app.py, __init__.py, test_middleware.py
- **Wave 3**: `docs(errors): add README documentation` — README.md
- **Final**: `chore: full test suite regression` — verify all pass

---

## Success Criteria

### Verification Commands
```bash
# 1. Import chain works
python -c "from basic_tool.errors import AppError, ErrorRegistry, ErrorEntry, CommonErrors, ErrorConfig, setup_error_handlers, check_conflicts; print('OK')"
# Expected: OK

# 2. Backward compat identity
python -c "from basic_tool.fastapi import AppError as A; from basic_tool.errors import AppError as B; assert A is B; print('OK')"
# Expected: OK

# 3. Property aliases
python -c "from basic_tool.errors import AppError; e = AppError(code='TEST', message='test', http_status=404); assert e.detail == 'test'; assert e.status_code == 404; print('OK')"
# Expected: OK

# 4. New tests pass
pytest tests/errors/ -v
# Expected: 25 passed, 0 failed

# 5. Full regression passes
pytest tests/ -v
# Expected: all pass
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All errors module tests pass (32/32)
- [x] `basic_tool/errors/README.md` exists with all public APIs documented with all public APIs documented
- [x] Every method has docstring
- [x] Every module has file-level docstring
