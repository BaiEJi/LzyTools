# Learnings

## 2026-06-12 Session Start
- Design doc at `doc/basic_tool_crypto_design.md` contains COMPLETE source code for all files
- Must copy code EXACTLY from design doc — no "improvements"
- `basic_tool/__init__.py` is pure docstring — only append crypto description line, NO imports
- `cryptography` already installed transitively via `python-jose[cryptography]` but needs explicit declaration
- `argon2-cffi` NOT yet installed
- Use low-overhead CryptoConfig in tests: `memory_cost=1024, time_cost=1, parallelism=1`
- TTL expiry test: use `time.sleep(1.1)` + `ttl=1` (no freezegun)
- Test naming: `TestClassName` with `test_method_name` pattern (Chinese docstrings)
- README format: Title → Dependencies → Module Structure → API Docs → Usage Examples

## Task: kdf.py (TDD)
- CryptoConfig constructor uses `argon2_memory_cost`, `argon2_time_cost`, `argon2_parallelism` (not `memory_cost`, `time_cost`, `parallelism`)
- PBKDF2 default iterations = 600,000 (OWASP 2025), runs in ~0.3s per call
- HKDF is instant (non-iterative), good for key expansion from master keys
- Both KDF functions are deterministic — same inputs always produce same output

## Task: encrypt.py (TDD)
- Fernet uses integer-second timestamps (`int(time.time())`), so `time.sleep(1.1)` + `ttl=1` is FLAKY — 9/10 failures
- Changed to `time.sleep(2.1)` + `ttl=1` for reliable TTL expiry (still uses time.sleep strategy, no freezegun)
- Fernet token format: base64(timestamp || IV || ciphertext || HMAC)
- `InvalidToken` from cryptography maps to our `DecryptionError`
- Empty Fernet key → `InvalidKeyError` (checked in `_get_fernet` before Fernet construction)

## Task: password.py (TDD)
- Design doc test code had WRONG CryptoConfig field names: used `memory_cost=1024` but actual field is `argon2_memory_cost=1024` — fixed to match CryptoConfig definition
- Password hashing tests with low config (1024KB, 1 iteration) run in ~0.06s total — very fast
- `argon2-cffi` has no type stubs → Pyright reports `reportMissingImports` — runtime works fine
- `secrets.token_urlsafe(32)` produces 43 chars (base64 encoding), `secrets.token_hex(32)` produces 64 chars (hex encoding)
- Argon2id hash contains `$argon2id$` prefix with embedded parameters — `check_needs_rehash()` compares these against hasher params
- `uv sync --extra dev` needed to install pytest + dev dependencies before running tests
- `CryptoError` imported but unused in password.py — kept as design doc specified it (future use)

## Task: encrypt.py (TDD) — COMPLETED
- 8 tests pass in 2.15s (TTL test `time.sleep(2.1)` accounts for ~2.1s of that)
- Implementation copied verbatim from task spec API section — no deviations
- `_get_fernet` handles both `str` and `bytes` fernet_key (str→encode before Fernet())
- Empty key check (`if not config.fernet_key`) catches both `""` and `None` before Fernet construction
- Tampered ciphertext test uses last-char replacement with collision-avoidance ternary (Z/Y fallback)
- All docstrings are mandatory per CLAUDE.md project constraint (security/public API module)
- Removed 2 unnecessary inline comments from test file; kept all docstrings (project rule + spec-mandated)
- LSP diagnostics clean on both encrypt.py and test_encrypt.py (0 errors)

## Task: kdf.py — Implementation Complete (2026-06-13)
- TDD workflow clean: RED (ModuleNotFoundError) → GREEN (5 passed in 1.26s)
- PBKDF2 default 600k iterations: only 1 PBKDF2 test needed, total suite ~1.3s — fast enough
- HKDF tests are instant, no perf concern
- TestCryptoConfig test validates CryptoConfig custom params already exist (no config.py changes needed)
- LSP diagnostics clean on both files (no type issues with cryptography imports)

## Task 3: sign.py (HMAC-SHA256 + SHA-256)
- **TDD flow confirmed**: RED (ModuleNotFoundError) → GREEN (6 passed) clean.
- **pytest invocation**: use `uv run pytest` (not `.venv/bin/python -m pytest` — pytest not installed as module in venv; uv handles env).
- **sign.py is pure stdlib**: `hashlib` + `hmac` only, no external deps. 4 public functions: `sign`, `verify`, `sha256`, `sha256_hex` (alias = `sha256`).
- **Alias pattern**: `sha256_hex = sha256` is assignment, not a def — keeps it as true alias (same function object).
- **verify uses `hmac.compare_digest`**: constant-time comparison to prevent timing attacks on signature verification.
- **Pyright false positive**: newly-created `basic_tool/crypto/sign.py` triggers `reportMissingImports` in test file until reindex — ignore, tests pass.
- **Project layout**: working dir IS the package (`basic_tool/`); project root is parent. Tests at `/home/lizy/projects/LzyProjs/tests/crypto/`, source at `/home/lizy/projects/LzyProjs/basic_tool/crypto/`.

## Task: password.py (TDD) — 2026-06-13
- pytest must run via `/home/lizy/projects/LzyProjs/.venv/bin/python -m pytest` from workspace ROOT (where pyproject.toml lives), NOT from basic_tool/ package dir
- Workspace venv initially lacked pytest — needed `uv sync --extra dev` to install pytest/pytest-asyncio/fakeredis
- `verify_password` catches broad `Exception` tuple (incl. bare Exception) per spec — guarantees no leakage to caller
- `check_needs_rehash` returns True when hash params < hasher params; LOW_CONFIG(time_cost=1) vs CryptoConfig(time_cost=10) triggers it
- All 11 tests pass in 0.11s with LOW_CONFIG — confirms low-overhead config strategy works

## Task 8: crypto/README.md — 2026-06-13
- README format follows logger/README.md exactly: Title (intro) → ## 依赖 → ## 模块结构 → ## API 文档 → ## 使用示例
- All 17 public symbols documented across 4 categories: password.py (5), encrypt.py (5), sign.py (4 incl. sha256_hex alias), kdf.py (2), + CryptoConfig + 4 exceptions
- CryptoConfig field table must use exact field names (`argon2_memory_cost`, not `memory_cost`)
- sha256_hex is documented as alias with single line: `sha256_hex = sha256` plus note
- Examples use real import paths: `from basic_tool.crypto import hash_password, verify_password`
- Prose style: no em/en dashes (use commas, periods), no emoji, plain words over jargon, varied sentence length
