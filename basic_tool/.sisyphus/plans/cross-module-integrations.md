# 跨模块集成：16 项 SDK 能力打通

## TL;DR

> **Quick Summary**: 为 basic_tool SDK 添加 16 项跨模块集成，打通 trace 传播闭环、metrics 采集、错误体系统一、日志补全、异步邮件发送。所有集成遵循现有 SDK 模式（显式依赖注入、init/close 生命周期、结构化日志）。
>
> **Deliverables**:
> - HTTP 出站请求自动注入 trace headers（traceparent / X-Trace-Id）
> - 任务队列自动序列化/反序列化请求上下文
> - JWT 认证后自动注入 user_id 到上下文
> - 4 个模块可选接入 MetricsCollector 采集指标
> - RateLimitError / CryptoError 继承 AppError，统一错误响应
> - 邮件异步发送（@task 集成）
> - Storage / Redis 操作日志补全
> - create_app 自动启用日志上下文注入
> - Worker 检测 AppError 跳过重试
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: T1 → T12 → F1-F4

---

## Context

### Original Request
用户在学习 SDK 能力后，发现大量跨模块调用的空白（如 HTTP 出站请求不传播 trace、任务队列不继承上下文、RateLimitError 不是 AppError 导致返回 500 而非 429 等）。用户选择了 16 项集成（#1,2,3,4,5,6,7,9,10,12,14,15,16,17,18,19）要求生成实施方案。

### Interview Summary
**Key Discussions**:
- 全量代码审计：阅读了 SDK 全部 15 个子包的核心源码
- 识别了 12 条已有集成链路和 19 个可补充机会
- 用户排除了 #8（/metrics 端点）、#11（concurrency 异常统一）、#13（告警通知）

**Research Findings**:
- `context/propagation.py` 已有 `inject_headers_to_httpx()` / `serialize_context()` / `deserialize_context()`，专为 #1/#2 设计但从未被调用
- `context/log_extra.py` 已有 `enable_log_injection()`，专为 #19 设计
- `MetricsCollector` 有 counter/gauge/histogram 方法，可直接用于 #4/#5/#6/#7
- `AppError` 已有 code/message/http_status/context 字段，可直接继承

### Metis Review
**Identified Gaps** (addressed):
- **redis↔metrics 循环导入**（BLOCKING）：metrics/writer.py 已导入 redis.Cache，若 redis 再导入 metrics 会形成 2-cycle → 采用 **回调协议**：@cached 接受 `on_hit`/`on_miss` 回调，不导入 metrics
- **errors→metrics→redis→errors 3-cycle**（BLOCKING）：若 errors 导入 metrics 且 redis 异常继承 AppError → 采用 **回调协议**：log_error() 接受可选 `on_error` 回调
- **enable_log_injection() 非幂等**：重复调用会堆叠 patcher → 增加 `_enabled` 守卫
- **RateLimitError 构造函数变更**：现有调用方依赖 `.key`/`.max_requests`/`.window` 属性 → 保持向后兼容构造函数
- **CryptoError 构造函数变更**：现有代码 `raise CryptoError("msg")` → 保持单参数兼容
- **ARQ 序列化限制**：闭包无法被 ARQ 序列化 → email task 使用模块级函数 + worker ctx 注入 sender
- **测试目录约定**：tests/ 镜像 basic_tool/，但 fastapi 测试在 tests/test_fastapi/

---

## Work Objectives

### Core Objective
打通 SDK 各模块间的能力调用，实现 trace 全链路传播、metrics 自动采集、错误响应统一。

### Concrete Deliverables
- 15 个实现任务（#14 和 #15 合并为一个 task）
- 每个任务包含代码修改 + 测试 + README 更新

### Definition of Done
- [x] `pytest tests/ -v` 全部通过，0 failures
- [x] `python -c "import basic_tool.fastapi"` 无循环导入
- [x] 所有被修改的包的 README.md 已更新

### Must Have
- 所有 metrics 参数为 `Optional[MetricsCollector] = None`，None 时零开销
- 所有异常继承变更保持向后兼容构造函数
- 所有日志使用 `from loguru import logger`（与现有代码一致）
- 每个修改的 basic_tool 子包更新 README.md

### Must NOT Have (Guardrails)
- **禁止** redis/errors 模块级别导入 metrics（循环导入）
- **禁止** 修改 propagation.py / ctx.py / log_extra.py 的已有函数签名
- **禁止** 在 create_app() 中管理 MetricsCollector 生命周期（本次范围外）
- **禁止** 新增 metrics 指标类型（只用现有 counter/gauge/histogram）
- **禁止** 新增异常类型或改变 FastAPI 错误响应格式
- **禁止** 使用 TYPE_CHECKING（代码库中无此先例）
- **禁止** 在测试中使用真实 Redis/SMTP/ARQ

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: Tests-after（每个 task 的实现 + 测试在同一个 task 中）
- **Framework**: pytest (asyncio_mode=auto)
- **Test location**: `/home/lizy/projects/LzyProjs/tests/`

### QA Policy
- **循环导入验证**: 每个 Wave 结束后 `python -c "import basic_tool.<module>"`
- **向后兼容验证**: 现有测试不修改即通过
- **No-op 验证**: metrics=None 时行为与修改前完全一致
- **Mock 策略**: fakeredis (Redis), httpx.MockTransport (HTTP), AsyncMock (SMTP/ARQ), tmp_path (filesystem)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - 6 parallel, no file conflicts):
├── T1:  #19 enable_log_injection 幂等守卫 + create_app 接入 [quick]
├── T2:  #9 RateLimitError → AppError（向后兼容） [quick]
├── T3:  #10 CryptoError 系 → AppError（向后兼容） [quick]
├── T4:  #3 auth 认证后注入 user_id 到 context [quick]
├── T5:  #18 concurrency 上下文继承文档化 [quick]
└── T6:  #17 task_queue AppError 跳过重试 [quick]

Wave 2 (Context & Logging - 5 parallel, after Wave 1):
├── T7:  #1 http_client 出站请求 trace 传播 [quick]
├── T8:  #2 task_queue 上下文序列化/反序列化 [quick]
├── T9:  #14+#15 storage 操作日志 + trace 关联 [quick]
├── T10: #16 redis 生命周期日志 [quick]
└── T11: #12 email 异步发送（@task 集成） [unspecified-low]

Wave 3 (Metrics Integration - 4 parallel, after Wave 2):
├── T12: #4 middleware 请求指标采集（直接注入） [unspecified-high]
├── T13: #5 errors 错误计数（回调协议避免循环） [quick]
├── T14: #6 redis @cached 缓存命中率（回调协议避免循环） [unspecified-high]
└── T15: #7 http_client 出站请求指标（直接注入） [unspecified-high]

Wave FINAL (4 parallel reviews, after ALL):
├── F1: Plan Compliance Audit (oracle)
├── F2: Code Quality Review (unspecified-high)
├── F3: Real Manual QA (unspecified-high)
└── F4: Scope Fidelity Check (deep)

Critical Path: T1 → T12 → F1-F4
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 6 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Files Touched |
|------|-----------|--------|---------------|
| T1 | - | T12 | context/log_extra.py, fastapi/app.py |
| T2 | - | T14 | redis/decorators.py, redis/README.md |
| T3 | - | - | crypto/exceptions.py, crypto/README.md |
| T4 | - | - | fastapi/auth.py |
| T5 | - | - | concurrency/*.py docstrings, concurrency/README.md |
| T6 | - | T8 | task_queue/worker.py |
| T7 | - | T15 | http_client/client.py, http_client/config.py |
| T8 | T6 | - | task_queue/queue.py, task_queue/worker.py |
| T9 | - | - | storage/storage.py, storage/local.py |
| T10 | - | T14 | redis/client/__init__.py |
| T11 | - | - | email/task.py (new), email/__init__.py |
| T12 | T1 | F1-F4 | fastapi/middleware.py, fastapi/config.py, fastapi/app.py |
| T13 | - | - | errors/log.py, errors/handler.py |
| T14 | T2,T10 | - | redis/decorators.py |
| T15 | T7 | - | http_client/client.py, http_client/config.py |

### Agent Dispatch Summary

- **Wave 1**: 6 × `quick`
- **Wave 2**: 4 × `quick` + 1 × `unspecified-low`
- **Wave 3**: 2 × `unspecified-high` + 1 × `quick` + 1 × `unspecified-high`
- **FINAL**: 1 × `oracle` + 2 × `unspecified-high` + 1 × `deep`

---

## TODOs

- [x] 1. **#19 enable_log_injection 幂等守卫 + create_app 自动接入**

  **What to do**:
  - 在 `context/log_extra.py` 中增加模块级 `_log_injection_enabled = False` 守卫变量
  - 修改 `enable_log_injection()`：函数入口检查 `if _log_injection_enabled: return`，成功后设为 True
  - 在 `fastapi/app.py` 的 `create_app()` 中，`setup_logger(config.log)` 调用之后（约 app.py:134 后），增加 `from basic_tool.context.log_extra import enable_log_injection; enable_log_injection()`
  - 条件：仅在 `config.log is not None`（即用户配置了日志）时调用
  - 更新 `context/README.md` 和 `fastapi/README.md`

  **Must NOT do**:
  - 不修改 `_inject_context()` 函数本身的逻辑
  - 不在 `config.log is None` 时调用 enable_log_injection（保持不配置日志时的默认行为）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3, T4, T5, T6)
  - **Blocks**: T12
  - **Blocked By**: None

  **References**:
  - `basic_tool/context/log_extra.py:51-70` — `enable_log_injection()` 函数，需增加幂等守卫。注意第 69 行 `loguru.logger.patch()` 每次调用返回新实例并复制 `_options`
  - `basic_tool/fastapi/app.py:132-134` — `create_app()` 中日志配置位置，在此之后插入 enable_log_injection 调用
  - `basic_tool/context/ctx.py:35-39` — ContextManager 和 request_context 使用 ContextVar，enable_log_injection 使其自动注入日志 extra

  **Acceptance Criteria**:
  - [ ] `enable_log_injection()` 调用两次不堆叠 patcher
  - [ ] `create_app()` 配置了 `config.log` 后所有日志自动携带 trace_id

  **QA Scenarios**:
  ```
  Scenario: 幂等性验证 — 连续调用不堆叠 patcher
    Tool: Bash (python)
    Preconditions: 无活跃 loguru 配置
    Steps:
      1. python -c "from basic_tool.context.log_extra import enable_log_injection; enable_log_injection(); enable_log_injection(); print('OK')"
    Expected Result: 输出 "OK"，无异常
    Evidence: .sisyphus/evidence/task-1-idempotency.txt

  Scenario: create_app 自动注入 — 日志自动携带 trace_id
    Tool: Bash (python pytest)
    Preconditions: fakeredis 可用
    Steps:
      1. 创建 FastApiConfig(log=LogConfig(level="DEBUG"))
      2. 调用 create_app(config)
      3. 使用 TestClient 发送 GET /health 请求
      4. 捕获 stderr 日志输出，检查是否包含 trace_id 字段
    Expected Result: 日志行包含 trace_id= 开头的字段
    Evidence: .sisyphus/evidence/task-1-log-injection.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(context): add idempotency guard to enable_log_injection and auto-enable in create_app`
  - Files: `context/log_extra.py`, `fastapi/app.py`, `context/README.md`, `fastapi/README.md`
  - Pre-commit: `pytest tests/context/ tests/test_fastapi/ -v`

---

- [x] 2. **#9 RateLimitError 继承 AppError（向后兼容）**

  **What to do**:
  - 修改 `redis/decorators.py` 中 `RateLimitError` 类定义：
    - 改为继承 `AppError` 而非 `Exception`
    - 保持现有构造函数签名 `(key, count, max_requests, window)` 完全不变
    - 在 `__init__` 内部调用 `super().__init__(code="RATE_LIMITED", message=..., http_status=429, context={...})`
    - 保留 `.key`, `.count`, `.max_requests`, `.window` 属性赋值
  - 在文件顶部增加 `from basic_tool.errors import AppError` 导入
  - 更新 `redis/README.md` 说明 RateLimitError 现在是 AppError 子类，FastAPI 会自动返回 429
  - 新增/更新测试验证：RateLimitError 既是 AppError 又保留原有属性

  **Must NOT do**:
  - 不改变构造函数的参数名和顺序
  - 不修改 `rate_limit()` 装饰器中 raise RateLimitError 的调用方式
  - 不改变异常消息格式 "请求频率超限 | key=..."

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3, T4, T5, T6)
  - **Blocks**: T14
  - **Blocked By**: None

  **References**:
  - `basic_tool/redis/decorators.py:42-53` — RateLimitError 当前定义，构造函数 `(key, count, max_requests, window)`，消息格式 "请求频率超限 | key={key} count={count} max={max_requests} window={window}s"
  - `basic_tool/errors/app_error.py:10-39` — AppError 基类，构造函数 `(code, message, http_status=400, context=None)`，有 `.code`/`.message`/`.http_status`/`.context` 属性
  - `tests/redis/test_decorators.py:91-135` — 现有 RateLimitError 测试，检查 `.key`/`.max_requests`/`.window` 属性和 match="请求频率超限" 消息
  - `basic_tool/redis/__init__.py:12,25` — RateLimitError 导出位置

  **Acceptance Criteria**:
  - [ ] `isinstance(RateLimitError(...), AppError)` 为 True
  - [ ] `RateLimitError(key="x", count=5, max_requests=3, window=60).http_status == 429`
  - [ ] 现有 `tests/redis/test_decorators.py` 全部通过（不修改测试代码）
  - [ ] FastAPI 全局异常处理器捕获 RateLimitError 返回 429（而非 500）

  **QA Scenarios**:
  ```
  Scenario: 向后兼容 — 现有测试不改即通过
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/redis/test_decorators.py -v
    Expected Result: 全部 PASS，0 failures
    Evidence: .sisyphus/evidence/task-2-backward-compat.txt

  Scenario: AppError 继承验证
    Tool: Bash (python)
    Steps:
      1. python -c "from basic_tool.redis.decorators import RateLimitError; from basic_tool.errors import AppError; e = RateLimitError(key='x', count=5, max_requests=3, window=60); assert isinstance(e, AppError); assert e.http_status == 429; assert e.code == 'RATE_LIMITED'; assert e.key == 'x'; print('OK')"
    Expected Result: 输出 "OK"
    Evidence: .sisyphus/evidence/task-2-apperror-inheritance.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(redis): RateLimitError inherits AppError with http_status=429`
  - Files: `redis/decorators.py`, `redis/README.md`, `tests/redis/test_decorators.py`
  - Pre-commit: `pytest tests/redis/test_decorators.py -v`

---

- [x] 3. **#10 CryptoError 系继承 AppError（向后兼容）**

  **What to do**:
  - 修改 `crypto/exceptions.py`：
    - `CryptoError` 改为继承 `AppError`，保持 `__init__(self, message: str)` 签名
    - 内部调用 `super().__init__(code="CRYPTO_ERROR", message=message, http_status=500)`
    - `DecryptionError` 继续继承 `CryptoError`，`__init__(self, message: str)` 调用 `super().__init__(message)` 并覆盖 code 为 `"DECRYPTION_ERROR"`、http_status 为 `400`
    - `InvalidKeyError` 同理，code=`"INVALID_KEY"`、http_status=`400`
    - `SignatureVerificationError` 同理，code=`"SIGNATURE_VERIFICATION_FAILED"`、http_status=`403`
  - 在文件顶部增加 `from basic_tool.errors import AppError`
  - 更新 `crypto/README.md`
  - 新增测试 `tests/crypto/test_exceptions.py` 验证继承关系和属性

  **Must NOT do**:
  - 不改变任何 raise 语句的调用方式（现有代码 `raise DecryptionError(f"...")` 必须继续工作）
  - 不增加新的异常类型
  - 不修改 `crypto/encrypt.py` / `crypto/password.py` / `crypto/sign.py`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T4, T5, T6)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/crypto/exceptions.py:1-22` — 当前异常定义，全部继承 `Exception`，无自定义 `__init__`
  - `basic_tool/errors/app_error.py:10-39` — AppError 基类定义
  - `basic_tool/crypto/encrypt.py:27,35,86` — 现有 raise 语句：`raise InvalidKeyError("fernet_key is empty")`, `raise DecryptionError(f"decryption failed: {e}")`
  - `tests/crypto/test_encrypt.py:38-77` — 现有测试使用 `pytest.raises(DecryptionError)` 和 `pytest.raises(InvalidKeyError)`

  **Acceptance Criteria**:
  - [ ] `isinstance(CryptoError("msg"), AppError)` 为 True
  - [ ] `DecryptionError("msg").code == "DECRYPTION_ERROR"`
  - [ ] 现有 `tests/crypto/` 全部通过（不修改测试代码）

  **QA Scenarios**:
  ```
  Scenario: 向后兼容 — 现有 crypto 测试不改即通过
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/crypto/ -v
    Expected Result: 全部 PASS
    Evidence: .sisyphus/evidence/task-3-backward-compat.txt

  Scenario: AppError 继承和属性验证
    Tool: Bash (python)
    Steps:
      1. python -c "from basic_tool.crypto.exceptions import CryptoError, DecryptionError, InvalidKeyError; from basic_tool.errors import AppError; e = DecryptionError('test'); assert isinstance(e, AppError); assert e.code == 'DECRYPTION_ERROR'; assert e.http_status == 400; print('OK')"
    Expected Result: "OK"
    Evidence: .sisyphus/evidence/task-3-apperror-inheritance.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(crypto): crypto exceptions inherit AppError for unified error handling`
  - Files: `crypto/exceptions.py`, `crypto/README.md`, `tests/crypto/test_exceptions.py`
  - Pre-commit: `pytest tests/crypto/ -v`

---

- [x] 4. **#3 JWT 认证后注入 user_id 到请求上下文**

  **What to do**:
  - 在 `fastapi/auth.py` 的 `JWTAuth.get_current_user()` 方法中，成功验证用户后增加 `ctx.set("user_id", user_id)`
  - 在文件顶部增加 `from basic_tool.context.ctx import ctx`
  - 注入位置：在 `user = await self._user_loader(user_id)` 成功返回之前（约 auth.py:130 之前）
  - 更新 `fastapi/README.md` 说明认证后 user_id 自动注入上下文

  **Must NOT do**:
  - 不修改 `ApiKeyAuth` 类（API Key 场景的 user_id 由业务层决定）
  - 不在认证失败时设置上下文
  - 不修改 `get_current_user` 的返回值或签名

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T3, T5, T6)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/fastapi/auth.py:94-132` — `get_current_user()` 方法，第 129 行 `user = await self._user_loader(user_id)` 是注入点
  - `basic_tool/context/ctx.py:42-70` — ContextManager 类，`ctx.set(key, value)` 原地修改当前上下文字典
  - `basic_tool/context/log_extra.py` — enable_log_injection 使 ctx 字段自动注入日志 extra，所以 user_id 设置后所有日志自动携带

  **Acceptance Criteria**:
  - [ ] JWT 认证成功后 `ctx.get("user_id")` 返回 token 中的 sub 值
  - [ ] 认证失败时 `ctx.get("user_id")` 为 None

  **QA Scenarios**:
  ```
  Scenario: JWT 认证后上下文包含 user_id
    Tool: Bash (pytest)
    Preconditions: 创建 JWTAuth 实例，mock user_loader 返回非 None
    Steps:
      1. 在 request_context 中调用 get_current_user
      2. 验证 ctx.get("user_id") == token 中的 sub 值
    Expected Result: user_id 正确设置
    Evidence: .sisyphus/evidence/task-4-auth-context.txt

  Scenario: 认证失败时不设置 user_id
    Tool: Bash (pytest)
    Preconditions: mock user_loader 返回 None
    Steps:
      1. 调用 get_current_user，期望抛出 HTTPException 401
      2. 验证 ctx 中无 user_id
    Expected Result: 401 异常，上下文无 user_id
    Evidence: .sisyphus/evidence/task-4-auth-fail.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(fastapi): inject user_id into request context after JWT authentication`
  - Files: `fastapi/auth.py`, `fastapi/README.md`, `tests/test_fastapi/test_auth.py`
  - Pre-commit: `pytest tests/test_fastapi/test_auth.py -v`

---

- [x] 5. **#18 concurrency 上下文继承文档化**

  **What to do**:
  - 在 `concurrency/pool.py` 的 `ConcurrencyPool` 类 docstring 中增加说明：所有通过 `run()` / `gather()` 执行的协程会自动继承当前 ContextVar 快照（Python 3.11+ asyncio 行为）
  - 在 `concurrency/batch.py` 的 `gather_with_limit()` / `gather_with_retry()` docstring 中增加类似说明
  - 在 `concurrency/task_group.py` 的 `TaskGroup` 类 docstring 中增加说明
  - 在 `concurrency/__init__.py` 模块 docstring 中增加"上下文传播"说明段落
  - 更新 `concurrency/README.md` 增加"请求上下文自动传播"章节

  **Must NOT do**:
  - 不修改任何函数的逻辑代码
  - 不增加新的代码行（仅 docstring 修改）
  - 不增加测试（纯文档变更）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T3, T4, T6)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/concurrency/pool.py:60-84` — `ConcurrencyPool.run()` 方法，协程在 semaphore 内 await
  - `basic_tool/concurrency/batch.py:48-75` — `run_one()` 内部协程执行
  - `basic_tool/concurrency/task_group.py:24-43` — TaskGroup 包装 asyncio.TaskGroup
  - Python 文档：asyncio.Task 和 TaskGroup 创建时自动复制当前 ContextVar 快照

  **Acceptance Criteria**:
  - [ ] ConcurrencyPool docstring 包含 "ContextVar" 或 "上下文" 说明
  - [ ] README.md 包含"请求上下文自动传播"章节

  **QA Scenarios**:
  ```
  Scenario: 文档完整性验证
    Tool: Bash (grep)
    Steps:
      1. grep -l "ContextVar\|上下文" basic_tool/concurrency/*.py
      2. grep -l "上下文\|context" basic_tool/concurrency/README.md
    Expected Result: pool.py, batch.py, task_group.py, __init__.py, README.md 全部匹配
    Evidence: .sisyphus/evidence/task-5-docs.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `docs(concurrency): document ContextVar inheritance in concurrent task execution`
  - Files: `concurrency/pool.py`, `concurrency/batch.py`, `concurrency/task_group.py`, `concurrency/__init__.py`, `concurrency/README.md`
  - Pre-commit: `pytest tests/concurrency/ -v`

---

- [x] 6. **#17 task_queue Worker 检测 AppError 跳过重试**

  **What to do**:
  - 在 `task_queue/worker.py` 的 `_wrap_function()` 中（约第 90-114 行），修改 wrapper 函数：
    - 捕获异常后检查 `isinstance(exc, AppError)`
    - 如果是 AppError，设置 `wrapper.coroutine = ...` 或使用 ARQ 的 `JobRetry` 机制标记不重试
    - 具体实现：在 wrapper 中 try/except，捕获 AppError 时 raise `arq.Retry` 的反面 — 即直接 raise 让 ARQ 视为不可重试的异常
    - ARQ 行为：非 `Exception` 子类（如 `BaseException`）不触发重试；但 AppError 是 Exception 子类。需要查阅 ARQ 文档确认：ARQ 对 `max_tries` 的处理是全局的，per-job 的重试控制需要通过 wrapper 内部逻辑实现
    - **最终方案**：在 wrapper 中 catch AppError，记录 WARNING 日志后直接返回（不 re-raise），让 ARQ 认为任务成功完成（但结果为 None 或错误标记 dict）。或者 catch AppError 后 raise 一个非 Exception 的标记异常（不推荐改变异常体系）
    - **推荐方案**：catch AppError，log warning，返回 `{"_error": True, "code": exc.code, "message": exc.message}` 作为任务结果。业务方检查返回值。
  - 在文件顶部增加 `from basic_tool.errors import AppError`（deferred import 在函数内部也可）
  - 更新 `task_queue/README.md` 说明 AppError 被视为业务错误不触发重试
  - 新增测试

  **Must NOT do**:
  - 不修改 `build_settings()` 的签名
  - 不修改非 AppError 异常的重试行为（网络错误等仍然重试）
  - 不改变 ARQ 的 `max_tries` 全局配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T3, T4, T5)
  - **Blocks**: T8
  - **Blocked By**: None

  **References**:
  - `basic_tool/task_queue/worker.py:90-114` — `_wrap_function()` 函数，当前只设置 `max_tries` 和 `job_timeout` 属性，wrapper 直接 `await func(*args, **kwargs)`
  - `basic_tool/errors/app_error.py:10-39` — AppError 定义
  - ARQ 文档：`max_tries` 控制重试次数，异常类型不影响是否重试（所有 Exception 子类都会重试直到 max_tries 耗尽）

  **Acceptance Criteria**:
  - [ ] 任务函数抛出 AppError 时，Worker 不重试（或只执行一次）
  - [ ] 任务函数抛出非 AppError（如 ConnectionError）时，行为不变（按 max_tries 重试）
  - [ ] AppError 的 code 和 message 被记录到日志

  **QA Scenarios**:
  ```
  Scenario: AppError 不触发重试
    Tool: Bash (pytest)
    Preconditions: 注册一个会 raise AppError 的 @task，设置 max_tries=3
    Steps:
      1. 执行 wrapper，验证函数只被调用 1 次（而非 3 次）
      2. 验证日志包含 AppError 的 code 和 message
    Expected Result: 函数调用 1 次，不重试
    Evidence: .sisyphus/evidence/task-6-apperror-no-retry.txt

  Scenario: 非 AppError 正常重试
    Tool: Bash (pytest)
    Preconditions: 注册一个会 raise ConnectionError 的 @task，max_tries=3
    Steps:
      1. 执行 wrapper，验证函数被调用 3 次
    Expected Result: 函数调用 3 次（重试行为不变）
    Evidence: .sisyphus/evidence/task-6-normal-retry.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(task_queue): skip retry for AppError business exceptions`
  - Files: `task_queue/worker.py`, `task_queue/README.md`, `tests/task_queue/test_worker.py`
  - Pre-commit: `pytest tests/task_queue/ -v`

- [x] 7. **#1 http_client 出站请求自动注入 trace headers**

  **What to do**:
  - 在 `http_client/config.py` 的 `HttpConfig` 中增加字段 `propagate_context: bool = True`
  - 在 `http_client/client.py` 的 `_build_event_hooks()` 中，当 `self._config.propagate_context` 为 True 时：
    - 在 `on_request` 钩子中调用 `from basic_tool.context.propagation import inject_headers_to_httpx`
    - 将返回的传播 headers 合并到 `request.headers` 中（不覆盖用户已设置的头）
    - 具体实现：`for k, v in inject_headers_to_httpx().items(): if k not in request.headers: request.headers[k] = v`
  - 在 `on_request` 钩子的日志中增加 `trace_id` 字段（从 `ctx.get("trace_id")` 读取）
  - 更新 `http_client/README.md` 说明出站请求自动携带 trace headers
  - 新增测试验证 headers 注入

  **Must NOT do**:
  - 不修改 `context/propagation.py` 的任何函数
  - 不覆盖用户显式设置的请求头
  - 不在无活跃上下文时注入空 headers（inject_headers_to_httpx 返回 {} 时跳过）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T8, T9, T10, T11)
  - **Blocks**: T15
  - **Blocked By**: None

  **References**:
  - `basic_tool/http_client/client.py:151-190` — `_build_event_hooks()` 方法，`on_request` 钩子在约 160 行
  - `basic_tool/http_client/config.py` — HttpConfig 类定义，需增加 `propagate_context` 字段
  - `basic_tool/context/propagation.py:75-93` — `inject_headers_to_httpx(headers)` 函数，返回合并后的 headers dict（上下文头 + 用户头，用户优先）
  - `basic_tool/context/propagation.py:36-72` — `get_propagation_headers()` 从 ContextVar 提取 trace_id/span_id/user_id 等并转为 HTTP 头名

  **Acceptance Criteria**:
  - [ ] `propagate_context=True` 时，出站请求包含 X-Trace-Id 头（当上下文中有 trace_id 时）
  - [ ] `propagate_context=False` 时，出站请求不包含任何额外 headers
  - [ ] 用户显式设置的请求头不被覆盖

  **QA Scenarios**:
  ```
  Scenario: 出站请求自动携带 trace headers
    Tool: Bash (pytest)
    Preconditions: 在 request_context(trace_id="abc123") 中使用 HttpClient
    Steps:
      1. 使用 httpx.MockTransport 捕获请求 headers
      2. 在 request_context 中发送 GET 请求
      3. 验证捕获的 headers 包含 X-Trace-Id: abc123
    Expected Result: headers["x-trace-id"] == "abc123"
    Evidence: .sisyphus/evidence/task-7-trace-propagation.txt

  Scenario: 无上下文时不注入 headers
    Tool: Bash (pytest)
    Preconditions: 不在 request_context 中
    Steps:
      1. 发送 GET 请求
      2. 验证 headers 中不包含 X-Trace-Id
    Expected Result: 无 X-Trace-Id 头
    Evidence: .sisyphus/evidence/task-7-no-context.txt

  Scenario: propagate_context=False 禁用传播
    Tool: Bash (pytest)
    Preconditions: HttpConfig(propagate_context=False)
    Steps:
      1. 在 request_context 中发送 GET 请求
      2. 验证 headers 中不包含 X-Trace-Id
    Expected Result: 无 X-Trace-Id 头
    Evidence: .sisyphus/evidence/task-7-disabled.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(http_client): auto-inject trace headers into outbound requests`
  - Files: `http_client/client.py`, `http_client/config.py`, `http_client/README.md`, `tests/http_client/test_client.py`
  - Pre-commit: `pytest tests/http_client/ -v`

---

- [x] 8. **#2 task_queue 上下文序列化/反序列化传播**

  **What to do**:
  - 在 `task_queue/queue.py` 的 `enqueue()` 方法中：
    - 增加 `from basic_tool.context.propagation import serialize_context`
    - 在调用 `self.client.enqueue_job()` 之前，调用 `serialize_context()` 获取当前上下文快照
    - 将上下文快照通过 ARQ 的 `_job_id` 同级参数传递（ARQ 的 `enqueue_job` 支持 `_job_try` 等元数据，检查是否支持自定义元数据）
    - ARQ `enqueue_job` 签名：检查是否可通过 `_job_id` 或额外参数传递元数据。如果 ARQ 不支持自定义元数据，则将上下文作为任务的第一个参数传递（在 ctx 之后）
    - **推荐方案**：将序列化的上下文 dict 作为任务函数的最后一个位置参数追加。但这会改变函数签名。更好的方案：使用 ARQ 的 `_job_id` 参数编码上下文（不推荐，长度限制）
    - **最终方案**：将上下文 dict 作为 ARQ job 的 `_job_try` 同级的自定义字段。查阅 ARQ `enqueue_job` 源码：`enqueue_job(function, *args, _job_id=None, _defer_by=None, _defer_until=None, _expires=None, **kwargs)`。ARQ 将 args 序列化存储。在 args 中追加一个 `_context` dict 参数，worker 的 on_job_start 从 ctx 中提取。
    - 实际上 ARQ 的 enqueue_job 将 *args 直接作为 Redis hash field 存储，worker 调用时传递给函数。所以可以将序列化的上下文作为 kwargs 传递，worker 在 on_job_start 中不处理（由 wrapper 处理）。
    - **最简方案**：在 enqueue 时，将 `serialize_context()` 结果存入 `_job_id` 的伴随数据中。ARQ 不直接支持，但可以将上下文作为函数的最后一个参数追加，并在 worker 的 _wrap_function 中提取并恢复上下文。
  - 在 `task_queue/worker.py` 的 `_wrap_function()` 中（T6 修改后的版本）：
    - 在执行 `await func(*args, **kwargs)` 之前，检查 args 中是否包含上下文 dict（按约定位置或键名）
    - 如果包含，调用 `deserialize_context(context_data)` 恢复上下文，用 `async with` 包裹任务执行
  - 更新 `task_queue/README.md` 说明上下文自动传播
  - 新增测试

  **Must NOT do**:
  - 不修改 `context/propagation.py` 的 `serialize_context()` / `deserialize_context()` 函数
  - 不改变 ARQ 的 `enqueue_job` 调用签名（仅追加参数）
  - 不在无活跃上下文时强制创建上下文

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T7, T9, T10, T11)
  - **Blocks**: None
  - **Blocked By**: T6（worker.py 被 T6 修改）

  **References**:
  - `basic_tool/task_queue/queue.py:91-135` — `enqueue()` 方法，第 120 行调用 `self.client.enqueue_job()`
  - `basic_tool/task_queue/worker.py:90-114` — `_wrap_function()` 函数，需在此恢复上下文
  - `basic_tool/context/propagation.py:96-122` — `serialize_context()` 返回 dict 副本，`deserialize_context(data)` 返回 `_RequestContext` 上下文管理器
  - ARQ `enqueue_job` 签名：支持 `*args` 和 `**kwargs` 传递给任务函数

  **Acceptance Criteria**:
  - [ ] `enqueue()` 时当前上下文被序列化并随任务传递
  - [ ] Worker 执行任务时上下文被恢复，`ctx.get("trace_id")` 返回入队时的值
  - [ ] 无活跃上下文时 `enqueue()` 不报错（serialize_context 返回 {}）

  **QA Scenarios**:
  ```
  Scenario: 上下文跨任务传播
    Tool: Bash (pytest)
    Preconditions: 在 request_context(trace_id="job-trace-123") 中 enqueue 任务
    Steps:
      1. 任务函数内读取 ctx.get("trace_id")
      2. 验证值 == "job-trace-123"
    Expected Result: trace_id 正确传播
    Evidence: .sisyphus/evidence/task-8-context-propagation.txt

  Scenario: 无上下文时不报错
    Tool: Bash (pytest)
    Preconditions: 不在 request_context 中 enqueue
    Steps:
      1. enqueue 任务，任务函数内 ctx.get("trace_id") 返回 None
    Expected Result: 任务正常执行，trace_id 为 None
    Evidence: .sisyphus/evidence/task-8-no-context.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(task_queue): propagate request context through job serialization`
  - Files: `task_queue/queue.py`, `task_queue/worker.py`, `task_queue/README.md`, `tests/task_queue/test_queue.py`
  - Pre-commit: `pytest tests/task_queue/ -v`

---

- [x] 9. **#14+#15 storage 操作日志 + trace 关联**

  **What to do**:
  - 在 `storage/storage.py` 的 `Storage` 门面类中：
    - `put()`: 增加 `logger.info("storage put | key={} size={} content_type={}", key, len(data), content_type)`
    - `get()`: 增加 `logger.debug("storage get | key={}", key)`
    - `delete()`: 增加 `logger.info("storage delete | key={}", key)`
    - `exists()`: 增加 `logger.debug("storage exists | key={} exists={}", key, result)`
    - `list()`: 增加 `logger.info("storage list | prefix={} count={}", prefix, len(result))`
  - 在 `storage/local.py` 的 `LocalBackend` 中：
    - `init()`: 增加 `logger.info("LocalBackend 初始化 | base_dir={}", self._config.base_dir)`
    - `close()`: 无需日志（无资源释放）
  - trace 关联：当 T1 的 enable_log_injection 在 create_app 中启用后，所有 storage 日志自动携带 trace_id。此处只需确保使用 `from loguru import logger`。
  - 在文件顶部增加 `from loguru import logger`
  - 更新 `storage/README.md`

  **Must NOT do**:
  - 不在 `LocalBackend` 的每次文件读写中加日志（只在 Storage 门面层加）
  - 不记录文件内容
  - 不增加日志级别配置
  - 不增加审计追踪功能

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T7, T8, T10, T11)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/storage/storage.py:65-149` — Storage 门面类的所有方法，当前无任何日志
  - `basic_tool/storage/local.py` — LocalBackend 实现，需查看 init() 方法
  - `basic_tool/logger/logger.py` — SDK 日志格式，使用 loguru logger 即可自动应用

  **Acceptance Criteria**:
  - [ ] `put()` 操作后 stderr 包含 "storage put" 日志
  - [ ] `delete()` 操作后 stderr 包含 "storage delete" 日志
  - [ ] 日志格式遵循 SDK 的 `level||file:line||key=value||message` 格式

  **QA Scenarios**:
  ```
  Scenario: 存储操作日志验证
    Tool: Bash (pytest)
    Preconditions: 使用 tmp_path 创建 LocalBackend
    Steps:
      1. capsys 捕获 stderr
      2. 调用 storage.put("test.txt", b"hello")
      3. 检查 stderr 包含 "storage put" 和 key=test.txt
    Expected Result: 日志包含操作信息和 key
    Evidence: .sisyphus/evidence/task-9-storage-logging.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(storage): add structured logging to storage operations`
  - Files: `storage/storage.py`, `storage/local.py`, `storage/README.md`, `tests/storage/test_storage.py`
  - Pre-commit: `pytest tests/storage/ -v`

---

- [x] 10. **#16 redis Cache 生命周期日志**

  **What to do**:
  - 在 `redis/client/__init__.py` 的 `Cache` 类中：
    - `init()`: 增加 `logger.info("Cache 初始化 | redis_url={} max_connections={}", self._config.url, self._config.max_connections)`
    - `close()`: 增加 `logger.info("Cache 已关闭")`
    - 连接池创建处：增加 `logger.debug("Redis 连接池已创建")`
  - 在文件顶部确认 `from loguru import logger` 已存在（如果不存在则增加）
  - 更新 `redis/README.md`

  **Must NOT do**:
  - 不在每个 Redis 命令（get/set 等）中加日志
  - 不增加连接池监控功能
  - 不修改 Cache 的任何方法逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T7, T8, T9, T11)
  - **Blocks**: T14
  - **Blocked By**: None

  **References**:
  - `basic_tool/redis/client/__init__.py` — Cache 类定义和 init()/close() 方法
  - `basic_tool/redis/health.py:18` — 已有 `from loguru import logger` 先例
  - `basic_tool/redis/locks.py:35` — 已有 `from loguru import logger` 先例

  **Acceptance Criteria**:
  - [ ] `cache.init()` 后日志包含 "Cache 初始化"
  - [ ] `cache.close()` 后日志包含 "Cache 已关闭"

  **QA Scenarios**:
  ```
  Scenario: Cache 生命周期日志
    Tool: Bash (pytest)
    Preconditions: fakeredis 可用（shared cache fixture）
    Steps:
      1. capsys 捕获 stderr
      2. await cache.init()
      3. 检查 stderr 包含 "Cache 初始化"
      4. await cache.close()
      5. 检查 stderr 包含 "Cache 已关闭"
    Expected Result: init 和 close 日志正确输出
    Evidence: .sisyphus/evidence/task-10-cache-lifecycle.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(redis): add lifecycle logging to Cache init/close`
  - Files: `redis/client/__init__.py`, `redis/README.md`, `tests/redis/test_client.py`
  - Pre-commit: `pytest tests/redis/test_client.py -v`

---

- [x] 11. **#12 email 异步发送（@task 集成）**

  **What to do**:
  - 新建 `email/task.py`：
    - 定义模块级 `@task` 函数 `send_email_task(ctx, to: list[str], subject: str, body: str, content_type: str = "text/plain", cc: list[str] | None = None, bcc: list[str] | None = None)`
    - 函数内部从 `ctx` 中获取 EmailSender 实例：`sender = ctx.get("email_sender")`，如果为 None 则 raise RuntimeError
    - 调用 `await sender.send(Email(to=to, subject=subject, body=body, ...))` 发送邮件
    - 返回 SendResult
  - 提供 `setup_email_worker(email_config: EmailConfig) -> Callable` 工厂函数：
    - 返回一个 `async def on_startup(ctx)` 回调
    - 回调中创建 `SmtpSender(email_config)`，调用 `sender` 存入 `ctx["email_sender"]`
    - 返回 `async def on_shutdown(ctx)` 回调关闭 sender
  - 在 `email/__init__.py` 中导出 `send_email_task`, `setup_email_worker`
  - 更新 `email/README.md` 增加"异步发送"章节
  - 新增测试 `tests/email/test_task.py`

  **Must NOT do**:
  - 不修改 `EmailSender` / `SmtpSender` 类
  - 不使用闭包（ARQ 无法序列化闭包）
  - 不在 task.py 中导入 SmtpSender（避免不必要的耦合，通过 ctx 注入）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T7, T8, T9, T10)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/task_queue/task.py:16-61` — `@task` 装饰器，注册到全局 `_REGISTRY`，函数签名第一个参数必须是 ctx
  - `basic_tool/email/sender.py:24-61` — EmailSender ABC，`send(email: Email) -> SendResult`
  - `basic_tool/email/models.py` — Email 数据模型，需查看构造参数
  - `basic_tool/email/config.py` — EmailConfig
  - `basic_tool/task_queue/worker.py:39-49` — `_on_startup` / `_on_shutdown` 回调模式，ctx 是 dict
  - ARQ 序列化限制：任务函数必须是模块级可引用的，闭包不可序列化

  **Acceptance Criteria**:
  - [ ] `send_email_task` 在 `@task` 注册表中
  - [ ] `setup_email_worker()` 返回的 on_startup 回调在 ctx 中设置 email_sender
  - [ ] 任务执行时调用 sender.send() 并返回 SendResult

  **QA Scenarios**:
  ```
  Scenario: 异步邮件发送流程
    Tool: Bash (pytest)
    Preconditions: AsyncMock 模拟 EmailSender.send()
    Steps:
      1. 调用 setup_email_worker(EmailConfig(...)) 获取 on_startup
      2. 执行 on_startup(ctx) 设置 email_sender
      3. 调用 send_email_task(ctx, to=["a@b.com"], subject="test", body="hello")
      4. 验证 sender.send 被 await 调用一次
    Expected Result: send 被调用，返回 SendResult
    Evidence: .sisyphus/evidence/task-11-async-email.txt

  Scenario: 缺少 email_sender 时报错
    Tool: Bash (pytest)
    Preconditions: ctx 中无 email_sender
    Steps:
      1. 调用 send_email_task(ctx, ...)
    Expected Result: raise RuntimeError("email_sender not found in worker context")
    Evidence: .sisyphus/evidence/task-11-no-sender.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(email): add async email sending via task_queue integration`
  - Files: `email/task.py` (new), `email/__init__.py`, `email/README.md`, `tests/email/test_task.py`
  - Pre-commit: `pytest tests/email/ -v`

- [x] 12. **#4 middleware 请求指标采集（直接注入 MetricsCollector）**

  **What to do**:
  - 在 `fastapi/config.py` 的 `FastApiConfig` 中增加字段 `metrics: MetricsCollector | None = None`
  - 在 `fastapi/middleware.py` 的 `RequestLoggingMiddleware` 中：
    - 增加 `__init__` 接受可选 `metrics: MetricsCollector | None = None` 参数
    - 在 `dispatch()` 方法中记录请求指标：
      - `self._metrics.counter("http_requests_total", labels={"method": method, "path": path, "status": str(status_code)})` 在响应后调用
      - `self._metrics.histogram("http_request_duration_seconds", elapsed_ms / 1000, labels={"method": method, "path": path})` 在响应后调用
    - 当 metrics=None 时跳过所有指标记录（零开销）
  - 在 `fastapi/app.py` 的 `create_app()` 中：
    - 传递 `config.metrics` 给 `RequestLoggingMiddleware`（如果 enable_request_logging）
    - 方式：`app.add_middleware(RequestLoggingMiddleware, metrics=config.metrics)`
  - 在 `fastapi/middleware.py` 顶部增加 `from basic_tool.metrics.collector import MetricsCollector`（仅类型注解用，运行时仅在 metrics 非 None 时使用）
  - 更新 `fastapi/README.md` 说明 metrics 自动采集
  - 新增测试

  **注意**：fastapi → metrics 导入不构成循环（metrics 不导入 fastapi）

  **Must NOT do**:
  - 不在 create_app() 中管理 MetricsCollector 的 init/close 生命周期
  - 不增加新的指标类型
  - metrics 记录失败时不影响请求处理（try/except 包裹）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T13, T14, T15)
  - **Blocks**: F1-F4
  - **Blocked By**: T1（fastapi/app.py 被 T1 修改）

  **References**:
  - `basic_tool/fastapi/middleware.py:19-52` — RequestLoggingMiddleware 当前实现，dispatch() 中已有 method/path/status/elapsed 的日志
  - `basic_tool/fastapi/app.py:162-163` — `app.add_middleware(RequestLoggingMiddleware)` 调用位置
  - `basic_tool/fastapi/config.py:49-75` — FastApiConfig 定义，需增加 metrics 字段
  - `basic_tool/metrics/collector.py:84-124` — MetricsCollector.counter()/gauge()/histogram() 方法签名

  **Acceptance Criteria**:
  - [ ] metrics=None 时请求处理行为与修改前完全一致
  - [ ] metrics 非 None 时 `http_requests_total` 和 `http_request_duration_seconds` 被记录
  - [ ] metrics 记录失败不影响正常请求响应

  **QA Scenarios**:
  ```
  Scenario: metrics 采集验证
    Tool: Bash (pytest)
    Preconditions: 创建 MockMetricsCollector（或真实 MetricsCollector），通过 FastApiConfig 传入
    Steps:
      1. 使用 TestClient 发送 GET /health
      2. 检查 collector._buffers 包含 "http_requests_total"
      3. 检查 collector._buffers 包含 "http_request_duration_seconds"
    Expected Result: 两个指标各至少 1 个 MetricPoint
    Evidence: .sisyphus/evidence/task-12-metrics-collection.txt

  Scenario: metrics=None 时零开销
    Tool: Bash (pytest)
    Preconditions: FastApiConfig() 不设置 metrics
    Steps:
      1. 发送 GET /health
      2. 验证响应正常，无异常
    Expected Result: 正常 200 响应，无指标记录
    Evidence: .sisyphus/evidence/task-12-no-metrics.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(fastapi): collect request metrics in middleware via optional MetricsCollector`
  - Files: `fastapi/middleware.py`, `fastapi/config.py`, `fastapi/app.py`, `fastapi/README.md`, `tests/test_fastapi/test_middleware.py`
  - Pre-commit: `pytest tests/test_fastapi/test_middleware.py -v`

---

- [x] 13. **#5 errors 错误计数（回调协议避免循环导入）**

  **What to do**:
  - 在 `errors/log.py` 的 `log_error()` 函数中增加可选参数 `on_error: Callable[[str, int], None] | None = None`
    - 参数含义：`on_error(error_code: str, http_status: int)` 回调函数
    - 在函数末尾调用：`if on_error is not None: try: on_error(exc.code if isinstance(exc, AppError) else "UNKNOWN", exc.http_status if isinstance(exc, AppError) else 500) except: pass`
  - 在 `errors/handler.py` 的 `setup_error_handlers()` 中增加可选 `on_error` 参数
    - 在各异常处理器的 `log_error()` 调用中传递 `on_error` 回调
  - **不在 errors 模块中导入 MetricsCollector**——回调由调用方（create_app 或业务代码）提供
  - 更新 `errors/README.md` 说明 on_error 回调用于外部指标采集

  **架构说明（为何用回调而非直接注入）**：
  ```
  如果 errors 直接导入 metrics：
    errors → metrics → redis → errors (RateLimitError 是 AppError 子类)
    形成 3-cycle 循环导入！

  使用回调协议：
    errors 不导入 metrics
    create_app(handler) 或业务代码在调用 setup_error_handlers() 时传入回调
    回调内部调用 metrics.counter("errors_total", ...)
    errors 保持为 DAG 叶子节点
  ```

  **Must NOT do**:
  - 不在 errors/log.py 或 errors/handler.py 中导入 basic_tool.metrics
  - 不改变 log_error() 现有参数的顺序（on_error 放最后）
  - 不在 on_error 回调失败时中断错误处理流程

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T12, T14, T15)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `basic_tool/errors/log.py:15-83` — `log_error()` 函数，需增加 on_error 参数
  - `basic_tool/errors/handler.py:40-116` — `setup_error_handlers()` 中三个异常处理器都调用 `log_error()`
  - `basic_tool/errors/app_error.py:10-39` — AppError 有 `.code` 和 `.http_status` 属性

  **Acceptance Criteria**:
  - [ ] `log_error()` 接受 on_error 参数，默认 None
  - [ ] on_error 非 None 时在日志记录后调用
  - [ ] on_error 抛异常时不影响错误处理流程
  - [ ] errors 模块不导入 metrics（`grep "import.*metrics" basic_tool/errors/*.py` 无结果）

  **QA Scenarios**:
  ```
  Scenario: on_error 回调被调用
    Tool: Bash (pytest)
    Preconditions: 创建 mock callback
    Steps:
      1. 调用 log_error(AppError("TEST", "msg", 400), on_error=mock_callback)
      2. 验证 mock_callback 被调用，参数为 ("TEST", 400)
    Expected Result: callback 调用一次，参数正确
    Evidence: .sisyphus/evidence/task-13-on-error-callback.txt

  Scenario: on_error=None 时行为不变
    Tool: Bash (pytest)
    Steps:
      1. 调用 log_error(AppError(...)) 不传 on_error
      2. 验证无异常，日志正常输出
    Expected Result: 正常执行
    Evidence: .sisyphus/evidence/task-13-no-callback.txt

  Scenario: 循环导入验证
    Tool: Bash (python)
    Steps:
      1. python -c "import basic_tool.errors; import basic_tool.metrics; import basic_tool.redis; print('OK')"
    Expected Result: "OK"，无 ImportError
    Evidence: .sisyphus/evidence/task-13-no-cycle.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(errors): add on_error callback for external metrics integration (cycle-safe)`
  - Files: `errors/log.py`, `errors/handler.py`, `errors/README.md`, `tests/errors/test_log.py`
  - Pre-commit: `pytest tests/errors/ -v`

---

- [x] 14. **#6 redis @cached 缓存命中率（回调协议避免循环导入）**

  **What to do**:
  - 在 `redis/decorators.py` 的 `cached()` 装饰器中增加两个可选参数：
    - `on_cache_hit: Callable[[str], None] | None = None` — 缓存命中时调用，参数为 cache key
    - `on_cache_miss: Callable[[str], None] | None = None` — 缓存未命中时调用，参数为 cache key
  - 在 wrapper 函数中：
    - 缓存命中时（`cached_val is not _MISSING and await cache.exists(key)` 为 True）：`if on_cache_hit: try: on_cache_hit(key) except: pass`
    - 缓存未命中时（执行函数前）：`if on_cache_miss: try: on_cache_miss(key) except: pass`
  - **不在 redis 模块中导入 MetricsCollector**
  - 更新 `redis/README.md` 说明 on_cache_hit/on_cache_miss 回调

  **架构说明（为何用回调而非直接注入）**：
  ```
  metrics/writer.py:13 已有：metrics → redis (Cache)
  如果 redis 再导入 metrics：redis → metrics
  形成 redis ↔ metrics 2-cycle 循环导入！

  使用回调协议：
    redis 不导入 metrics
    调用方在装饰器使用时传入回调：
      collector = MetricsCollector(...)
      @cached(prefix="user", ttl=600,
              on_cache_hit=lambda k: collector.counter("cache_hits_total", labels={"key": k}),
              on_cache_miss=lambda k: collector.counter("cache_misses_total", labels={"key": k}))
    redis 保持为 DAG 叶子节点
  ```

  **Must NOT do**:
  - 不在 redis/decorators.py 中导入 basic_tool.metrics
  - 不改变 cached() 现有参数顺序（on_cache_hit/on_cache_miss 放最后）
  - 不在回调失败时中断缓存逻辑

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T12, T13, T15)
  - **Blocks**: None
  - **Blocked By**: T2（redis/decorators.py 被 T2 修改），T10（redis/client/__init__.py 被 T10 修改，但本 task 只改 decorators.py）

  **References**:
  - `basic_tool/redis/decorators.py:83-157` — `cached()` 装饰器当前实现
  - `basic_tool/redis/decorators.py:145-147` — 缓存命中判断逻辑 `cached_val is not _MISSING and await cache.exists(key)`
  - `basic_tool/metrics/writer.py:13` — 已有的 metrics → redis 导入，证明 2-cycle 风险

  **Acceptance Criteria**:
  - [ ] `cached()` 接受 on_cache_hit/on_cache_miss 参数，默认 None
  - [ ] 缓存命中时调用 on_cache_hit，未命中时调用 on_cache_miss
  - [ ] 回调参数为 cache key 字符串
  - [ ] redis 模块不导入 metrics（`grep "import.*metrics" basic_tool/redis/decorators.py` 无结果）

  **QA Scenarios**:
  ```
  Scenario: 缓存命中回调
    Tool: Bash (pytest)
    Preconditions: fakeredis 可用
    Steps:
      1. 创建 mock_hit 和 mock_miss callback
      2. @cached(prefix="test", ttl=60, on_cache_hit=mock_hit, on_cache_miss=mock_miss)
      3. 第一次调用 → miss callback 被调用
      4. 第二次调用 → hit callback 被调用
    Expected Result: miss 调用 1 次，hit 调用 1 次
    Evidence: .sisyphus/evidence/task-14-cache-callbacks.txt

  Scenario: 回调=None 时行为不变
    Tool: Bash (pytest)
    Steps:
      1. @cached(prefix="test", ttl=60) 不传回调
      2. 正常调用两次，验证缓存命中行为不变
    Expected Result: 行为与修改前一致
    Evidence: .sisyphus/evidence/task-14-no-callbacks.txt

  Scenario: 循环导入验证
    Tool: Bash (python)
    Steps:
      1. python -c "import basic_tool.redis; import basic_tool.metrics; print('OK')"
    Expected Result: "OK"
    Evidence: .sisyphus/evidence/task-14-no-cycle.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(redis): add cache hit/miss callbacks for metrics integration (cycle-safe)`
  - Files: `redis/decorators.py`, `redis/README.md`, `tests/redis/test_decorators.py`
  - Pre-commit: `pytest tests/redis/test_decorators.py -v`

---

- [x] 15. **#7 http_client 出站请求指标（直接注入 MetricsCollector）**

  **What to do**:
  - 在 `http_client/config.py` 的 `HttpConfig` 中增加字段 `metrics: MetricsCollector | None = None`
  - 在 `http_client/client.py` 的 `_build_event_hooks()` 中：
    - 当 `self._config.metrics` 非 None 时，在 `on_response` 钩子中记录：
      - `self._config.metrics.counter("http_client_requests_total", labels={"method": method, "url": str(url), "status": str(status)})`
      - `self._config.metrics.histogram("http_client_request_duration_seconds", elapsed_ms / 1000, labels={"method": method, "url": str(url)})`
    - 在 `RetryTransport` 的重试日志处（transport.py:68,76,88）旁边增加可选的 metrics 重试计数
  - 在 `http_client/client.py` 和 `http_client/transport.py` 顶部增加 `from basic_tool.metrics.collector import MetricsCollector`（仅类型注解用）
  - **注意**：http_client → metrics 导入不构成循环（metrics 不导入 http_client，metrics 只导入 redis）
  - 更新 `http_client/README.md`

  **Must NOT do**:
  - 不在 metrics=None 时增加任何开销
  - 不记录请求/响应 body 到 metrics
  - metrics 记录失败时不影响 HTTP 请求

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T12, T13, T14)
  - **Blocks**: F1-F4
  - **Blocked By**: T7（http_client/client.py 和 config.py 被 T7 修改）

  **References**:
  - `basic_tool/http_client/client.py:151-190` — `_build_event_hooks()` 方法，on_response 钩子在约 168 行
  - `basic_tool/http_client/config.py` — HttpConfig 类，需增加 metrics 字段
  - `basic_tool/http_client/transport.py:68,76,88` — RetryTransport 重试日志位置
  - `basic_tool/metrics/collector.py:84-124` — MetricsCollector API

  **Acceptance Criteria**:
  - [ ] metrics=None 时 HTTP 客户端行为不变
  - [ ] metrics 非 None 时 `http_client_requests_total` 和 `http_client_request_duration_seconds` 被记录
  - [ ] http_client → metrics 导入不构成循环

  **QA Scenarios**:
  ```
  Scenario: 出站请求指标采集
    Tool: Bash (pytest)
    Preconditions: HttpConfig(metrics=collector), httpx.MockTransport 模拟响应
    Steps:
      1. 发送 GET 请求
      2. 检查 collector._buffers 包含 "http_client_requests_total"
      3. 检查 collector._buffers 包含 "http_client_request_duration_seconds"
    Expected Result: 两个指标各至少 1 个 MetricPoint
    Evidence: .sisyphus/evidence/task-15-http-metrics.txt

  Scenario: metrics=None 零开销
    Tool: Bash (pytest)
    Steps:
      1. HttpConfig() 不设置 metrics
      2. 发送请求，验证行为正常
    Expected Result: 正常响应，无指标记录
    Evidence: .sisyphus/evidence/task-15-no-metrics.txt

  Scenario: 循环导入验证
    Tool: Bash (python)
    Steps:
      1. python -c "import basic_tool.http_client; import basic_tool.metrics; print('OK')"
    Expected Result: "OK"
    Evidence: .sisyphus/evidence/task-15-no-cycle.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(http_client): collect outbound request metrics via optional MetricsCollector`
  - Files: `http_client/client.py`, `http_client/config.py`, `http_client/transport.py`, `http_client/README.md`, `tests/http_client/test_client.py`
  - Pre-commit: `pytest tests/http_client/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v` + linter. Review all changed files for: `as any`/type ignores, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(integrations): foundation - log injection idempotency, error unification, auth context, worker retry control`
- **Wave 2**: `feat(integrations): context propagation - http trace, task queue context, storage/redis logging, async email`
- **Wave 3**: `feat(integrations): metrics collection - middleware, errors, cache hit rate, http client`
- **FINAL**: no commit (review only)

---

## Success Criteria

### Verification Commands
```bash
# No circular imports
python -c "import basic_tool.fastapi; import basic_tool.redis; import basic_tool.metrics; import basic_tool.errors; import basic_tool.crypto; import basic_tool.http_client; import basic_tool.task_queue; import basic_tool.storage; import basic_tool.email; print('OK')"

# All tests pass
pytest tests/ -v

# enable_log_injection idempotent
python -c "from basic_tool.context import enable_log_injection; enable_log_injection(); enable_log_injection(); print('OK')"
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] `pytest tests/ -v` — 0 failures
- [x] No circular imports
- [x] All README.md updated
