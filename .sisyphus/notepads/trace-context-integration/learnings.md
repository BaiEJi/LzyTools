# Learnings — trace-context-integration

## Conventions
- 项目使用 pytest，测试在 tests/ 目录下，镜像 basic_tool/ 结构
- 测试文件 test_ctx.py 使用方法内 import（非顶层 import）
- 日志断言使用 StringIO 作为 loguru sink
- 异常处理器测试使用 TestClient(app, raise_server_exceptions=False)
- context 基于 ContextVar[dict]，_RequestContext 使用 token-based reset
- id_generator.TraceContext: root() / child_span() / to_traceparent() / from_traceparent()
- from_traceparent() 会抛 ValueError（malformed 场景需 catch）

## Key Design Decisions
- W3C traceparent 头格式: 00-{trace_id 32hex}-{span_id 16hex}-01
- ContextMiddleware 创建 child span（入口服务 = 独立 span）
- 中间件顺序: CORS(最先添加=最内层) -> RequestLoggingMiddleware -> ContextMiddleware(最后添加=最外层)
- clean break: 不加 request_id 别名

## middleware ordering in starlette
- add LAST = outermost = runs FIRST on request
- ContextMiddleware 必须最后添加（最外层，最先执行，设置 context）
- RequestLoggingMiddleware 次之（内层，读 context）

## contextvar propagation
- BaseHTTPMiddleware 的 call_next spawns child task (copies context)
- set-in-outer -> read-in-inner: WORKS
- set-in-inner -> read-in-outer: DOES NOT WORK
- T1 has dedicated propagation verification test (#1 risk)

## T-FastApiConfig-ContextSwitch (Wave 1)
- Tests live at workspace root `/home/lizy/projects/LzyProjs/tests/`, NOT under `basic_tool/` package dir. The CWD during dev is the `basic_tool` package folder; always use absolute paths starting from workspace root.
- `FastApiConfig` field order: all fields have defaults, so append new bool switches after `enable_error_handlers` — no ordering issues.
- Project rule: every test method needs a Chinese docstring (matches existing convention + CLAUDE.md mandate). Docstrings are NOT ai-slop here.
- fastapi/README.md has a code block listing FastApiConfig fields — must be kept in sync on every field change.

## T2: errors 包适配 request_id -> trace_id (2026-06-13)

### 完成
- `basic_tool/errors/log.py`: `log_error()` 参数 `request_id` -> `trace_id`，`extra["request_id"]` -> `extra["trace_id"]`，docstring 同步。
- `basic_tool/errors/handler.py`: 顶部新增 `from basic_tool.context.ctx import ctx`；3 个异常处理器中 `request_id=getattr(request.state, "request_id", "")` -> `trace_id=ctx.get("trace_id", "")`。

### 关键发现
1. **测试文件无需改动**：`tests/errors/test_log.py` 和 `tests/errors/test_handler.py` 中**没有任何 `request_id` 引用**——测试既不传该参数，也不在断言中检查它。因此 4.3/4.4 节"如有则同步更新"的条件不成立，零改动。重命名后的参数是可选 kwarg，现有测试不传它，仍正常工作。
2. **32 tests 全部通过**，LSP 诊断无 error/warning。
3. **README 待同步（flag for orchestrator）**：`basic_tool/errors/README.md` 第 236 行的 prose 仍提到 `request_id`（"...包含请求方法、路径和 request_id"）。本任务 MUST DO 严格限定 4 个文件，未改 README。建议编排器单独安排 README 扫描更新任务（可能涉及多个 T 子任务的累积变更，集中处理更合适）。
4. **handler.py 3 处替换的区分技巧**：3 个 `getattr(request.state, "request_id", "")` 完全相同，需用上下文（所在 handler 函数名 / 紧邻的返回状态码）来唯一定位，不能用 replaceAll。
5. **ctx.get() 在无中间件时返回 None**：默认值由 `ctx.get("trace_id", "")` 的第二参数兜底为 `""`，符合 `log_error` 期望的 falsy 语义（空串跳过 extra 注入）。

## T5: README 文档更新 (2026-06-13)

### 完成情况
- **context/README.md**: T1 已完整更新，无需修改。_DEFAULT_HEADER_MAP 正确（trace_id/span_id/tenant_id/user_id），ContextMiddleware 描述已改为 W3C traceparent，无 request_id 残留。
- **errors/README.md**: 仅 1 处残留（line 236 "包含请求方法、路径和 request_id"），已改为 trace_id 并补充来源说明（ctx.get("trace_id")）。
- **fastapi/README.md**: 中间件栈描述需更新。X-Request-ID 引用已移除，补充了 ContextMiddleware（W3C traceparent）作为栈中第 2 层，并为每个中间件标注了对应的 enable_* 开关。

### 关键发现
- app.py（create_app）目前尚未 wire up `enable_context_middleware`，仅有 config 字段和 ContextMiddleware 类存在。wiring 可能是 T3/T4 的后续工作。文档按预期最终状态编写（config 默认 True，所有构建块已就位）。
- RequestLoggingMiddleware 现在从 ctx.get("trace_id") 读取 trace_id（不再注入 X-Request-ID header）。
- handler.py 中三个异常处理器均通过 `ctx.get("trace_id", "")` 获取 trace_id，不再依赖 request.state。

### 验证
- `grep -rn "request_id\|X-Request-ID" context/README.md errors/README.md fastapi/README.md` → 0 匹配
- `grep -ln "traceparent" context/README.md fastapi/README.md` → 2 文件命中

## T5-final: create_app 集成 + ContextMiddleware bug fix (2026-06-13)

### 完成情况
- `basic_tool/fastapi/app.py`: 添加 `from basic_tool.context.middleware import ContextMiddleware` 导入，在 `create_app()` 中 `RequestLoggingMiddleware` 之后、`error_handlers` 之前注册 `ContextMiddleware`（受 `config.enable_context_middleware` 控制）。
- `tests/test_fastapi/test_app.py`: `TestCreateAppMiddleware` 类替换为 6 个新测试（traceparent 传播、disabled 开关、端到端 child span、异常响应 traceparent）。
- `basic_tool/context/middleware.py`: **genuine bug fix** — 从 `BaseHTTPMiddleware` 转为纯 ASGI 中间件。
- `basic_tool/errors/handler.py`: **genuine bug fix** — `global_exception_handler` 从 `scope["basic_tool.traceparent"]` 读取并添加到 500 响应头。
- 480 tests passed, 1 skipped (pre-existing).

### 关键发现: Starlette 1.2.1 BaseHTTPMiddleware + Exception handler 架构缺陷
1. **`@app.exception_handler(Exception)` 注册到 `ServerErrorMiddleware`，不是 `ExceptionMiddleware`**。Starlette 将 `Exception`/500 handler 从 `exception_handlers` dict 中提取出来，传给 `ServerErrorMiddleware.handler`。其余 handler（AppError、RequestValidationError 等）传给 `ExceptionMiddleware`。
2. **`ServerErrorMiddleware` 位于所有 user middleware 之外**。当异常传播到 `ServerErrorMiddleware`，它创建的响应直接通过原始 `send` 发送，绕过所有 user middleware。
3. **`BaseHTTPMiddleware.call_next` 在异常时重新抛出**（`raise app_exc`），而非返回错误响应。这导致 `dispatch` 中 `response = await call_next(request); response.headers["traceparent"] = ...` 这段代码在异常时永远不执行。
4. **修复方案**: (a) ContextMiddleware 转为纯 ASGI，wrap `send` 注入 traceparent 到所有正常响应（包括 AppError/validation）；(b) ContextMiddleware 将 traceparent 写入 `scope["basic_tool.traceparent"]`（scope 在整个请求生命周期内持久存在）；(c) `global_exception_handler` 从 scope 读取 traceparent 添加到 500 响应头。
5. **纯 ASGI 中间件仍然兼容 `app.add_middleware(ContextMiddleware)`** — Starlette 接受任何有 `__init__(self, app)` + `__call__(self, scope, receive, send)` 的类。
6. **ContextVar 传播在纯 ASGI 中仍然有效** — anyio task group 创建子任务时复制 context，inner middleware (RequestLoggingMiddleware as BaseHTTPMiddleware) 仍能读到 ctx.get("trace_id")。

### 文件路径
- 包目录 = `/home/lizy/projects/LzyProjs/basic_tool/`（这既是 CWD 也是 Python 包根）
- 测试目录 = `/home/lizy/projects/LzyProjs/tests/`（在工作区根，不在包目录下）

## F3 QA Learnings (2026-06-13)

### Starlette Exception Handler Routing (CRITICAL)
Starlette's `build_middleware_stack` splits exception handlers:
- `Exception` and `500` handlers -> **ServerErrorMiddleware** (outermost, OUTSIDE user middleware)
- All other handlers -> **ExceptionMiddleware** (innermost, INSIDE user middleware)

This means ContextMiddleware's ContextVar is NOT available in the catch-all Exception handler.
Test with AppError handler (which IS inside ContextMiddleware) works perfectly.

### TestClient Loguru Format
When capturing loguru output via `io.StringIO()`, use `format='{level}||{extra}||{message}'`
to render bound extra fields. Using `format='{message}'` hides extras, making it appear
that trace_id is missing when it's actually present in the bound logger.

### ContextMiddleware is Pure ASGI (Correct Design)
The pure ASGI implementation (not BaseHTTPMiddleware) correctly sets traceparent response
headers even during exceptions, because the `send_with_traceparent` wrapper is always called.
BaseHTTPMiddleware would fail here because `call_next` re-raises on exception.

### W3C Trace Context Verification
- `TraceContext.from_traceparent()` correctly parses and `.child_span()` creates new span_id
- Malformed traceparent triggers ValueError -> caught -> degrades to `TraceContext.root()`
- `get_propagation_headers()` correctly reconstructs traceparent from trace_id + span_id

### Middleware Stack Order in create_app
```
ServerErrorMiddleware (outermost)
  -> ContextMiddleware (sets trace_id/span_id/parent_span_id in ContextVar)
    -> RequestLoggingMiddleware (reads trace_id from ContextVar for access log)
      -> CORSMiddleware
        -> ExceptionMiddleware (handles AppError etc.)
          -> Router/Route
```
ContextMiddleware added LAST = outermost user middleware = first to execute.
