# W3C Trace Context 集成：替换 request_id 为 trace_id

## TL;DR

> **Quick Summary**: 将 ContextMiddleware 集成到 create_app() 中，用 id_generator 的 W3C TraceContext（trace_id / span_id）替换现有的 uuid4 request_id，实现完整的分布式链路追踪能力。
> 
> **Deliverables**:
> - 每个 FastAPI 请求自动获得隔离的 context（trace_id, span_id, client_ip）
> - W3C 标准 traceparent 头的提取/创建/传播全链路
> - RequestLoggingMiddleware 改为纯消费者，消除双 ID 生成隐患
> - Error handlers 统一从 context 读取 trace_id
> - 所有相关测试和 README 同步更新
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: T1(context) -> T4(logging) -> T6(create_app) -> F1-F4(verification)

---

## Context

### Original Request
用户希望每个接口访问自动获得隔离的 context，并用 id_generator 生成的 trace_id 替代 uuid4 request_id。

### Interview Summary
**Key Discussions**:
- 确认 13 个组件，context 模块已有完整的 ContextVar + middleware 基础设施
- 当前 create_app() 未注册 ContextMiddleware，且与 RequestLoggingMiddleware 双重生成 ID
- 用户要求最优方案：完整 W3C Trace Context
- 测试策略：TDD（测试先行）

**Research Findings**:
- id_generator.TraceContext 已实现完整 W3C: root() / child_span() / to_traceparent() / from_traceparent()
- request_id 涉及 10 个源文件、46 处引用
- 现有 57 个测试文件，pytest 基础设施完善
- log_extra.py 代码无需改动（动态注入所有 context 键），但 docstring 示例需更新

### Metis Review
**Identified Gaps** (addressed):
- 遗漏 log_extra.py: 代码无需改（动态注入），docstring 示例需更新 -> 纳入 T1
- 遗漏 fastapi/config.py: 需新增 enable_context_middleware 开关 -> 纳入 T3
- malformed traceparent: from_traceparent() 会抛 ValueError，中间件必须 catch -> 纳入 T1
- access logging 丢失风险: RequestLoggingMiddleware 的访问日志功能必须保留 -> T4 明确保留
- 文件数纠正: 9 个源文件（非 7）、5 个测试文件（非 4）、3 个 README -> 已反映在任务中
- ContextVar 传播风险: BaseHTTPMiddleware 的 task spawning 是否影响传播 -> T1 专项验证测试
- propagation 冲突: 已有 trace_id->X-Trace-Id 映射，需增加 traceparent 重建 -> T1 处理
- 异常时响应头丢失: 需确保 traceparent 响应头在异常时也能设置 -> T1 处理

---

## Work Objectives

### Core Objective
用 W3C Trace Context 替换 uuid4 request_id，让 create_app() 一行代码即可获得完整的请求级上下文隔离和分布式追踪能力。

### Concrete Deliverables
- context/ctx.py: request_context() 自动生成 trace_id（替代 request_id）
- context/middleware.py: ContextMiddleware 使用 TraceContext，提取/创建 traceparent
- context/propagation.py: 重建 traceparent 传出，移除 request_id 映射
- fastapi/middleware.py: RequestLoggingMiddleware 从 context 读取 trace_id，保留访问日志
- fastapi/app.py: create_app() 注册 ContextMiddleware
- fastapi/config.py: 新增 enable_context_middleware 开关
- errors/handler.py + errors/log.py: 从 context 读取 trace_id
- 全部相关测试和 README 同步

### Definition of Done
- [x] pytest tests/ -v 全部通过（0 failures）
- [x] 请求无 traceparent 头时自动生成 root trace（32 hex trace_id）
- [x] 请求有 traceparent 头时正确解析并创建 child span（trace_id 不变，span_id 变化）
- [x] 响应头包含 traceparent（格式 00-{trace_id}-{span_id}-01）
- [x] malformed traceparent 不崩溃，降级为 root trace
- [x] 访问日志包含 trace_id
- [x] 错误日志包含 trace_id
- [x] 并发请求 trace_id 隔离

### Must Have
- W3C traceparent 头标准格式（00-{trace_id}-{span_id}-01）
- ContextMiddleware 创建 child span（入口服务作为独立 span）
- RequestLoggingMiddleware 保留访问日志功能（method/path/status/elapsed）
- malformed/empty traceparent 优雅降级为 root trace
- ContextVar 在中间件栈中正确传播（外层 set -> 内层 read）
- 所有 request_id -> trace_id 的改名（clean break，不留别名）

### Must NOT Have (Guardrails)
- 不修改 basic_tool/id_generator/ 任何文件（已完善）
- 不实现 W3C tracestate 头支持（超出范围）
- 不添加 trace sampling 逻辑（flags 固定 "01"）
- 不将 BaseHTTPMiddleware 改写为 pure ASGI（除非传播测试失败）
- 不在错误响应 JSON body 中添加 trace_id（仅在日志中）
- 不修复 X-Request-Id vs X-Request-ID 大小写不一致（属于既有问题，不在范围内）
- 不修改 ContextManager、_RequestContext、_context_data 存储机制（只改存的键名）
- 不改变 log_error() 签名（仅 request_id -> trace_id 改名）
- 不处理 WebSocket 请求的上下文（BaseHTTPMiddleware 仅处理 HTTP，WS 明确排除）
- 不加 request_id 向后兼容别名（clean break）

---

## Verification Strategy

> ZERO HUMAN INTERVENTION - ALL verification is agent-executed.

### Test Decision
- Infrastructure exists: YES（pytest，57 个测试文件）
- Automated tests: TDD（测试先行）
- Framework: pytest
- Workflow: 每个 task 先更新测试（RED），再改实现（GREEN）

### QA Policy
- Middleware 集成: 使用 fastapi.testclient.TestClient
- 日志断言: 使用 io.StringIO 作为 loguru sink
- Context 隔离: 使用 asyncio.gather()
- 异常处理: 使用 TestClient(app, raise_server_exceptions=False)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - foundation, 3 parallel):
|- T1: Context 包全面改造 [deep]
|- T2: Errors 包适配 [unspecified-high]
|- T3: Config 开关 [quick]

Wave 2 (After Wave 1 - FastAPI integration, 2 parallel):
|- T4: RequestLoggingMiddleware 改造 [unspecified-high]
|- T5: README 文档更新 [writing]

Wave 3 (After Wave 2 - final wiring, 1 task):
|- T6: create_app 集成 [deep]

Wave FINAL (After ALL tasks - 4 parallel reviews):
|- F1: Plan compliance audit (oracle)
|- F2: Code quality review (unspecified-high)
|- F3: Real manual QA (unspecified-high)
|- F4: Scope fidelity check (deep)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| T1 | - | T4, T5, T6 |
| T2 | - | T5, T6 |
| T3 | - | T6 |
| T4 | T1 | T6 |
| T5 | T1, T2 | - |
| T6 | T1, T3, T4 | F1-F4 |
| F1-F4 | ALL | - |

### Agent Dispatch Summary

- Wave 1: 3 tasks - T1 deep, T2 unspecified-high, T3 quick
- Wave 2: 2 tasks - T4 unspecified-high, T5 writing
- Wave 3: 1 task - T6 deep
- FINAL: 4 tasks - F1 oracle, F2 unspecified-high, F3 unspecified-high, F4 deep

---

## TODOs

- [x] 1. **Context 包全面改造*（ctx.py + middleware.py + propagation.py + log_extra.py + test_ctx.py）

  **What to do**:
  - **ctx.py**: `request_context()` 自动生成从 `request_id`(uuid4) 改为 `trace_id`(TraceGenerator().trace_id())。移除 `import uuid`，改为从 `basic_tool.id_generator` 导入 `TraceGenerator`
  - **context/middleware.py**: ContextMiddleware 重写为 W3C:
    - 提取 `traceparent` 头（非 X-Request-Id）
    - 有头: `TraceContext.from_traceparent(header)` 然后 `.child_span()`
    - 无头或 malformed: `TraceContext.root()`（捕获 ValueError 降级）
    - 存入 context: trace_id, span_id, parent_span_id, client_ip
    - 响应头: `traceparent`，用 try/finally 确保即使异常也设置
  - **context/propagation.py**: 移除 `request_id: X-Request-Id`，添加 `span_id: X-Span-Id`，保留 `trace_id: X-Trace-Id`。`get_propagation_headers()` 额外重建 `traceparent`（从 trace_id+span_id 拼装）
  - **context/log_extra.py**: 仅更新 docstring 示例 `request_id` -> `trace_id`（代码无需改）
  - **tests/context/test_ctx.py**: TDD 全量更新 ~40 处断言 request_id -> trace_id。新增: child span 验证、root trace 生成、malformed 降级、ContextVar 传播专项测试

  **Must NOT do**: 不修改 ContextManager/_RequestContext/_context_data；不实现 tracestate；不加 sampling

  **Recommended Agent Profile**:
  - Category: `deep`（4 源文件 + 1 大型测试文件，紧密耦合）
  - Skills: []

  **Parallelization**: Wave 1 parallel with T2, T3 | Blocks: T4, T5, T6 | Blocked By: None

  **References**:
  - `basic_tool/context/ctx.py:133-145` - request_context() 当前 auto-gen 逻辑
  - `basic_tool/context/middleware.py:37-64` - ContextMiddleware 当前 X-Request-Id 提取
  - `basic_tool/context/propagation.py:36-66` - _DEFAULT_HEADER_MAP 和 get_propagation_headers()
  - `basic_tool/id_generator/trace.py:42-109` - TraceContext: root(), child_span(), to_traceparent(), from_traceparent()
  - `basic_tool/id_generator/generator.py:166-172` - TraceGenerator.trace_id()
  - `tests/context/test_ctx.py` - 全部 344 行现有测试结构

  **WHY References Matter**:
  - trace.py root()/child_span() 是创建 trace 的核心 API
  - from_traceparent() 会抛 ValueError（malformed 场景需 catch）
  - to_traceparent() 生成响应头格式 00-{trace_id}-{span_id}-01
  - propagation.py 需额外重建 traceparent，不只是 key-value 映射

  **QA Scenarios**:

  ```
  Scenario: request_context() 自动生成 trace_id
    Tool: Bash (python -c)
    Steps:
      1. with request_context(): tid = ctx.get('trace_id')
      2. 断言 len(tid)==32 且全是 hex 字符
    Expected Result: "32:True"
    Evidence: .sisyphus/evidence/task-1-auto-gen-trace-id.txt

  Scenario: 有 traceparent 头时创建 child span
    Tool: Bash (TestClient)
    Steps:
      1. GET /test with "traceparent: 00-abcdef0123456789abcdef0123456789-1111111111111111-01"
      2. 断言 trace_id=="abcdef0123456789abcdef0123456789"（保留）
      3. 断言 span_id!="1111111111111111"（变化）
      4. 断言 parent_span_id=="1111111111111111"
    Expected Result: child span 正确创建
    Evidence: .sisyphus/evidence/task-1-child-span.json

  Scenario: 无 traceparent 头时生成 root trace
    Tool: Bash (TestClient)
    Steps:
      1. GET /test（无 trace 相关头）
      2. 断言响应头 traceparent 格式 00-{32hex}-{16hex}-01
    Expected Result: 新 root trace 生成
    Evidence: .sisyphus/evidence/task-1-root-trace.json

  Scenario: malformed traceparent 优雅降级
    Tool: Bash (TestClient)
    Steps:
      1. GET /test with "traceparent: garbage"
      2. 断言 HTTP 200 不崩溃
      3. 断言响应头有合法 traceparent（新 root）
    Expected Result: 降级为 root trace
    Evidence: .sisyphus/evidence/task-1-malformed-fallback.json

  Scenario: ContextVar 传播验证（#1 技术风险）
    Tool: Bash (TestClient)
    Steps:
      1. 栈叠 ContextMiddleware(外) + RequestLoggingMiddleware(内)
      2. GET /test，路由中读 ctx.get("trace_id")
      3. 断言非 None
    Expected Result: trace_id 在路由中可读（传播成功）
    Failure Indicators: None（传播失败需改 pure ASGI）
    Evidence: .sisyphus/evidence/task-1-contextvar-propagation.json

  Scenario: propagation 重建 traceparent
    Tool: Bash (python -c)
    Steps:
      1. with request_context(trace_id="a"*32, span_id="1"*16): headers = get_propagation_headers()
      2. 断言 headers["traceparent"]=="00-aaaa...-1111...-01"
      3. 断言 headers["X-Trace-Id"]=="a"*32
    Expected Result: traceparent 正确重建
    Evidence: .sisyphus/evidence/task-1-propagation.txt
  ```

  **Commit**: YES | Message: `refactor(context): replace request_id with W3C trace_id` | Pre-commit: `pytest tests/context/ -v`

---

- [x] 2. **Errors 包适配*（errors/log.py + errors/handler.py + tests/errors/test_log.py + tests/errors/test_handler.py）

  **What to do**:
  - **errors/log.py**: `log_error()` 参数 `request_id: str = ""` 改为 `trace_id: str = ""`。docstring 同步更新。`extra["request_id"]` 改为 `extra["trace_id"]`
  - **errors/handler.py**: 3 处 `request_id=getattr(request.state, "request_id", "")` 改为从 context 读取:
    - 导入: `from basic_tool.context.ctx import ctx`
    - 改为: `trace_id=ctx.get("trace_id", "")`
    - 参数名同步改为 `trace_id=`
  - **tests/errors/test_log.py**: 所有 `request_id=` 参数改为 `trace_id=`，断言中 `request_id` 改为 `trace_id`
  - **tests/errors/test_handler.py**: 如果有 request_id 相关断言则同步更新；确保用 TestClient(app, raise_server_exceptions=False) 模式

  **Must NOT do**: 不改 log_error() 签名结构（仅改名）；不在错误 JSON body 中加 trace_id

  **Recommended Agent Profile**:
  - Category: `unspecified-high`（2 源文件 + 2 测试文件，中等复杂度）
  - Skills: []

  **Parallelization**: Wave 1 parallel with T1, T3 | Blocks: T5, T6 | Blocked By: None

  **References**:
  - `basic_tool/errors/log.py:15-83` - log_error() 函数，参数 request_id 在第 21 行
  - `basic_tool/errors/handler.py:31-88` - 3 个异常处理器，各有一处 getattr(request.state, "request_id")
  - `tests/errors/test_log.py` - 现有 log_error 测试
  - `tests/errors/test_handler.py` - 现有异常处理器测试

  **WHY References Matter**:
  - handler.py 第 39/61/83 行是三个 getattr 调用点，需逐一替换为 ctx.get
  - log.py 第 47-48 行 extra["request_id"] 是日志字段名，需改为 trace_id
  - 测试文件需匹配新参数名

  **QA Scenarios**:

  ```
  Scenario: 错误日志包含 trace_id
    Tool: Bash (python -c with StringIO sink)
    Steps:
      1. 构造 app，注册 ContextMiddleware + setup_error_handlers
      2. 路由 raise RuntimeError("test")
      3. 用 StringIO 捕获 loguru 输出
      4. 断言输出包含 "trace_id=" 且值非空
    Expected Result: 错误日志中有 trace_id
    Evidence: .sisyphus/evidence/task-2-error-log-trace-id.txt

  Scenario: 无 context 时不崩溃
    Tool: Bash (python -c)
    Steps:
      1. 不注册 ContextMiddleware，仅 setup_error_handlers
      2. 触发 AppError
      3. 断言返回正确 status_code（不崩溃）
    Expected Result: 优雅处理，trace_id 为空字符串
    Evidence: .sisyphus/evidence/task-2-no-context.json

  Scenario: AppError 返回正确状态码
    Tool: Bash (TestClient)
    Steps:
      1. raise AppError(code="NOT_FOUND", message="test", http_status=404)
      2. 断言 status_code==404, json()["code"]=="NOT_FOUND"
    Expected Result: 标准化错误响应
    Evidence: .sisyphus/evidence/task-2-app-error.json
  ```

  **Commit**: YES | Message: `refactor(errors): read trace_id from context` | Pre-commit: `pytest tests/errors/ -v`

---

- [x] 3. **Config 开关*（fastapi/config.py + tests/test_fastapi/test_config.py）

  **What to do**:
  - **fastapi/config.py**: `FastApiConfig` 新增字段 `enable_context_middleware: bool = True`
  - **tests/test_fastapi/test_config.py**: 新增测试验证默认值为 True，可设为 False

  **Must NOT do**: 不改其他配置字段；不加 context 相关的业务逻辑（仅加开关字段）

  **Recommended Agent Profile**:
  - Category: `quick`（1 源文件加 1 字段 + 1 测试文件加 1-2 用例）
  - Skills: []

  **Parallelization**: Wave 1 parallel with T1, T2 | Blocks: T6 | Blocked By: None

  **References**:
  - `basic_tool/fastapi/config.py:49-73` - FastApiConfig 类定义，最后一行是 enable_error_handlers

  **QA Scenarios**:

  ```
  Scenario: 默认启用 context middleware
    Tool: Bash (python -c)
    Steps:
      1. config = FastApiConfig(title="test")
      2. 断言 config.enable_context_middleware == True
    Expected Result: True
    Evidence: .sisyphus/evidence/task-3-default-enabled.txt

  Scenario: 可禁用 context middleware
    Tool: Bash (python -c)
    Steps:
      1. config = FastApiConfig(title="test", enable_context_middleware=False)
      2. 断言 config.enable_context_middleware == False
    Expected Result: False
    Evidence: .sisyphus/evidence/task-3-disable.txt
  ```

  **Commit**: YES | Message: `feat(fastapi): add enable_context_middleware config flag` | Pre-commit: `pytest tests/test_fastapi/test_config.py -v`

---

- [x] 4. **RequestLoggingMiddleware 改造*（fastapi/middleware.py + tests/test_fastapi/test_middleware.py）

  **What to do**:
  - **fastapi/middleware.py**: RequestLoggingMiddleware 改为纯消费者:
    - 移除 `request_id = uuid.uuid4().hex`（不再自己生成 ID）
    - 移除 `request.state.request_id = request_id`
    - 导入 `from basic_tool.context.ctx import ctx`
    - 读取 trace_id: `trace_id = ctx.get("trace_id", "")`
    - 日志中 `request_id=` 改为 `trace_id={}`
    - 移除 `response.headers["X-Request-ID"] = request_id`（ContextMiddleware 负责 traceparent 响应头）
    - 保留: 访问日志功能（method, path, status, elapsed_ms）— 这是核心功能不可丢失
  - **tests/test_fastapi/test_middleware.py**:
    - `test_request_id_in_response`: 改为需要 ContextMiddleware 栈叠才能验证 traceparent 响应头
    - `test_request_id_unique_per_request`: 改为验证 trace_id 唯一性（需 ContextMiddleware）
    - AppError 测试保持不变（不依赖 request_id）
    - 新增: 测试 RequestLoggingMiddleware 从 context 读取 trace_id
    - 新增: 测试无 ContextMiddleware 时 trace_id 为空但不崩溃

  **Must NOT do**: 不删除访问日志功能；不生成任何 ID；不设置任何响应头

  **Recommended Agent Profile**:
  - Category: `unspecified-high`（需理解中间件栈叠顺序和 ContextVar 传播）
  - Skills: []

  **Parallelization**: Wave 2 parallel with T5 | Blocks: T6 | Blocked By: T1

  **References**:
  - `basic_tool/fastapi/middleware.py:19-54` - RequestLoggingMiddleware 当前实现（生成 ID + 访问日志 + 响应头）
  - `basic_tool/context/ctx.py:42-53` - ctx.get() API（读取 trace_id）
  - `tests/test_fastapi/test_middleware.py:30-61` - 当前 TestRequestLoggingMiddleware 测试

  **WHY References Matter**:
  - middleware.py 第 37 行 uuid4 生成要删除
  - 第 44-51 行访问日志要保留（仅改 request_id -> trace_id）
  - 第 53 行 X-Request-ID 响应头要删除
  - 测试需要栈叠 ContextMiddleware 才能验证完整流程

  **QA Scenarios**:

  ```
  Scenario: RequestLoggingMiddleware 从 context 读 trace_id
    Tool: Bash (TestClient + StringIO)
    Steps:
      1. 构造 app，先 add RequestLoggingMiddleware，再 add ContextMiddleware
      2. GET /test
      3. 用 StringIO 捕获 loguru 输出
      4. 断言输出包含 "trace_id=" 且值非空（32 hex 字符）
    Expected Result: 访问日志包含 trace_id
    Evidence: .sisyphus/evidence/task-4-log-with-trace-id.txt

  Scenario: 访问日志保留 method/path/status/elapsed
    Tool: Bash (TestClient + StringIO)
    Steps:
      1. 栈叠 ContextMiddleware + RequestLoggingMiddleware
      2. GET /test
      3. 断言日志包含 method=GET, path=/test, status=200, elapsed=, trace_id=
    Expected Result: 完整访问日志（5 个字段）
    Evidence: .sisyphus/evidence/task-4-access-log-complete.txt

  Scenario: 无 ContextMiddleware 时不崩溃
    Tool: Bash (TestClient)
    Steps:
      1. 仅注册 RequestLoggingMiddleware（不注册 ContextMiddleware）
      2. GET /test
      3. 断言 HTTP 200（不崩溃）
      4. 断言日志中 trace_id 为空或 None
    Expected Result: 正常工作，trace_id 缺失但不报错
    Evidence: .sisyphus/evidence/task-4-no-context.txt
  ```

  **Commit**: YES | Message: `refactor(fastapi): RequestLoggingMiddleware reads trace_id from context` | Pre-commit: `pytest tests/test_fastapi/test_middleware.py -v`

---

- [x] 5. **README 文档更新*（3 个 README 文件）

  **What to do**:
  - **basic_tool/context/README.md**:
    - 更新所有 `request_id` -> `trace_id` 的示例和说明
    - 更新 ContextMiddleware 说明: X-Request-Id -> traceparent（W3C）
    - 更新 _DEFAULT_HEADER_MAP 文档表
    - 新增 traceparent 重建逻辑说明
    - 更新代码示例
  - **basic_tool/errors/README.md**:
    - 更新 request_id -> trace_id 的说明（第 236 行附近）
    - 更新 log_error() 签名文档
  - **basic_tool/fastapi/README.md**:
    - 更新中间件栈说明: 新增 ContextMiddleware
    - 更新 X-Request-ID -> traceparent
    - 新增 enable_context_middleware 配置说明
    - 更新 create_app() 中间件链描述

  **Must NOT do**: 不改 id_generator README；不加与代码不符的 API 描述

  **Recommended Agent Profile**:
  - Category: `writing`（3 个文档文件，需准确反映代码改动）
  - Skills: []

  **Parallelization**: Wave 2 parallel with T4 | Blocks: None | Blocked By: T1, T2

  **References**:
  - `basic_tool/context/README.md` - 当前文档（多处 request_id/X-Request-Id）
  - `basic_tool/errors/README.md:236` - request_id 说明
  - `basic_tool/fastapi/README.md:187` - X-Request-ID 说明
  - T1 和 T2 的改动（通过读取改后的源文件获取最新 API）

  **QA Scenarios**:

  ```
  Scenario: README 无 request_id 残留
    Tool: Bash (grep)
    Steps:
      1. grep -rn "request_id" basic_tool/context/README.md basic_tool/errors/README.md basic_tool/fastapi/README.md
    Expected Result: 0 匹配（或仅在迁移说明历史上下文中提及）
    Evidence: .sisyphus/evidence/task-5-no-request-id.txt

  Scenario: README 包含 traceparent 说明
    Tool: Bash (grep)
    Steps:
      1. grep -l "traceparent" basic_tool/context/README.md basic_tool/fastapi/README.md
    Expected Result: 至少 2 个文件包含 traceparent
    Evidence: .sisyphus/evidence/task-5-traceparent-docs.txt
  ```

  **Commit**: YES | Message: `docs: update READMEs for W3C trace context migration` | Pre-commit: none

---

- [x] 6. **create_app 集成*（fastapi/app.py + tests/test_fastapi/test_app.py）

  **What to do**:
  - **fastapi/app.py**: create_app() 注册 ContextMiddleware:
    - 在中间件注册区域（CORS 之后、RequestLoggingMiddleware 之后）添加:
      ```python
      from basic_tool.context.middleware import ContextMiddleware, setup_context_middleware
      if config.enable_context_middleware:
          app.add_middleware(ContextMiddleware)
      ```
    - 关键: ContextMiddleware 必须最后添加（= 最外层 = 最先执行）
    - 中间件注册顺序: CORS(最先添加=最内层) -> RequestLoggingMiddleware -> ContextMiddleware(最后添加=最外层)
    - 这样 ContextMiddleware 最先执行（设置 context），RequestLoggingMiddleware 后执行（读取 context）
  - **tests/test_fastapi/test_app.py**:
    - `test_request_logging_enabled`(第175行): X-Request-ID -> traceparent 断言
    - `test_request_logging_disabled`(第189行): X-Request-ID -> traceparent 断言
    - 新增: test_context_middleware_enabled - 验证 create_app 默认注册 ContextMiddleware
    - 新增: test_context_middleware_disabled - 验证 enable_context_middleware=False 时不注册
    - 新增: test_full_stack_traceparent - 完整中间件栈验证 traceparent 端到端
    - 新增: test_error_has_trace_id - 触发异常验证日志含 trace_id

  **Must NOT do**: 不改 CORS/health/auth/routers/lifespan 逻辑；只加 ContextMiddleware 注册

  **Recommended Agent Profile**:
  - Category: `deep`（集成任务，需理解 Starlette 中间件栈顺序和全链路验证）
  - Skills: []

  **Parallelization**: Wave 3 alone | Blocks: F1-F4 | Blocked By: T1, T3, T4

  **References**:
  - `basic_tool/fastapi/app.py:131-211` - create_app() 函数，中间件注册在第 149-162 行
  - `basic_tool/fastapi/config.py:49-73` - FastApiConfig（T3 已添加 enable_context_middleware）
  - `basic_tool/context/middleware.py` - ContextMiddleware（T1 已改造为 W3C）
  - `tests/test_fastapi/test_app.py:172-201` - TestCreateAppMiddleware 现有测试

  **WHY References Matter**:
  - app.py 第 149-162 行是中间件注册区域，ContextMiddleware 要加在这里
  - Starlette 中间件顺序: 最后添加 = 最外层 = 最先执行（ContextMiddleware 需最先执行）
  - test_app.py 第 187/201 行的 X-Request-ID 断言需改为 traceparent

  **QA Scenarios**:

  ```
  Scenario: create_app 默认注册 ContextMiddleware
    Tool: Bash (TestClient)
    Steps:
      1. config = FastApiConfig(title="test")
      2. app = create_app(config)
      3. @app.get("/test") return {"trace_id": ctx.get("trace_id")}
      4. GET /test
      5. 断言 json()["trace_id"] 非 None（32 hex）
      6. 断言响应头有 traceparent
    Expected Result: ContextMiddleware 默认启用
    Evidence: .sisyphus/evidence/task-6-default-context.json

  Scenario: enable_context_middleware=False 时禁用
    Tool: Bash (TestClient)
    Steps:
      1. config = FastApiConfig(title="test", enable_context_middleware=False)
      2. app = create_app(config)
      3. @app.get("/test") return {"trace_id": ctx.get("trace_id")}
      4. GET /test
      5. 断言 json()["trace_id"] 为 None
      6. 断言响应头无 traceparent
    Expected Result: ContextMiddleware 禁用
    Evidence: .sisyphus/evidence/task-6-disabled.json

  Scenario: 完整中间件栈 traceparent 端到端
    Tool: Bash (TestClient)
    Steps:
      1. config = FastApiConfig(title="test")（默认启用所有中间件）
      2. app = create_app(config)
      3. GET /test with "traceparent: 00-abcdef0123456789abcdef0123456789-1111111111111111-01"
      4. 断言响应头 traceparent 以 "00-abcdef0123456789abcdef0123456789-" 开头（trace_id 保留）
      5. 断言 span_id 变化（!= 1111111111111111）
    Expected Result: traceparent 正确传播
    Evidence: .sisyphus/evidence/task-6-e2e-traceparent.json

  Scenario: 异常请求日志含 trace_id
    Tool: Bash (TestClient + StringIO)
    Steps:
      1. app = create_app(FastApiConfig(title="test"))
      2. @app.get("/error") raise RuntimeError("boom")
      3. client = TestClient(app, raise_server_exceptions=False)
      4. GET /error
      5. 用 StringIO 捕获日志
      6. 断言日志包含 "trace_id=" 且值非空
    Expected Result: 错误日志含 trace_id（证明 context 在异常处理器中可用）
    Evidence: .sisyphus/evidence/task-6-error-trace-id.txt

  Scenario: 全量测试通过
    Tool: Bash
    Steps:
      1. pytest tests/ -v
    Expected Result: 0 failures
    Evidence: .sisyphus/evidence/task-6-full-test-suite.txt
  ```

  **Commit**: YES | Message: `feat(fastapi): integrate ContextMiddleware into create_app` | Pre-commit: `pytest tests/ -v`


---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** (oracle) - APPROVE: Must Have [6/6] | Must NOT Have [10/10] | Definition of Done [8/8] | VERDICT: APPROVE

- [x] F2. **Code Quality Review** (unspecified-high) - APPROVE: Tests [480 pass/0 fail/1 skip] | All 16 changed files CLEAN | No AI slop | VERDICT: APPROVE

- [x] F3. **Real Manual QA** (unspecified-high) - APPROVE: Scenarios [15/15 pass] | T6.4 bug found (error log missing trace_id for unhandled exceptions), fixed by extracting trace_id from scope["basic_tool.traceparent"] in global_exception_handler | VERDICT: APPROVE (after fix)

- [x] F4. **Scope Fidelity Check** (deep) - APPROVE: Tasks [6/6 compliant] | id_generator untouched | Scope creep: NONE | 2 justified deviations (pure ASGI + scope traceparent for 500 responses) | VERDICT: APPROVE

---

## Commit Strategy

| Commit | After | Message | Key Files |
|--------|-------|---------|-----------|
| C1 | T1 | refactor(context): replace request_id with W3C trace_id | ctx.py, middleware.py, propagation.py, log_extra.py, test_ctx.py |
| C2 | T2 | refactor(errors): read trace_id from context | log.py, handler.py, test_log.py, test_handler.py |
| C3 | T3 | feat(fastapi): add enable_context_middleware config flag | config.py, test_config.py |
| C4 | T4 | refactor(fastapi): RequestLoggingMiddleware reads trace_id from context | middleware.py, test_middleware.py |
| C5 | T5 | docs: update READMEs for W3C trace context migration | 3 README files |
| C6 | T6 | feat(fastapi): integrate ContextMiddleware into create_app | app.py, test_app.py |

Pre-commit for ALL: pytest tests/ -v

---

## Success Criteria

### Verification Commands
```bash
pytest tests/ -v                    # Expected: all PASS
grep -r "request_id" basic_tool/ --include="*.py"  # Expected: 0 matches
git diff --name-only basic_tool/id_generator/      # Expected: empty
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] No request_id references in source code
- [x] id_generator/ 目录零改动
- [x] 3 个 README 全部更新
- [x] create_app() 默认注册 ContextMiddleware
