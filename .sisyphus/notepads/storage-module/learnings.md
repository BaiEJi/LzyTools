# Storage Module - Learnings

## Codebase Patterns
- Pydantic BaseModel for all config classes (RedisConfig, IDConfig)
- Flat __init__.py exports with __all__ list
- Module-level docstrings on every .py file
- Tests: pytest + pytest-asyncio (asyncio_mode="auto")
- Test class grouping with Chinese docstrings
- tests/ mirrors basic_tool/ structure
- No __init__.py in test subdirectories
- Loguru for logging: `logger.info("msg | key={}", val)`
- aiofiles is new dependency (not yet in pyproject.toml)
- Path.is_relative_to() for path traversal checks (3.9+, project requires 3.11+)

## Design Doc Key Points
- .ct sidecar files for content_type persistence
- Storage facade delegates to backend
- LocalBackend uses aiofiles for async I/O
- metadata is no-op in v1 (interface only)
- Empty key should raise ValueError
- list() must read .ct sidecar (Metis review fix)
- put silently overwrites (no protection)

## aiofiles Dependency (2026-06-13)
- Added `"aiofiles>=23.0.0"` to pyproject.toml dependencies (after cryptography)
- Installed version: 25.1.0
- NOTE: `aiofiles.__version__` does NOT exist (AttributeError); use `importlib.metadata.version('aiofiles')` instead
- aiofiles is a pure Python package, no transitive deps

## Task 2 (config.py + backend.py) — Completed
- StorageConfig uses pydantic BaseModel, mirrors RedisConfig style exactly
- MinIO fields kept as docstring-only comments (not commented-out code) to keep model clean
- FileInfo uses __slots__ for memory efficiency
- StorageBackend ABC: 8 abstract async methods (init, close, put, get, delete, exists, info, list)
- list() docstring explicitly notes .ct sidecar reading for content_type consistency
- Verification: `python -c "from basic_tool.storage.config import StorageConfig; c=StorageConfig(); print(c.backend, c.base_dir)"` → "local ./uploads"
- Verification: instantiating StorageBackend() raises TypeError (abstract class)
- LSP diagnostics: 0 errors on both files

## Task 3 (test_storage.py TDD RED) — Completed
- Created tests/storage/conftest.py with 3 fixtures: storage_config (tmp_path), storage (uninit), initialized_storage (init+yield+close)
- Created tests/storage/test_storage.py with 20 tests across 8 classes (TestInit, TestPutGet, TestDelete, TestExists, TestInfo, TestList, TestUrl, TestSecurity)
- test discovery: 20 collected, 0 errors during collection
- RED phase verified: all 20 fail/error with `ModuleNotFoundError: No module named 'basic_tool.storage.local'`
- DISCOVERY: storage.py ALREADY EXISTS (Task 5 in progress/complete) — Storage.__init__ calls _create_backend() which lazy-imports LocalBackend from local.py
- The lazy import pattern in storage.py means tests can import Storage fine, but instantiation fails because local.py doesn't exist
- test_delete_removes_ct_file uses behavioral verification: re-put without content_type after delete, assert info().content_type is None (proves .ct sidecar was cleaned)
- Three tests (TestInit x2, TestUrl.test_url_no_prefix) construct Storage directly in test body to customize config; rest use initialized_storage fixture

## Task 4 (local.py LocalBackend GREEN) — Completed
- Single-line storage.py change: `LocalBackend(self._config.base_dir)` → `LocalBackend(self._config)` (pass full StorageConfig so LocalBackend can read auto_create_dir)
- LocalBackend takes StorageConfig (not str) — matches the "config object" convention used by Cache(RedisConfig)
- `_resolve()` centralizes BOTH empty-key check AND path traversal (is_relative_to) — reused by put/get/delete/exists/info
- Extracted `_ct_path()` helper (static) and `_read_ct()` async helper to DRY up sidecar handling
- .ct naming: `target.with_suffix(target.suffix + ".ct")` APPENDS to full filename (a.png → a.png.ct), never replaces extension
- put() else-branch removes stale .ct via `unlink(missing_ok=True)` — critical for test_delete_removes_ct_file (re-put without ct must yield None)
- list() uses `prefix_path.rglob("*")` from `base_dir/prefix`; skips non-files and `.ct` sidecars; normalizes keys with `.replace(os.sep, "/")`
- init() auto_create_dir=False path raises FileNotFoundError (not creates dir) — verified by test_init_missing_dir_raises
- GREEN phase: 20/20 tests pass in 0.31s
- LSP: local.py 0 diagnostics; storage.py has PRE-EXISTING Pyright reportOptionalMemberAccess errors on `self._backend` (None-typed then reassigned in __init__) — NOT introduced by this task, out of scope (only _create_backend may change)
- Whole basic_tool/storage/ dir is untracked (new), so storage.py diagnostics are from Task 5 code, not Task 4

## Integration QA — Completed (2026-06-13)
- Storage tests: 20/20 PASSED in 0.10s (isolated run)
- Full regression suite: 430 passed, 1 skipped, 0 failures, 3 warnings (11.52s)
  - 1 skip: pre-existing redis `test_blmove_immediate` (unrelated module)
  - 3 warnings: pre-existing (fastapi StarletteDeprecationWarning, concurrency RuntimeWarning) — NOT from storage
- Imports: `from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo` → OK
- Docstrings: config.py, backend.py, local.py, storage.py all have module-level docstrings → OK
- Path traversal security: test_path_traversal + test_key_with_leading_slash → both PASSED
- LSP diagnostics (storage/ dir): 9 Pyright errors, ALL pre-existing on storage.py `self._backend` Optional type
  (reportOptionalMemberAccess + reportReturnType) — documented in Task 4 learnings line 60 as out of scope
  - config.py, backend.py, local.py, __init__.py: 0 errors each
- No fixes required: all storage tests pass, no regressions introduced
