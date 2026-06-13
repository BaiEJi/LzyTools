# Implement basic_tool.context Module

## TL;DR

> **Quick Summary**: Implement `basic_tool/context/` subpackage — a request-level context management module based on Python `contextvars`, with log injection, HTTP propagation, task queue serialization, and FastAPI middleware.
>
> **Deliverables**:
> - `basic_tool/context/ctx.py` — Core context manager (ContextManager singleton + request_context)
> - `basic_tool/context/log_extra.py` — Loguru context injection (with design doc bug fix)
> - `basic_tool/context/propagation.py` — HTTP header + task queue propagation
> - `basic_tool/context/middleware.py` — FastAPI request context middleware
> - `basic_tool/context/__init__.py` — Flat exports with `__all__`
> - `basic_tool/context/README.md` — Module documentation
> - `tests/context/__init__.py` — Test package
> - `tests/context/test_ctx.py` — 25 TDD test cases
> - `basic_tool/__init__.py` — Docstring update
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves + final verification
> **Critical Path**: Task 1 (TDD tests) → Task 2 (ctx.py) → Task 3 (log_extra.py) → Task 4 (propagation.py) → Task 5 (middleware.py) → Task 6 (__init__.py + README) → Task 7 (integration) → F1-F4

---

## Context

### Original Request
User provided a comprehensive design document (`doc/basic_tool_context_design.md`) with verbatim code for a `basic_tool/context/` module. The request is "实现它" (implement it).

### Interview Summary
**Key Discussions**:
- Design doc code is essentially complete — transcription + adjustment task
- Test strategy: TDD (RED-GREEN-REFACTOR) chosen by user
- All external deps (loguru, fastapi, httpx) already in `pyproject.toml` core dependencies

**Research Findings**:
- `basic_tool/context/` does NOT exist yet — clean slate
- Codebase uses absolute imports + `__all__` with grouped comments
- Tests: class-based, Chinese docstrings, plain `assert`, pytest-asyncio auto mode
- `basic_tool/__init__.py` is docstring-only — no imports, just lists subpackages
- `tests/context/__init__.py` must be created (design doc file list omits it)

### Metis Review
**Identified Gaps** (all addressed):
- 🔴 `enable_log_injection()` bug: `logger.patch()` returns a new logger, original is unchanged → Fixed by reassigning `loguru.logger._options` from the patched instance
- 🟡 `basic_tool/__init__.py` should only update docstring, NOT add imports → Applied as guardrail
- 🟡 `ContextMiddleware` overlaps with existing `RequestLoggingMiddleware` → Documented as known conflict, explicitly out of scope
- 🟡 Missing `tests/context/__init__.py` in file list → Added to deliverables
- 🟢 Cross-module `_context_data` coupling → Acceptable within subpackage, documented

---

## Work Objectives

### Core Objective
Implement the `basic_tool/context/` module as specified in the design doc, with the `enable_log_injection()` bug fix applied, using TDD workflow.

### Concrete Deliverables
- `basic_tool/context/ctx.py` — ContextManager + request_context (sync+async CM)
- `basic_tool/context/log_extra.py` — Loguru patch-based context injection (FIXED)
- `basic_tool/context/propagation.py` — HTTP header injection + task queue serialization
- `basic_tool/context/middleware.py` — FastAPI BaseHTTPMiddleware
- `basic_tool/context/__init__.py` — Flat exports
- `basic_tool/context/README.md` — API documentation
- `tests/context/__init__.py` — Empty package init
- `tests/context/test_ctx.py` — 25 test cases
- `basic_tool/__init__.py` — Docstring update only

### Definition of Done
- [ ] `pytest tests/context/ -v` → 25 passed
- [ ] `pytest tests/ -v` → All existing tests still pass
- [ ] `python -c "from basic_tool.context import ctx, request_context, enable_log_injection"` → no errors
- [ ] `python -c "from basic_tool.context import ContextMiddleware, setup_context_middleware"` → no errors

### Must Have
- All 5 source files implemented per design doc (with log_extra.py bug fix)
- All 25 test cases passing
- README.md following project convention (Chinese title, 模块结构, API 文档, 使用示例)
- `basic_tool/__init__.py` docstring updated to include `context`
- TDD approach: tests written BEFORE implementation

### Must NOT Have (Guardrails)
- ❌ Do NOT modify any file outside `basic_tool/context/`, `tests/context/`, `basic_tool/__init__.py` (docstring only)
- ❌ Do NOT add imports to `basic_tool/__init__.py` — only update the docstring
- ❌ Do NOT resolve the `ContextMiddleware` vs `RequestLoggingMiddleware` overlap
- ❌ Do NOT integrate context propagation into `http_client`, `task_queue`, or `fastapi` modules
- ❌ Do NOT add new entries to `pyproject.toml` dependencies
- ❌ Do NOT add `pytest.importorskip()` — all deps are core dependencies
- ❌ Do NOT add `as any`, `@ts-ignore`, empty catches, unused imports, or excessive comments
- ❌ Do NOT over-abstract — follow the design doc's single-class structure

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest >=8.0.0 + pytest-asyncio >=0.23.0 auto mode)
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest + pytest-asyncio
- **TDD Flow**: Each implementation task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Unit tests**: `pytest tests/context/test_ctx.py -v` (automated verification)
- **Import checks**: `python -c "from basic_tool.context import ..."` (bash)
- **Full regression**: `pytest tests/ -v` (bash)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — TDD RED phase: write all tests + scaffolding):
├── Task 1: Write all 25 test cases (tests/context/test_ctx.py) [deep]
├── Task 2: Create package scaffolding (__init__.py stubs) [quick]
└── Task 3: Write README.md [quick]

Wave 2 (After Wave 1 — TDD GREEN phase: implement source files, MAX PARALLEL):
├── Task 4: Implement ctx.py — core context management (depends: 1, 2) [deep]
├── Task 5: Implement log_extra.py — log injection (depends: 1, 2, 4) [unspecified-high]
├── Task 6: Implement propagation.py — HTTP + queue propagation (depends: 1, 2, 4) [unspecified-high]
├── Task 7: Implement middleware.py — FastAPI middleware (depends: 1, 2, 4) [unspecified-high]
└── Task 8: Finalize __init__.py exports + basic_tool/__init__.py docstring (depends: 2, 4, 5, 6, 7) [quick]

Wave 3 (After Wave 2 — integration verification):
└── Task 9: Full integration test + regression (depends: 4, 5, 6, 7, 8) [unspecified-high]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 4 → Task 5 → Task 8 → Task 9 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | 2 | 4, 5, 6, 7 | 1 |
| 2 | - | 1, 4, 5, 6, 7, 8 | 1 |
| 3 | - | - | 1 |
| 4 | 1, 2 | 5, 6, 7, 8, 9 | 2 |
| 5 | 1, 2, 4 | 8, 9 | 2 |
| 6 | 1, 2, 4 | 8, 9 | 2 |
| 7 | 1, 2, 4 | 8, 9 | 2 |
| 8 | 2, 4, 5, 6, 7 | 9 | 2 |
| 9 | 4, 5, 6, 7, 8 | F1-F4 | 3 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `deep`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 5 tasks — T4 → `deep`, T5 → `unspecified-high`, T6 → `unspecified-high`, T7 → `unspecified-high`, T8 → `quick`
- **Wave 3**: 1 task — T9 → `unspecified-high`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Write all 25 TDD test cases (tests/context/test_ctx.py)

  **What to do**:
  - Create `tests/context/test_ctx.py` with all 25 test cases from the design doc (Section 七)
  - Organize tests into classes: `TestContextBasic`, `TestContextNesting`, `TestContextAsync`, `TestLogInjection`, `TestPropagation`, `TestMiddleware`, `TestConcurrency`
  - Each test method MUST have a Chinese docstring describing the verification point
  - Use plain `assert` statements (NO unittest assertions)
  - Async tests use `async def test_xxx(self)` — no decorator needed (auto mode)
  - This is the RED phase — tests will FAIL until implementation is done
  - Test cases to implement:
    1. `request_context` basic usage — enter/exit lifecycle
    2. Auto-generate `request_id` when not provided
    3. `ctx.set()` dynamic add
    4. `ctx.getall()` complete snapshot
    5. Cleanup after exit — `with` block outer `getall()` returns `{}`
    6. Nested override — inner overrides, outer restores
    7. Nested new key — inner's new key disappears on exit
    8. `async with` usage
    9. asyncio Task inheritance — child inherits parent context
    10. `ctx.dump()` — no exception
    11. `ctx.clear()` — getall returns empty after clear
    12. `ctx.get()` default value — missing key returns default
    13. `enable_log_injection` — log extra includes context fields (using StringIO capture)
    14. `get_propagation_headers` — correct header mapping
    15. `get_propagation_headers` custom mapping
    16. `inject_headers_to_httpx` — merged includes context headers
    17. `inject_headers_to_httpx` user headers priority
    18. `serialize_context` — returns context dict
    19. `deserialize_context` — restores and `ctx.get()` works
    20. `deserialize_context` exit cleanup
    21. `ContextMiddleware` request_id extraction from `X-Request-Id`
    22. `ContextMiddleware` auto-generate when no header
    23. `ContextMiddleware` response header `X-Request-Id`
    24. `ContextMiddleware` client_ip extraction
    25. Concurrent isolation — two async requests have independent contexts

  **Must NOT do**:
  - Do NOT implement any source files yet (this is RED phase)
  - Do NOT add `pytest.importorskip()` — all deps are core

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 25 test cases with careful TDD design, async patterns, and FastAPI TestClient usage
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - None needed — this is test writing, no specialized skills required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 5, 6, 7
  - **Blocked By**: Task 2 (needs `tests/context/__init__.py` to exist first)

  **References**:

  **Pattern References** (existing tests to follow):
  - `tests/redis/test_client.py` — Class-based test pattern with Chinese docstrings, `async def test_xxx(self, cache)` style
  - `tests/logger/test_logger.py` — StringIO capture pattern for log output testing, sync test pattern
  - `tests/id_generator/test_generator.py` — `unittest.mock.patch` usage pattern

  **API/Type References** (contracts tests must validate against):
  - `doc/basic_tool_context_design.md:530-572` — Complete API reference table (all method signatures, return types)
  - `doc/basic_tool_context_design.md:576-718` — All usage examples showing expected behavior

  **External References**:
  - pytest-asyncio auto mode: `async def test_xxx()` works without decorators

  **WHY Each Reference Matters**:
  - `test_client.py`: Canonical test structure in this codebase — class grouping, method naming, fixture usage
  - `test_logger.py`: Shows how to capture loguru output with `io.StringIO()` — essential for test #13
  - Design doc API tables: Provide exact signatures and expected return types for all assertions

  **Acceptance Criteria**:

  - [ ] `tests/context/test_ctx.py` created with 25 test methods across appropriate classes
  - [ ] Every test method has a Chinese docstring
  - [ ] `pytest tests/context/test_ctx.py -v` → All 25 tests FAIL (RED phase confirmation)
  - [ ] No import errors in test file (all symbols resolve)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TDD RED phase — all 25 tests fail as expected
    Tool: Bash
    Preconditions: Task 2 (scaffolding) is complete
    Steps:
      1. Run `pytest tests/context/test_ctx.py -v --tb=no 2>&1 | tail -5`
      2. Verify output shows "25 failed" or equivalent failure count
      3. Verify NO import errors (no "ModuleNotFoundError" or "ImportError")
    Expected Result: All 25 tests collected and failed, zero collection errors
    Failure Indicators: "ModuleNotFoundError", "collection failure", fewer than 25 tests collected
    Evidence: .sisyphus/evidence/task-1-red-phase.txt

  Scenario: Test file has correct structure
    Tool: Bash
    Steps:
      1. Run `grep -c "def test_" tests/context/test_ctx.py`
      2. Verify count >= 25
      3. Run `grep -c '"""' tests/context/test_ctx.py`
      4. Verify every test method has a docstring (count >= 50 — open+close per method)
    Expected Result: 25+ test methods, all with docstrings
    Failure Indicators: Fewer than 25 test methods, missing docstrings
    Evidence: .sisyphus/evidence/task-1-test-structure.txt
  ```

  **Commit**: YES (groups with Task 2, 3)
  - Message: `test(context): add 25 TDD test cases for context module`
  - Files: `tests/context/__init__.py`, `tests/context/test_ctx.py`
  - Pre-commit: `pytest tests/context/test_ctx.py --collect-only -q`

- [x] 2. Create package scaffolding

  **What to do**:
  - Create `tests/context/__init__.py` (empty file)
  - Create `basic_tool/context/__init__.py` with a minimal stub that imports from submodules that don't exist yet — use comment placeholders so the file is syntactically valid but imports will fail until implementation is done
  - Alternatively, create `basic_tool/context/__init__.py` as an empty file first, and finalize exports in Task 8

  **Must NOT do**:
  - Do NOT create actual implementation files (ctx.py, log_extra.py, etc.)
  - Do NOT add imports to `basic_tool/__init__.py`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Creating empty/stub files — trivial task
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 1, 4, 5, 6, 7, 8
  - **Blocked By**: None (start immediately)

  **References**:

  **Pattern References**:
  - `tests/redis/` — Test directory with `__init__.py` (or without — either pattern is fine)
  - `tests/logger/` — Another test directory pattern

  **WHY Each Reference Matters**:
  - Ensures Python can resolve `tests/context/` as a package

  **Acceptance Criteria**:

  - [ ] `tests/context/__init__.py` exists (may be empty)
  - [ ] `basic_tool/context/` directory exists
  - [ ] `basic_tool/context/__init__.py` exists

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Package directories and files exist
    Tool: Bash
    Steps:
      1. Run `test -f tests/context/__init__.py && echo "OK" || echo "MISSING"`
      2. Run `test -f basic_tool/context/__init__.py && echo "OK" || echo "MISSING"`
    Expected Result: Both files exist
    Failure Indicators: "MISSING" for any file
    Evidence: .sisyphus/evidence/task-2-scaffolding.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `test(context): add 25 TDD test cases for context module`
  - Files: `tests/context/__init__.py`, `basic_tool/context/__init__.py`

- [x] 3. Write README.md

  **What to do**:
  - Create `basic_tool/context/README.md` following the project's canonical README format
  - Sections: Chinese title → 依赖 → 模块结构 (file tree) → API 文档 (method tables) → 使用示例
  - Use the design doc's API reference (Section 四) and usage examples (Section 五) as content source
  - Document the `enable_log_injection()` behavior correctly (with the bug fix applied)

  **Must NOT do**:
  - Do NOT modify any existing README files
  - Do NOT add usage patterns not in the design doc

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Documentation task following established template
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: None
  - **Blocked By**: None (start immediately)

  **References**:

  **Pattern References**:
  - `basic_tool/redis/README.md` — Canonical README format: Chinese title, 依赖, 模块结构 tree, API 文档 tables, 使用示例
  - `basic_tool/logger/README.md` — Another README example

  **Content References**:
  - `doc/basic_tool_context_design.md:530-572` — API reference table (all signatures)
  - `doc/basic_tool_context_design.md:576-718` — Usage examples

  **WHY Each Reference Matters**:
  - `redis/README.md`: Provides the exact section structure and formatting conventions to follow
  - Design doc Sections 四-五: All the actual content (API signatures, examples) to include

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/README.md` exists
  - [ ] Contains sections: 依赖, 模块结构, API 文档, 使用示例
  - [ ] All public API methods documented with signatures

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README follows project conventions
    Tool: Bash
    Steps:
      1. Run `grep -c "依赖" basic_tool/context/README.md`
      2. Verify count >= 1
      3. Run `grep -c "模块结构" basic_tool/context/README.md`
      4. Verify count >= 1
      5. Run `grep -c "API" basic_tool/context/README.md`
      6. Verify count >= 1
    Expected Result: All required sections present
    Failure Indicators: Missing sections
    Evidence: .sisyphus/evidence/task-3-readme.txt
  ```

  **Commit**: YES (separate commit)
  - Message: `docs(context): add module README`
  - Files: `basic_tool/context/README.md`

- [x] 4. Implement ctx.py — core context management (TDD GREEN)

  **What to do**:
  - Create `basic_tool/context/ctx.py` implementing the core context management module
  - Implement based on design doc Section 3.1 (`doc/basic_tool_context_design.md:60-237`)
  - Key components:
    - `_context_data: ContextVar[dict[str, Any]]` — single ContextVar holding the entire context dict
    - `ContextManager` class — singleton with `get()`, `set()`, `getall()`, `dump()`, `clear()` methods
    - `request_context(**kwargs)` — factory function, auto-generates `request_id` if not provided
    - `_RequestContext` — supports both `with` and `async with`, uses `ContextVar.set()` / `reset()` for nesting safety
  - Every method MUST have a docstring with Args, Returns descriptions
  - File MUST have a module-level docstring
  - Run `pytest tests/context/test_ctx.py -k "test 1-12" -v` to verify tests 1-12 pass (GREEN)

  **Must NOT do**:
  - Do NOT implement log_extra.py, propagation.py, or middleware.py
  - Do NOT add configuration classes (no `config.py` needed)
  - Do NOT use `from __future__ import annotations` unless design doc uses it

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core module with contextvars, token-based nesting, sync+async CM — requires careful implementation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO — blocked by Task 1 (tests), blocks Tasks 5, 6, 7
  - **Parallel Group**: Wave 2 (first task)
  - **Blocks**: Tasks 5, 6, 7, 8, 9
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `basic_tool/logger/logger.py` — Module structure: module docstring, class with method docstrings
  - `basic_tool/id_generator/generator.py` — Simpler module pattern with config + core class

  **API/Type References**:
  - `doc/basic_tool_context_design.md:60-237` — Complete ctx.py implementation code (verbatim reference)
  - `doc/basic_tool_context_design.md:530-541` — API table for ContextManager methods

  **External References**:
  - Python `contextvars` docs: `ContextVar`, `Token`, `set()`/`reset()` for nesting safety

  **WHY Each Reference Matters**:
  - Design doc 60-237: Contains the exact code to implement — this is the primary reference
  - `contextvars.Token.reset()`: Critical for correct nesting behavior — inner context exit restores outer

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/ctx.py` created with `ContextManager`, `request_context`, `_RequestContext`
  - [ ] Module-level docstring present
  - [ ] All methods have docstrings with Args/Returns
  - [ ] `python -c "from basic_tool.context.ctx import ctx, request_context, ContextManager"` → no errors
  - [ ] Tests 1-12 pass: `pytest tests/context/test_ctx.py -v --tb=short` (only tests 1-12 should pass; 13-25 still fail)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Core context lifecycle works (tests 1-12 pass)
    Tool: Bash
    Preconditions: Task 2 scaffolding complete, test file exists
    Steps:
      1. Run `pytest tests/context/test_ctx.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR)" | head -30`
      2. Verify tests for basic usage, set/get, getall, cleanup, nesting, async, dump, clear, default all PASS
      3. Count passed tests — should be 12 for ctx.py tests
    Expected Result: 12 PASSED (tests 1-12), remaining tests still fail (expected — GREEN for ctx only)
    Failure Indicators: Core tests fail, import errors
    Evidence: .sisyphus/evidence/task-4-ctx-green.txt

  Scenario: Import and basic usage verification
    Tool: Bash
    Steps:
      1. Run `python -c "from basic_tool.context.ctx import ctx, request_context; print('OK')"`
      2. Run `python -c "
from basic_tool.context.ctx import ctx, request_context
with request_context(request_id='test', user_id=42):
    assert ctx.get('request_id') == 'test'
    assert ctx.get('user_id') == 42
    assert ctx.getall() == {'request_id': 'test', 'user_id': 42}
assert ctx.getall() == {}
print('ALL OK')"`
    Expected Result: "OK" then "ALL OK"
    Failure Indicators: AssertionError, ImportError
    Evidence: .sisyphus/evidence/task-4-ctx-verify.txt
  ```

  **Commit**: YES
  - Message: `feat(context): implement core context management with ContextManager and request_context`
  - Files: `basic_tool/context/ctx.py`
  - Pre-commit: `pytest tests/context/test_ctx.py --tb=short -q`

- [x] 5. Implement log_extra.py — log context injection (TDD GREEN + BUG FIX)

  **What to do**:
  - Create `basic_tool/context/log_extra.py` implementing loguru context injection
  - **CRITICAL BUG FIX**: The design doc's `enable_log_injection()` is broken — `logger.patch()` returns a new logger but the design discards it
  - **Fix**: Reassign `loguru.logger._options` from the patched logger to make the patch global:
    ```python
    def enable_log_injection() -> None:
        import loguru
        patched = loguru.logger.patch(_inject_context)
        loguru.logger._options = patched._options
    ```
  - This ensures ALL loguru logger references (including `basic_tool.logger.get()`) are patched
  - `_inject_context(record)` reads `_context_data.get()` and merges into `record["extra"]` (without overwriting user-provided extras)
  - Every method MUST have a docstring
  - Run `pytest tests/context/test_ctx.py -k "test 13" -v` to verify test 13 passes

  **Must NOT do**:
  - Do NOT modify `basic_tool/logger/` files
  - Do NOT use `logger.patch(_inject_context)` as a standalone statement (it's a no-op)
  - Do NOT change the public API — `enable_log_injection()` still returns `None`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding loguru internals (`_options` attribute) to implement the bug fix correctly
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO — depends on ctx.py being complete
  - **Parallel Group**: Wave 2 (after Task 4)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Tasks 1, 2, 4

  **References**:

  **Pattern References**:
  - `basic_tool/logger/logger.py` — How the project configures loguru (format, sinks)

  **API/Type References**:
  - `doc/basic_tool_context_design.md:240-294` — Original log_extra.py code (NOTE: contains the bug)
  - `doc/basic_tool_context_design.md:553-554` — API table for `enable_log_injection()`

  **External References**:
  - loguru `Logger._options` — Internal tuple used by `patch()` to store patcher functions; can be reassigned to apply patch globally

  **WHY Each Reference Matters**:
  - Design doc 240-294: The base code, but MUST be modified to fix the `patch()` no-op bug
  - `logger._options`: The mechanism for making the patch global — the key difference from the broken design doc

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/log_extra.py` created
  - [ ] Module-level docstring present
  - [ ] `_inject_context` and `enable_log_injection` have docstrings
  - [ ] Test 13 passes: `pytest tests/context/test_ctx.py -k "log_injection or test_13" -v`
  - [ ] `python -c "from basic_tool.context.log_extra import enable_log_injection"` → no errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Log injection works — extra includes context fields
    Tool: Bash
    Steps:
      1. Run `python -c "
import io, sys
from loguru import logger
from basic_tool.context.ctx import request_context, _context_data
from basic_tool.context.log_extra import enable_log_injection

# Capture output
buf = io.StringIO()
logger.remove()
logger.add(buf, format='{message}', filter=lambda r: True)
enable_log_injection()

with request_context(request_id='log-test', user_id=99):
    logger.info('test message')

output = buf.getvalue()
assert 'request_id=log-test' in output or 'log-test' in output
print('OK: log injection works')
"`
    Expected Result: "OK: log injection works"
    Failure Indicators: AssertionError, meaning context fields not in log output
    Evidence: .sisyphus/evidence/task-5-log-injection.txt

  Scenario: User-provided extra not overwritten
    Tool: Bash
    Steps:
      1. Run `python -c "
import io
from loguru import logger
from basic_tool.context.ctx import request_context, _context_data
from basic_tool.context.log_extra import enable_log_injection

buf = io.StringIO()
logger.remove()
logger.add(buf, format='{message}', filter=lambda r: True)
enable_log_injection()

with request_context(request_id='r1'):
    logger.info('msg', request_id='user-override')

output = buf.getvalue()
# User's explicit request_id should take priority
print('OK: priority check passed')
"`
    Expected Result: No error — user extra takes priority
    Evidence: .sisyphus/evidence/task-5-priority.txt
  ```

  **Commit**: YES
  - Message: `feat(context): implement log context injection with global patch fix`
  - Files: `basic_tool/context/log_extra.py`
  - Pre-commit: `pytest tests/context/test_ctx.py -k "log" --tb=short -q`

- [x] 6. Implement propagation.py — HTTP + queue propagation (TDD GREEN)

  **What to do**:
  - Create `basic_tool/context/propagation.py` implementing HTTP header and task queue propagation
  - Implement based on design doc Section 3.3 (`doc/basic_tool_context_design.md:296-397`)
  - Key components:
    - `_DEFAULT_HEADER_MAP` — context key → HTTP header name mapping
    - `get_propagation_headers(header_map=None)` — extract propagation headers from current context
    - `inject_headers_to_httpx(headers=None)` — merge context headers with user headers (user priority)
    - `serialize_context()` — snapshot current context for task queue
    - `deserialize_context(data)` — restore context from serialized data (returns `request_context(**data)`)
  - Every function MUST have a docstring with Args, Returns
  - Run `pytest tests/context/test_ctx.py -k "propagation or serialize or deserialize" -v` to verify tests 14-20 pass

  **Must NOT do**:
  - Do NOT modify `basic_tool/http_client/` or `basic_tool/task_queue/`
  - Do NOT add actual HTTP calls — only header dict generation

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple functions with subtle semantics (user priority, header filtering, serialization round-trip)
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 7 — after Task 4 completes)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Tasks 1, 2, 4

  **References**:

  **API/Type References**:
  - `doc/basic_tool_context_design.md:296-397` — Complete propagation.py code
  - `doc/basic_tool_context_design.md:556-563` — API table for propagation functions

  **WHY Each Reference Matters**:
  - Design doc 296-397: Verbatim implementation code — primary reference
  - API table: Method signatures to match exactly

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/propagation.py` created with all 5 functions + default header map
  - [ ] Module-level docstring present
  - [ ] All functions have docstrings
  - [ ] Tests 14-20 pass
  - [ ] `python -c "from basic_tool.context.propagation import get_propagation_headers, inject_headers_to_httpx, serialize_context, deserialize_context"` → no errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: HTTP header propagation works
    Tool: Bash
    Steps:
      1. Run `python -c "
from basic_tool.context.ctx import request_context, _context_data
from basic_tool.context.propagation import get_propagation_headers, inject_headers_to_httpx

with request_context(request_id='h1', tenant_id='t1'):
    headers = get_propagation_headers()
    assert headers == {'X-Request-Id': 'h1', 'X-Tenant-Id': 't1'}

    merged = inject_headers_to_httpx({'Authorization': 'Bearer x'})
    assert merged['X-Request-Id'] == 'h1'
    assert merged['Authorization'] == 'Bearer x'
print('OK')
"`
    Expected Result: "OK"
    Failure Indicators: AssertionError, KeyError
    Evidence: .sisyphus/evidence/task-6-headers.txt

  Scenario: Serialization round-trip works
    Tool: Bash
    Steps:
      1. Run `python -c "
from basic_tool.context.ctx import ctx, request_context, _context_data
from basic_tool.context.propagation import serialize_context, deserialize_context

with request_context(request_id='s1', user_id=42):
    data = serialize_context()
    assert data['request_id'] == 's1'
    assert data['user_id'] == 42

    with deserialize_context(data):
        assert ctx.get('request_id') == 's1'
        assert ctx.get('user_id') == 42
print('OK')
"`
    Expected Result: "OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-6-serialize.txt
  ```

  **Commit**: YES
  - Message: `feat(context): implement HTTP header and task queue propagation`
  - Files: `basic_tool/context/propagation.py`
  - Pre-commit: `pytest tests/context/test_ctx.py -k "propagation or serialize" --tb=short -q`

- [x] 7. Implement middleware.py — FastAPI context middleware (TDD GREEN)

  **What to do**:
  - Create `basic_tool/context/middleware.py` implementing FastAPI request context middleware
  - Implement based on design doc Section 3.4 (`doc/basic_tool_context_design.md:399-481`)
  - Key components:
    - `ContextMiddleware(BaseHTTPMiddleware)` — extracts request_id from `X-Request-Id` header (or generates UUID), extracts client_ip (prefers `X-Forwarded-For`), creates `request_context`, adds `X-Request-Id` to response
    - `setup_context_middleware(app: FastAPI)` — convenience function to register middleware
  - Every method and function MUST have a docstring
  - Tests 21-25 use FastAPI `TestClient` for integration testing
  - Run `pytest tests/context/test_ctx.py -k "middleware" -v` to verify tests 21-25 pass

  **Must NOT do**:
  - Do NOT modify `basic_tool/fastapi/middleware.py` (existing `RequestLoggingMiddleware`)
  - Do NOT resolve the overlap between `ContextMiddleware` and `RequestLoggingMiddleware`
  - Do NOT add `X-Forwarded-For` parsing beyond what the design doc specifies

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires FastAPI/Starlette knowledge, TestClient setup for async middleware testing
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6 — after Task 4 completes)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Tasks 1, 2, 4

  **References**:

  **API/Type References**:
  - `doc/basic_tool_context_design.md:399-481` — Complete middleware.py code
  - `doc/basic_tool_context_design.md:565-569` — API table for middleware

  **Test References**:
  - `tests/test_fastapi/` — FastAPI test patterns using TestClient

  **WHY Each Reference Matters**:
  - Design doc 399-481: Verbatim implementation code
  - `tests/test_fastapi/`: Shows how this project sets up FastAPI TestClient for testing middleware

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/middleware.py` created with `ContextMiddleware` and `setup_context_middleware`
  - [ ] Module-level docstring present
  - [ ] All methods have docstrings
  - [ ] Tests 21-25 pass
  - [ ] `python -c "from basic_tool.context.middleware import ContextMiddleware, setup_context_middleware"` → no errors

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Middleware extracts and returns request_id
    Tool: Bash
    Preconditions: ctx.py implemented (Task 4)
    Steps:
      1. Run `python -c "
from fastapi import FastAPI
from fastapi.testclient import TestClient
from basic_tool.context.middleware import ContextMiddleware

app = FastAPI()
app.add_middleware(ContextMiddleware)

@app.get('/test')
def test_route():
    from basic_tool.context.ctx import ctx
    return {'request_id': ctx.get('request_id')}

client = TestClient(app)
# Test with provided request_id
resp = client.get('/test', headers={'X-Request-Id': 'my-req-123'})
assert resp.json()['request_id'] == 'my-req-123'
assert resp.headers['X-Request-Id'] == 'my-req-123'

# Test auto-generation
resp2 = client.get('/test')
assert resp2.json()['request_id'] is not None
assert len(resp2.json()['request_id']) == 32  # UUID hex
print('OK')
"`
    Expected Result: "OK"
    Failure Indicators: AssertionError, import errors
    Evidence: .sisyphus/evidence/task-7-middleware.txt

  Scenario: Middleware handles client_ip extraction
    Tool: Bash
    Steps:
      1. Run `python -c "
from fastapi import FastAPI
from fastapi.testclient import TestClient
from basic_tool.context.middleware import ContextMiddleware

app = FastAPI()
app.add_middleware(ContextMiddleware)

@app.get('/ip')
def test_ip():
    from basic_tool.context.ctx import ctx
    return {'client_ip': ctx.get('client_ip')}

client = TestClient(app)
resp = client.get('/ip')
assert resp.json()['client_ip'] is not None
print('OK')
"`
    Expected Result: "OK"
    Evidence: .sisyphus/evidence/task-7-client-ip.txt
  ```

  **Commit**: YES
  - Message: `feat(context): implement FastAPI request context middleware`
  - Files: `basic_tool/context/middleware.py`
  - Pre-commit: `pytest tests/context/test_ctx.py -k "middleware" --tb=short -q`

- [x] 8. Finalize __init__.py exports + update basic_tool docstring

  **What to do**:
  - Update `basic_tool/context/__init__.py` with complete exports following project convention:
    - Module-level Chinese docstring with usage example
    - Absolute imports from all submodules
    - `__all__` list with grouped comments (核心, 日志注入, 透传, FastAPI)
  - Update `basic_tool/__init__.py` — ONLY add `context` to the docstring module list, NO import statements
  - Follow the pattern from `basic_tool/redis/__init__.py` or `basic_tool/crypto/__init__.py` for `__all__`

  **Must NOT do**:
  - Do NOT add import statements to `basic_tool/__init__.py`
  - Do NOT modify any other files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward export wiring and docstring update
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO — must wait for all source files (Tasks 4-7)
  - **Parallel Group**: Wave 2 (last task)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 4, 5, 6, 7

  **References**:

  **Pattern References**:
  - `basic_tool/redis/__init__.py` — `__all__` with grouped comments pattern
  - `basic_tool/crypto/__init__.py` — Another `__all__` example
  - `basic_tool/__init__.py` — Current docstring-only format to update

  **API/Type References**:
  - `doc/basic_tool_context_design.md:483-526` — Complete `__init__.py` code with all exports

  **WHY Each Reference Matters**:
  - `redis/__init__.py`: The canonical `__all__` pattern with grouped comments like `# 核心`
  - Design doc 483-526: The exact exports to include

  **Acceptance Criteria**:

  - [ ] `basic_tool/context/__init__.py` has Chinese docstring + `__all__` + absolute imports
  - [ ] `python -c "from basic_tool.context import ctx, request_context, enable_log_injection, ContextMiddleware, setup_context_middleware, get_propagation_headers, inject_headers_to_httpx, serialize_context, deserialize_context"` → no errors
  - [ ] `basic_tool/__init__.py` docstring mentions `context` module
  - [ ] `basic_tool/__init__.py` has NO import statements added

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All public API imports work
    Tool: Bash
    Steps:
      1. Run `python -c "
from basic_tool.context import (
    ctx, ContextManager, request_context,
    enable_log_injection,
    get_propagation_headers, inject_headers_to_httpx,
    serialize_context, deserialize_context,
    ContextMiddleware, setup_context_middleware,
)
assert isinstance(ctx, ContextManager)
print('ALL IMPORTS OK')
"`
    Expected Result: "ALL IMPORTS OK"
    Failure Indicators: ImportError, AssertionError
    Evidence: .sisyphus/evidence/task-8-imports.txt

  Scenario: basic_tool docstring updated, no imports added
    Tool: Bash
    Steps:
      1. Run `grep "context" basic_tool/__init__.py`
      2. Verify `context` appears in the docstring
      3. Run `grep "^from\|^import" basic_tool/__init__.py`
      4. Verify NO import lines exist
    Expected Result: "context" in docstring, zero import lines
    Failure Indicators: Import lines found, "context" not in docstring
    Evidence: .sisyphus/evidence/task-8-docstring.txt
  ```

  **Commit**: YES
  - Message: `feat(context): finalize module exports and update top-level docstring`
  - Files: `basic_tool/context/__init__.py`, `basic_tool/__init__.py`
  - Pre-commit: `python -c "from basic_tool.context import ctx, request_context"`

- [x] 9. Full integration test + regression check

  **What to do**:
  - Run `pytest tests/context/ -v` — verify ALL 25 tests pass (GREEN)
  - Run `pytest tests/ -v` — verify NO regressions in existing tests
  - Run all import verification commands from success criteria
  - Verify the complete context lifecycle works end-to-end:
    1. Create request context with auto-generated request_id
    2. Set dynamic fields
    3. Nested context with override
    4. Async context inheritance
    5. Log injection
    6. HTTP header propagation
    7. Serialization round-trip
    8. FastAPI middleware with TestClient

  **Must NOT do**:
  - Do NOT fix failing tests by modifying test expectations — fix the source code instead
  - Do NOT skip or mark tests as `pytest.skip`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive verification with potential debugging if integration issues arise
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO — must wait for all implementation tasks
  - **Parallel Group**: Wave 3 (after Wave 2)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 4, 5, 6, 7, 8

  **References**:

  **Pattern References**:
  - `doc/basic_tool_context_design.md:576-718` — All usage examples to verify against

  **Acceptance Criteria**:

  - [ ] `pytest tests/context/ -v` → 25 passed, 0 failed
  - [ ] `pytest tests/ -v` → all tests pass, 0 regressions
  - [ ] All 5 success criteria commands pass (from Success Criteria section)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All 25 tests pass (TDD GREEN confirmed)
    Tool: Bash
    Preconditions: All source files implemented (Tasks 4-8)
    Steps:
      1. Run `pytest tests/context/ -v 2>&1 | tail -10`
      2. Verify "25 passed" in output
      3. Run `pytest tests/context/ -v 2>&1 | grep -c "PASSED"`
      4. Verify count == 25
    Expected Result: 25 passed, 0 failed
    Failure Indicators: Any FAILED or ERROR
    Evidence: .sisyphus/evidence/task-9-all-green.txt

  Scenario: No regressions in existing tests
    Tool: Bash
    Steps:
      1. Run `pytest tests/ -v --tb=short 2>&1 | tail -5`
      2. Verify all tests pass (no new failures)
    Expected Result: All tests pass, new context tests included
    Failure Indicators: Any new FAILURES not present before
    Evidence: .sisyphus/evidence/task-9-regression.txt

  Scenario: End-to-end integration
    Tool: Bash
    Steps:
      1. Run `python -c "
import asyncio
from basic_tool.context import (
    ctx, request_context, enable_log_injection,
    get_propagation_headers, inject_headers_to_httpx,
    serialize_context, deserialize_context,
)

# Sync lifecycle
with request_context(request_id='e2e-001', user_id=42, tenant_id='t1'):
    assert ctx.get('request_id') == 'e2e-001'
    ctx.set('trace_id', 'trace-abc')
    assert ctx.getall()['trace_id'] == 'trace-abc'

    # Nested
    with request_context(request_id='nested'):
        assert ctx.get('request_id') == 'nested'
        assert ctx.get('user_id') == 42  # inherited
    assert ctx.get('request_id') == 'e2e-001'  # restored

    # Propagation
    headers = get_propagation_headers()
    assert 'X-Request-Id' in headers
    assert headers['X-Request-Id'] == 'e2e-001'

    # Serialization
    data = serialize_context()
    with deserialize_context(data):
        assert ctx.get('request_id') == 'e2e-001'

# Cleanup verified
assert ctx.getall() == {}
print('E2E OK')
"`
    Expected Result: "E2E OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-9-e2e.txt
  ```

  **Commit**: NO (verification only — no new changes expected)

---\n\n## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run import command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v`. Review all new files for: `as any`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify all methods have docstrings (Args, Returns). Verify all files have module-level docstrings.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | Docstrings [N/N] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute key scenarios: (1) sync context lifecycle, (2) async context inheritance, (3) nested context restoration, (4) log injection, (5) HTTP header propagation, (6) FastAPI middleware with TestClient. Save evidence to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Verify `basic_tool/__init__.py` change is docstring-only (no imports added). Verify no files outside scope were modified.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **After Task 3** (scaffolding): `feat(context): scaffold context module with tests and README` — basic_tool/context/__init__.py, tests/context/__init__.py, tests/context/test_ctx.py, basic_tool/context/README.md
- **After Task 4** (ctx.py): `feat(context): implement core context management` — basic_tool/context/ctx.py
- **After Task 5** (log_extra.py): `feat(context): implement log context injection` — basic_tool/context/log_extra.py
- **After Task 6** (propagation.py): `feat(context): implement HTTP and queue propagation` — basic_tool/context/propagation.py
- **After Task 7** (middleware.py): `feat(context): implement FastAPI context middleware` — basic_tool/context/middleware.py
- **After Task 8** (exports): `feat(context): finalize exports and docstring` — basic_tool/context/__init__.py, basic_tool/__init__.py

---

## Success Criteria

### Verification Commands
```bash
pytest tests/context/ -v           # Expected: 25 passed
pytest tests/ -v                   # Expected: all pass (no regressions)
python -c "from basic_tool.context import ctx, request_context, enable_log_injection"
python -c "from basic_tool.context import ContextMiddleware, setup_context_middleware"
python -c "from basic_tool.context import get_propagation_headers, inject_headers_to_httpx"
python -c "from basic_tool.context import serialize_context, deserialize_context"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All 25 tests pass
- [ ] No regressions in existing tests
