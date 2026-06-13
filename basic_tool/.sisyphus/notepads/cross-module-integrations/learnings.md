# Learnings — cross-module-integrations

## Project Layout
- Package `basic_tool` lives at `/home/lizy/projects/LzyProjs/basic_tool/` (the directory IS the package)
- Tests at `/home/lizy/projects/LzyProjs/tests/` (mirror structure)
- pyproject.toml at `/home/lizy/projects/LzyProjs/pyproject.toml`
- Run tests from `/home/lizy/projects/LzyProjs/` with `python -m pytest tests/ -v`
- Python 3.13 (conda), pytest 8.x, asyncio_mode=auto

## Baseline
- 480 passed, 1 skipped (before any changes)

## Conventions
- Use `from loguru import logger` (NOT basic_tool.logger)
- Tests use fakeredis for Redis, AsyncMock for SMTP/ARQ, tmp_path for filesystem, httpx.MockTransport for HTTP
- Each basic_tool subpackage has its own README.md
- Multi-file modules use folder + __init__.py + Mixin pattern

## Critical Architecture Constraints (from Metis review)
- **redis↔metrics 2-cycle**: metrics/writer.py imports redis.Cache. Redis must NOT import metrics → use CALLBACK PROTOCOL
- **errors→metrics→redis→errors 3-cycle**: errors must NOT import metrics → use CALLBACK PROTOCOL
- **enable_log_injection() non-idempotent**: needs `_enabled` guard
- **RateLimitError / CryptoError constructor compat**: keep existing signatures
- **ARQ serialization**: no closures → email task uses module-level function + worker ctx injection
- **NO TYPE_CHECKING**: codebase has no precedent

## File Paths Reference
- context/log_extra.py:51-70 — enable_log_injection()
- fastapi/app.py:132-134 — create_app() log config location
- context/ctx.py:35-39 — ContextManager, request_context
- redis/decorators.py:42-53 — RateLimitError
- errors/app_error.py:10-39 — AppError base
- crypto/exceptions.py:1-22 — crypto exceptions
- fastapi/auth.py:94-132 — get_current_user()
- task_queue/worker.py:90-114 — _wrap_function()
- context/propagation.py:36-122 — inject/serialize/deserialize
- http_client/client.py:151-190 — _build_event_hooks()
- http_client/config.py — HttpConfig
- storage/storage.py:65-149 — Storage facade
- task_queue/queue.py:91-135 — enqueue()
- metrics/collector.py:84-124 — MetricsCollector API
- fastapi/middleware.py:19-52 — RequestLoggingMiddleware
- fastapi/config.py:49-75 — FastApiConfig

## T9 — RateLimitError → AppError (DONE)
- Pattern for unifying custom exception → AppError subclass:
  1. Keep EXACT same `__init__` signature (positional params) so all callers/tests work unchanged
  2. Set domain attrs FIRST (self.key etc.), THEN call `super().__init__(code=..., message=..., http_status=..., context={...})`
  3. Reuse existing message string verbatim — tests use `match="请求频率超限"`
- No circular import: `basic_tool.errors` does NOT import `basic_tool.redis`, safe to import AppError in redis/decorators.py
- AppError already calls `super().__init__(message)` internally (Exception base), so str(e) still works
- Result: 482 passed (was 480), 0 regressions

## T19 — enable_log_injection 幂等守卫 + create_app 自动接入 (DONE)
- Idempotency guard pattern: module-level `_log_injection_enabled = False`, check at function entry with `global` keyword, set True after success
- `enable_log_injection()` patcher persists across `logger.remove()` calls — removing handlers does NOT remove the patcher from `_options`
- Existing test `test_enable_log_injection` calls enable twice: still passes with guard because patcher remains active from first call
- Idempotency test approach: reset guard to False, call once, capture `_options` identity, call again, assert `_options is` same object (no reassignment)
- `create_app()` integration: inline deferred import `from basic_tool.context.log_extra import enable_log_injection` inside `if config.log is not None:` block avoids import order issues
- Result: 96 passed (tests/context/ + tests/test_fastapi/), 0 regressions

## T10 — CryptoError 系继承 AppError (DONE)
- Pattern for hierarchy where ONLY base inherits AppError, subclasses override code/http_status:
  1. `CryptoError(AppError).__init__(self, message)` → `super().__init__(code="CRYPTO_ERROR", message=message, http_status=500)`
  2. Each subclass `__init__(self, message)` → `super().__init__(message)` then `self.code = "..."; self.http_status = ...` (override AFTER super().__init__)
  3. AppError.__init__ sets code/message/http_status/context, so subclass just overrides code/http_status afterward — no need to pass them up the chain
- Keeping `__init__(self, message: str)` signature means all existing `raise DecryptionError(f"...")` calls work UNCHANGED — zero edits to encrypt.py/password.py/sign.py
- No circular import: `basic_tool.crypto.exceptions` imports `basic_tool.errors` (one-way), errors module does NOT import crypto
- Tests verify: isinstance(AppError), isinstance(CryptoError), code, http_status, .detail/.status_code aliases, to_dict(), polymorphic catch (except CryptoError catches subclass)
- Result: 48 passed (tests/crypto/), 0 regressions. Added 18 new tests in test_exceptions.py

## #17 — task_queue Worker AppError 跳过重试 (DONE)
- `from basic_tool.errors import AppError` at top of worker.py — NO circular import (errors does not import task_queue)
- `_wrap_function` wrapper now wraps `return await func(*args, **kwargs)` in try/except AppError
- AppError → log WARNING with code+message, return `{"_error": True, "code": ..., "message": ...}` (ARQ sees success → no retry)
- Non-AppError → falls through naturally, re-raised for ARQ retry per max_tries
- `max_tries`/`job_timeout` attribute assignment on wrapper is preserved AFTER the try/except logic
- Testing approach: call `_wrap_function()` directly (not through ARQ) — for AppError assert dict returned + call_count==1; for ConnectionError use `pytest.raises`
- Result: 34 passed (tests/task_queue/), 0 regressions

## #3 — JWT 认证后注入 user_id 到请求上下文 (DONE)
- Injection point: AFTER `if user is None: raise` check, BEFORE `return user` — only reached on successful auth
- `user_id` value = `payload.get("sub")` extracted from decoded JWT (line 123)
- Import: `from basic_tool.context.ctx import ctx` alongside other basic_tool imports
- `ctx.set("user_id", user_id)` modifies the current context dict in-place — requires active `request_context()` to be meaningful
- **Test gotcha — shared default ContextVar pollution**: earlier TestClient-based tests (no middleware → no request_context) call `get_current_user`, which calls `ctx.set` on the shared default `{}` dict, polluting it for subsequent tests. Fix: call `ctx.clear()` inside `request_context()` in context-injection tests to get a clean slate
- Tests call `get_current_user(token=token)` directly (not via TestClient) inside `async with request_context()` — `Depends()` default is ignored when passing kwarg directly
- asyncio_mode=auto in pyproject.toml → async test functions work without `@pytest.mark.asyncio`
- Result: 18 passed (tests/test_fastapi/test_auth.py), 506 passed total, 0 regressions

## #12 — email 异步发送 @task 集成 (2026-06-13)
- `email/task.py` creates module-level `@task()` decorated `send_email_task(ctx, to, subject, body, content_type="text/plain", cc=None, bcc=None)` — ctx first param required by @task decorator
- `SmtpSender` has NO `init()` method — connection is lazy via `_ensure_connection()` on first `send()`. So `on_startup` just constructs `SmtpSender(config)` (no I/O), `on_shutdown` calls `await sender.close()`
- No circular import: `email/task.py` → `task_queue/task.py` is one-way (task_queue doesn't import email)
- `setup_email_worker(email_config)` returns `(on_startup, on_shutdown)` tuple — closures are fine here (NOT @task functions, just worker lifecycle callbacks)
- Email constructor accepts `to: str | list[str]` — passing `list[str]` from task params works directly
- Tests use AsyncMock for sender, patch.object(sender, "close", new_callable=AsyncMock) for close
- Pyright `**dict` unpacking into Pydantic models triggers false positives in test files — pre-existing pattern (test_sender.py has same errors), acceptable
- Result: 536 passed (was 506), 0 regressions. 12 new tests in tests/email/test_task.py

## Task #18 — concurrency 上下文继承文档化 (2026-06-13)
- Pure documentation task: added "请求上下文传播" docstring paragraphs to 5 files
- Files: concurrency/__init__.py, pool.py, batch.py, task_group.py, README.md
- Key doc point: asyncio.Task copies ContextVar snapshot at creation time (Python 3.11+)
- Context is SNAPSHOT (inherited, not shared/mutable across tasks)
- README added new "请求上下文自动传播" section with 2 examples (auto-propagation + snapshot isolation)
- All 31 concurrency tests pass; no logic changes
- Existing Pyright warning in timeout.py:33 is pre-existing (object type for coro param)

## #1 — http_client 出站请求自动注入 trace headers (DONE)
- `inject_headers_to_httpx()` with no args returns context-ONLY headers (empty dict if no context). Does NOT read request.headers.
- httpx `request.headers` is case-insensitive: `name not in request.headers` works correctly even when keys differ in case (e.g. "X-Trace-Id" vs "x-trace-id")
- `_build_event_hooks()` restructured: `on_request` added when `log_requests OR propagate_context` (was only `log_requests`). `on_response` only when `log_requests`.
- Injection logic: `for name, value in inject_headers_to_httpx().items(): if name not in request.headers: request.headers[name] = value` — naturally no-ops when no context (empty dict) and respects user-set headers
- Test pattern: `_header_capture_handler()` returns (captured_dict, handler). MockTransport handler iterates `request.headers` to snapshot all headers. Tests access lowercase keys (httpx normalizes: `captured.get("x-trace-id")`)
- Pre-existing task_queue test failures (test_queue.py) are from OTHER uncommitted work in tree — NOT from http_client changes. Confirmed via `git stash`.
- Result: 31 passed (tests/http_client/), 506+2 pre-existing failures in unrelated modules

## #14+#15 — storage 操作日志 + trace 关联 (DONE 2026-06-13)
- Pattern for adding loguru logging to async facade methods:
  1. `from loguru import logger` at module top (NOT basic_tool.logger)
  2. For void methods (put/delete): log BEFORE delegating to backend
  3. For methods returning a value (get/exists/list): MUST capture result in var, log, then return — never log inline in return statement (loses the value)
  4. Loguru `.info/.debug` first arg is message template, subsequent args are positional `.format()` substitutions: `logger.info("storage put | key={} size={}", key, len(data))`
- Trace correlation: just using `from loguru import logger` is sufficient — when `enable_log_injection()` active, the patcher injects ctx fields (trace_id) into every record's extra; no code change needed in callers
- Testing loguru output: most robust pattern in this repo (per tests/logger/test_logger.py) is `StringIO` sink + `logger.remove()` + `logger.add(buf, level="DEBUG", enqueue=False, format="{message}")` — insulates from global loguru state set up by other tests' setup() calls. capsys is fragile because setup() elsewhere may have replaced the default stderr sink with a configured one at INFO level (hiding DEBUG logs)
- Pre-existing Pyright errors on storage.py: `Storage._backend: StorageBackend | None` triggers `reportOptionalMemberAccess` for every `self._backend.X()` call and `reportReturnType` on `_create_backend` — these are NOT introduced by logging additions
- Result: 518 passed (was 506), 8 new tests in tests/storage/test_logging.py, 0 regressions

## #2 — task_queue 上下文序列化/反序列化传播 (DONE)
- **Enqueue side** (queue.py): `serialize_context()` called before `enqueue_job()`, result passed as `_context_snapshot=<dict>` kwarg. Returns `{}` when no active context.
- **Worker side** (worker.py `_wrap_function`): pops `_context_snapshot` from kwargs; if non-empty dict, wraps execution in `async with deserialize_context(snapshot):`; if None/empty, executes normally (backward compat).
- **Critical**: changed `build_settings` to ALWAYS wrap functions (removed `if max_tries or job_timeout` guard) — otherwise tasks without per-task meta wouldn't get context restoration.
- **Structure**: used nested `async def _execute()` inside wrapper to avoid duplicating the try/except AppError block between context-restored and non-restored paths.
- `deserialize_context(data)` returns `_RequestContext` which supports `async with` — context is restored for the task body, then automatically reset on exit.
- ARQ `enqueue_job(**kwargs)` passes all non-`_`-reserved kwargs to the task function — `_context_snapshot` flows through as a kwarg to the wrapper.
- **Test gotcha**: existing `assert_called_once_with` tests needed `_context_snapshot={}` added since there's no active context during tests.
- Result: 40 passed (tests/task_queue/), +6 new tests, 0 regressions

## T6 — @cached on_cache_hit/on_cache_miss 回调协议 (callback protocol)

**Goal:** Let external metrics code observe cache hit/miss rates without redis
importing metrics (which would create redis↔metrics cycle since
metrics/writer.py:13 already imports redis.Cache).

**Pattern — Callback Injection (依赖注入):**
- `cached()` gains two optional kwargs `on_cache_hit: Callable[[str], None] | None`
  and `on_cache_miss: Callable[[str], None] | None`, appended LAST to preserve
  existing param order.
- Callbacks receive the cache KEY (string), not the value — keeps them
  lightweight and uniform.
- Each invocation wrapped in `try/except Exception: pass` — callback failures
  must NEVER break caching logic. Silent swallow is the contract.

**Flow insertion points in the wrapper** (decorators.py):
1. HIT branch: after `cached_val is not _MISSING and await cache.exists(key)`
   evaluates true, before `return cached_val`.
2. MISS branch: after the hit check fails, BEFORE `result = await func(...)`.
   (Calling miss before executing the function keeps semantics intuitive:
   "we discovered we have to execute the function".)

**Tests** (use fakeredis via the `cache` fixture in tests/conftest.py):
- `test_cache_hit_miss_callbacks`: call decorated fn twice; first call should
  invoke `on_miss` once, second call should invoke `on_hit` once. Both should
  receive the same cache key string.
- `test_callbacks_default_none`: omit callbacks; normal cache behavior.
- `test_callback_exception_swallowed_on_hit`: callback raises; caching still
  returns the cached value.
- `test_callback_exception_swallowed_on_miss`: callback raises; function still
  executes and returns.
- Use `unittest.mock.MagicMock` for callback — it has `.assert_called_once()`
  and `.call_args.args[0]` which makes assertions concise.

**Verification trick — no metrics import:**
```bash
grep "import.*metrics" basic_tool/redis/decorators.py  # must return nothing
```

## #4 — middleware 请求指标采集 (DONE 2026-06-13)
- **BaseHTTPMiddleware `__init__` override**: when adding kwargs to `add_middleware(SomeMiddleware, kwarg=val)`, must override `__init__(self, app, kwarg=default)` and call `super().__init__(app)` — Starlette passes `app` positionally and extra kwargs by keyword
- **Pydantic non-pydantic-typed field**: `FastApiConfig.metrics: MetricsCollector | None` requires `model_config = {"arbitrary_types_allowed": True}` on the model (same pattern as `email/models.py`). Without it, Pydantic rejects the custom class type at validation
- **Import path for MetricsCollector**: `from basic_tool.metrics.collector import MetricsCollector` in both config.py and middleware.py — NO circular import (metrics → redis → errors, nothing imports fastapi back). Verified safe, no TYPE_CHECKING needed (codebase convention)
- **Zero-overhead pattern**: `if self._metrics is not None:` guard before the try/except — None default means no metric recording at all; the try/except only wraps the recording calls (counter/histogram), not the logging
- **MetricsCollector constructor**: `MetricsCollector(MetricsConfig(service_name="..."), endpoint="http://...")` — counter/gauge/histogram just append to `_buffers` defaultdict, no init() needed for in-memory testing. Inspect `collector._buffers["metric_name"]` for assertions
- **Test approach**: 3 tests — (1) real collector via create_app + GET /health, assert `_buffers` contents; (2) default config (metrics=None) GET /health works; (3) Mock with `counter.side_effect = RuntimeError` via `app.add_middleware(..., metrics=bad_metrics)` + `raise_server_exceptions=False`, assert 200
- **app.py pre-existing Pyright errors**: lines 65/83/150 have lifespan AsyncIterator typing errors — NOT introduced by this change (my edit was line 166 only)
- Result: 549 passed (was 537), 1 skipped, 0 regressions. 3 new tests in test_middleware.py

## #5 — errors on_error 回调协议 (DONE 2026-06-13)
- **Pattern identical to T6 (redis @cached callbacks)**: add optional `on_error: Callable[[str, int], None] | None = None` as LAST param, wrap invocation in `try/except Exception: pass`.
- **log.py**: `on_error` appended after `trace_id` (all params are keyword-only via `*`). Callback invoked AFTER logging completes (so even slow metrics won't delay logging). AppError → `(exc.code, exc.http_status)`; non-AppError → `("UNKNOWN", 500)`.
- **handler.py**: `on_error` added as 3rd positional param to `setup_error_handlers(app, config, on_error)`, passed through to all 3 internal `log_error()` calls. Import `Callable` from typing alongside `Mapping`.
- **grep gotcha**: `grep "import.*metrics"` matches Chinese docstring text "不直接 import metrics" literally. Reworded to "不直接依赖 metrics 模块" so the exact task grep command `grep "import.*metrics" basic_tool/errors/*.py` returns NOTHING (exit 1).
- **AppError import**: already done via delayed import inside function body (`from basic_tool.errors.app_error import AppError`) — reused the existing `isinstance(exc, AppError)` check already in the function for the callback branch.
- **Tests** (5 new in TestLogErrorCallback): callback invoked with correct (code, status) for 4xx + 5xx; None default works; callback raising RuntimeError doesn't break flow; non-AppError passes ("UNKNOWN", 500). Use `unittest.mock.MagicMock` + `.assert_called_once_with(...)`.
- Result: 37 passed (tests/errors/), 549 passed total, 0 regressions

## #7 — http_client 出站请求指标 (DONE 2026-06-13)
- **Pydantic v2 arbitrary types**: `MetricsCollector` is NOT a Pydantic model → need `model_config = ConfigDict(arbitrary_types_allowed=True)` on HttpConfig
- **Import safety verified**: `http_client.config → metrics.collector → metrics.config + metrics.models` (NO path back to http_client). `python -c "import basic_tool.http_client; import basic_tool.metrics"` succeeds
- **Hook restructure in `_build_event_hooks`**: 
  - `need_request_hook` now includes `metrics is not None` (was only log/propagate)
  - Introduced `need_start_time = log_requests or metrics is not None` — `_start_time` must be set for histogram even when logging off
  - `on_response` registered when `log_requests or metrics is not None`; logging block guarded by `if self._config.log_requests`; metrics block guarded by `if self._config.metrics is not None` with try/except + debug log fallback
- **MetricsCollector API confirmed**: `counter(name, value=1.0, labels=None)`, `histogram(name, value, labels=None)` — value is positional for histogram
- **Metric names**: `http_client_requests_total` (counter, labels: method/url/status) and `http_client_request_duration_seconds` (histogram, labels: method/url). Used EXPECTED OUTCOME name (with "request") over MUST DO shorthand
- **Retry counter SKIPPED**: RetryTransport only receives RetryConfig, not HttpConfig. It's a public class usable independently (README L130-143). Adding metrics param would change public API + mix concerns. Documented rationale in README
- **Test pattern**: construct MetricsCollector WITHOUT calling `await collector.init()` (avoids spawning httpx client + flush task). Directly inspect `collector._buffers[name]` for recorded MetricPoint objects — `point.labels` dict, `point.value` float
- **Zero-overhead test**: `HttpConfig(log_requests=False, propagate_context=False)` → `_build_event_hooks()` returns `{}` (no hooks at all)
- Result: 37 passed (tests/http_client/, +6 new), 555 passed total, 0 regressions, 0 LSP errors

## #7 FIX — RetryTransport 重试指标补齐 (DONE 2026-06-13)
- F4 Scope Fidelity found transport.py was not modified for retry metrics despite plan requirement. Follow-up fix.
- `RetryTransport.__init__` gains OPTIONAL `metrics: MetricsCollector | None = None` param (default None = zero overhead, backward compat for standalone usage)
- Added `_record_retry(url)` helper method: early-return if `self._metrics is None`; try/except wraps `self._metrics.counter(...)` with debug log fallback — retry logic NEVER breaks due to metrics
- Called `_record_retry(request.url)` AFTER each of the 3 logger calls: status-code retry (L78), connection-error retry (L88), exhausted (L104)
- `client.py _build_transport`: passes `metrics=self._config.metrics` to RetryTransport constructor — single source of truth flows from HttpConfig
- **Edit tool gotcha**: `edit` with non-unique `oldString` hits FIRST occurrence. My `assert transport.state == "open"` matched inside `test_half_open_after_recovery_timeout` (mid-class), not the intended last test → broke file structure. Fix: read larger context, replace from a unique anchor point
- **Exhausted retry count**: with `max_retries=3` all-503, total counters = 4 (3 status retries + 1 exhausted). Test assertion must account for all 3 retry-point recordings, not just loop iterations
- Pre-existing Pyright error at transport.py `raise last_exc` (Optional type) — NOT introduced by this change
- Result: 42 passed (tests/http_client/, +5 new), 560 passed total, 0 regressions
