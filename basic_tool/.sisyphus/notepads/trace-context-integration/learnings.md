# Learnings — Context Package W3C TraceContext Migration

## Architecture
- `request_context(**kwargs)` factory in `ctx.py` now auto-generates `trace_id` (128-bit hex via `TraceGenerator().trace_id()`) instead of `request_id` (uuid4).
- Module-level singleton `_trace_gen = TraceGenerator()` avoids repeated instantiation.
- `ContextMiddleware` uses W3C `traceparent` header: parses via `TraceContext.from_traceparent().child_span()` (preserves upstream trace_id, generates new span_id, sets parent_span_id). Malformed/missing → falls back to `TraceContext.root()`.
- `propagation.py` `_DEFAULT_HEADER_MAP` now maps `trace_id`/`span_id` (not `request_id`). `get_propagation_headers()` additionally reconstructs `traceparent` header when both trace_id and span_id are present in context.

## Key API behaviors
- `TraceContext.from_traceparent(header)` raises `ValueError` on malformed input — must catch and degrade to `root()`.
- `TraceContext.root()` generates trace_id (32 hex) + span_id (16 hex), parent_span_id="".
- `TraceContext.child_span()` preserves trace_id, generates new span_id, sets parent_span_id=old span_id.
- `to_traceparent()` returns `00-{trace_id}-{span_id}-01`.

## ContextVar propagation through middleware
- Confirmed WORKING: ContextMiddleware added LAST (outermost) sets context, inner middleware can read it. Test `test_contextvar_propagation_through_middleware` verifies this.
- No need to rewrite BaseHTTPMiddleware as pure ASGI.

## Test patterns
- Tests use method-internal imports (not top-level) — preserved this style.
- 28 tests total (was 25): added `test_middleware_child_span`, `test_middleware_malformed_traceparent`, `test_contextvar_propagation_through_middleware`.
- For propagation tests: when only `trace_id` is set (no `span_id`), `traceparent` header is NOT reconstructed (both required).

## Pre-existing LSP errors (NOT introduced by this change)
- `log_extra.py:69-70`: Pyright complains about `_inject_context` patcher type and `_options` attribute access. Pre-existing.
- `propagation.py:122`: Pyright return type complaint on `deserialize_context`. Pre-existing.

## Files modified
- `basic_tool/context/ctx.py` — removed `import uuid`, added `TraceGenerator` import + singleton, `request_context()` uses `trace_id`
- `basic_tool/context/middleware.py` — full rewrite of `dispatch()` for W3C traceparent, removed `import uuid`
- `basic_tool/context/propagation.py` — header map update + traceparent reconstruction
- `basic_tool/context/log_extra.py` — docstring only (request_id → trace_id)
- `basic_tool/context/README.md` — updated API docs and examples
- `tests/context/test_ctx.py` — full TDD rewrite (28 tests, all pass)

## T5: RequestLoggingMiddleware 改造为消费者 (2026-06-13)

### 改造内容
- `fastapi/middleware.py`: 移除 `import uuid`、`request.state.request_id` 赋值、`X-Request-ID` 响应头设置
- 新增 `from basic_tool.context.ctx import ctx`，日志中 `request_id={}` → `trace_id={}`
- `trace_id = ctx.get("trace_id", "")` 在无 ContextMiddleware 时返回空字符串（不崩溃），已验证

### 测试验证
- Starlette 中间件栈叠顺序确认: 后添加 = 最外层 = 最先执行
- ContextMiddleware 后添加（外层）→ 设置 context → RequestLoggingMiddleware 内层读取 trace_id
- 无 ContextMiddleware 时，TestClient 请求仍正常返回 200，无 traceparent 响应头
- 8 tests passed: TestAppError(2) + TestRequestLoggingMiddleware(2) + TestSetupErrorHandlers(4)

### 注意
- `setup_error_handlers` 兼容函数和 AppError 导入保持不变（向后兼容）
- 不再设置任何响应头（traceparent 由 ContextMiddleware 负责）
