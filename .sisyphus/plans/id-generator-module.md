# 实现 basic_tool.id_generator 模块

## TL;DR

> **Quick Summary**: 在 `basic_tool/id_generator/` 下新建分布式链路追踪（W3C Trace Context）和唯一 ID 生成（Snowflake）模块，零外部依赖，含完整单元测试。
> 
> **Deliverables**:
> - 4 个源文件：config.py, trace.py, generator.py, __init__.py
> - 1 个 README.md
> - 2 个测试文件 + 测试包标记
> - pyproject.toml 版本号升级到 0.5.0
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 4 → Task 5 → Task 6

---

## Context

### Original Request
用户提供了完整的设计文档 `doc/basic_tool_id_generator_design.md`，要求按设计实现 `basic_tool/id_generator` 子模块，提供分布式链路追踪（W3C Trace Context）和业务唯一 ID 生成（Snowflake）两大能力。

### Interview Summary
**Key Discussions**:
- 实现策略：以设计文档为基础，允许根据代码库实际情况微调
- Metis 发现了设计文档中的几个代码 bug 和测试缺口，需在实现中修复

**Research Findings**:
- 代码库约定确认：Pydantic BaseModel 配置 + 绝对导入 + `__all__` 导出 + README.md
- 测试框架：pytest + asyncio_mode="auto"，class-based 分组，plain assert
- 当前版本：0.4.0，升级到 0.5.0

### Metis Review
**Identified Gaps** (addressed):
- `new()` 的 `Raises: RuntimeError` 文档与代码不匹配 → 修正 docstring，保留自旋等待行为但移除虚假的 Raises 声明
- `generator.py` 中 `import os` 未使用 → 移除
- `IDGenerator.__init__` 中 worker_id 重复验证 → 移除（Pydantic 已处理）
- `from_traceparent` 不验证 hex 内容 → 增加 hex 格式校验
- 时钟回拨测试/序列溢出测试需要 mock `_current_ms` → 使用 monkeypatch，配合 `pytest.mark.timeout(5)` 防止无限循环

---

## Work Objectives

### Core Objective
按设计文档实现 `basic_tool/id_generator` 模块，修复已知 bug，编写覆盖所有公开 API 的单元测试。

### Concrete Deliverables
- `basic_tool/id_generator/config.py` — IDConfig（Pydantic BaseModel）
- `basic_tool/id_generator/trace.py` — TraceContext（W3C Trace Context）
- `basic_tool/id_generator/generator.py` — IDGenerator（Snowflake）+ TraceGenerator
- `basic_tool/id_generator/__init__.py` — 平铺导出
- `basic_tool/id_generator/README.md` — 模块文档
- `tests/id_generator/__init__.py` — 测试包标记
- `tests/id_generator/test_trace.py` — TraceContext + TraceGenerator 测试
- `tests/id_generator/test_generator.py` — IDGenerator 测试
  - `pyproject.toml` — version 升级到 0.5.0（若已是 0.5.0 则跳过）

### Definition of Done
- [ ] `python -c "from basic_tool.id_generator import IDConfig, IDGenerator, TraceContext, TraceGenerator"` 无报错
- [ ] `pytest tests/id_generator/ -v` 全部通过
- [ ] `pytest tests/ -v` 全部通过（零回归）
- [ ] 所有公开类/方法有 docstring
- [ ] README.md 覆盖所有公开 API

### Must Have
- W3C 兼容的 TraceContext（trace_id 32位 hex, span_id 16位 hex）
- Snowflake IDGenerator（64-bit, 趋势递增, 线程安全）
- 完整单元测试覆盖（含时钟回拨、序列溢出等边界场景）
- hex 格式校验（`from_traceparent` 拒绝非 hex 字符）

### Must NOT Have (Guardrails)
- **不得**修改 `conftest.py`（id_generator 不需要共享 fixture）
- **不得**修改 `basic_tool/__init__.py`（已过时，不在本次范围）
- **不得**添加 contextvars 集成或自动 trace 传播
- **不得**实现 FastAPI 中间件代码（仅作为 README 中的使用示例）
- **不得**给 TraceContext 添加 `__eq__`/`__hash__`/dataclass 转换
- **不得**添加 logger 集成代码
- **不得**添加 `os` import（设计文档中的错误）
- **不得**在 IDGenerator.__init__ 中重复验证 worker_id（Pydantic 已处理）

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES（pytest + pytest-asyncio）
- **Automated tests**: TDD — 每个实现任务包含对应测试
- **Framework**: pytest

### QA Policy
每个任务包含 agent-executed QA scenarios。Evidence saved to `.sisyphus/evidence/`.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - foundation, no dependencies):
├── Task 1: config.py — IDConfig 配置模型 [quick]
├── Task 2: trace.py — TraceContext 链路上下文 [quick]
└── (Task 3 depends on both, so Wave 1 is sequential in practice)

Wave 2 (After Task 1 & 2 - core implementation):
├── Task 3: generator.py — IDGenerator + TraceGenerator [deep]
└── (depends: config.py, trace.py)

Wave 3 (After Task 3 - integration + docs):
├── Task 4: __init__.py — 平铺导出 [quick]
├── Task 5: README.md — 模块文档 [writing]
├── Task 6: pyproject.toml 版本升级 + 全量测试验证 [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → Task 3 → Task 4 → Task 5 → Task 6 → F1-F4
Parallel Speedup: Wave 1 tasks can be done by same agent sequentially (small files)
Max Concurrent: 2 (Wave 1, Task 1 & 2 could be parallel but single agent handles both)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 3, 4 | 1 |
| 2 | — | 3, 4 | 1 |
| 3 | 1, 2 | 4 | 2 |
| 4 | 1, 2, 3 | 5, 6 | 3 |
| 5 | 4 | 6 | 3 |
| 6 | 4, 5 | F1-F4 | 3 |
| F1-F4 | 6 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 1 agent — T1 `quick`, T2 `quick`
- **Wave 2**: 1 agent — T3 `deep`
- **Wave 3**: 1 agent — T4 `quick`, T5 `writing`, T6 `quick`
- **FINAL**: 4 agents — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. 实现 config.py + trace.py — IDConfig 配置模型与 TraceContext 链路上下文

  **What to do**:
  - 创建 `basic_tool/id_generator/` 目录
  - 创建 `basic_tool/id_generator/config.py`：IDConfig（Pydantic BaseModel），字段 worker_id（int, 0-1023, default=0）和 epoch（int, default=1704067200000），带完整 docstring
  - 创建 `basic_tool/id_generator/trace.py`：TraceContext 类，使用 `__slots__`，属性 trace_id/span_id/parent_span_id
    - `__init__(trace_id, span_id, parent_span_id="")`
    - `root()` classmethod：使用 `secrets.token_hex(16)` 生成 trace_id，`secrets.token_hex(8)` 生成 span_id
    - `child_span()`：共享 trace_id，当前 span_id 成为 parent_span_id，生成新 span_id
    - `to_traceparent()`：格式 `"00-{trace_id}-{span_id}-01"`
    - `from_traceparent(header)` classmethod：解析 traceparent，验证版本号、trace_id 长度(32)、span_id 长度(16)，**增加 hex 格式校验**（使用 `int(value, 16)` 或正则验证）
    - `__repr__`
  - 所有类和公开方法必须有 docstring（含 Args/Returns/Raises 部分）

  **Must NOT do**:
  - 不添加 `__eq__`/`__hash__`/dataclass 转换
  - 不添加 contextvars 集成
  - 不使用外部依赖（仅标准库 secrets + pydantic）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO（两个文件共同被 Task 3 依赖，单个 agent 顺序处理更高效）
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/task_queue/config.py` — Pydantic BaseModel 配置模式（class docstring + Attributes 部分 + Field 定义）
  - `basic_tool/redis/config.py` — 另一个 Pydantic config 参考

  **Design Doc References**:
  - `doc/basic_tool_id_generator_design.md:84-105` — IDConfig 完整代码
  - `doc/basic_tool_id_generator_design.md:113-215` — TraceContext 完整代码
  - **注意**：`from_traceparent` 方法需增加 hex 格式校验（设计文档中缺失）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: config.py — IDConfig 验证
    Tool: Bash
    Preconditions: 文件已创建
    Steps:
      1. python -c "from basic_tool.id_generator.config import IDConfig; c = IDConfig(); print(c.worker_id, c.epoch)"
      2. python -c "from basic_tool.id_generator.config import IDConfig; IDConfig(worker_id=1024)" 2>&1
    Expected Result: Step 1 输出 "0 1704067200000"；Step 2 输出包含 "validation error" 的错误信息
    Evidence: .sisyphus/evidence/task-1-config-validation.txt

  Scenario: trace.py — TraceContext 核心功能
    Tool: Bash
    Steps:
      1. python -c "
from basic_tool.id_generator.trace import TraceContext
ctx = TraceContext.root()
assert len(ctx.trace_id) == 32, f'trace_id len: {len(ctx.trace_id)}'
assert len(ctx.span_id) == 16, f'span_id len: {len(ctx.span_id)}'
assert ctx.parent_span_id == ''

child = ctx.child_span()
assert child.trace_id == ctx.trace_id
assert child.span_id != ctx.span_id
assert child.parent_span_id == ctx.span_id

tp = child.to_traceparent()
parsed = TraceContext.from_traceparent(tp)
assert parsed.trace_id == child.trace_id
assert parsed.span_id == child.span_id
print('trace ok')
"
    Expected Result: 输出 "trace ok"
    Evidence: .sisyphus/evidence/task-1-trace-basic.txt

  Scenario: trace.py — from_traceparent 拒绝非法输入
    Tool: Bash
    Steps:
      1. python -c "
from basic_tool.id_generator.trace import TraceContext
import traceback
# 非法格式（部分数不对）
try:
    TraceContext.from_traceparent('00-abc-def')
    assert False, 'should raise'
except ValueError as e:
    print(f'bad format: {e}')

# 非法版本号
try:
    TraceContext.from_traceparent('01-' + 'a'*32 + '-' + 'b'*16 + '-01')
    assert False, 'should raise'
except ValueError as e:
    print(f'bad version: {e}')

# trace_id 长度不对
try:
    TraceContext.from_traceparent('00-' + 'a'*16 + '-' + 'b'*16 + '-01')
    assert False, 'should raise'
except ValueError as e:
    print(f'bad trace_id len: {e}')

# 非 hex 字符（关键：设计文档缺失的校验）
try:
    TraceContext.from_traceparent('00-' + 'z'*32 + '-' + 'a'*16 + '-01')
    assert False, 'should raise'
except ValueError as e:
    print(f'bad hex: {e}')

print('validation ok')
"
    Expected Result: 输出 4 条错误信息和 "validation ok"
    Evidence: .sisyphus/evidence/task-1-trace-validation.txt
  ```

  **Commit**: NO（与后续任务合并提交）

- [x] 2. 实现 generator.py — IDGenerator（Snowflake）+ TraceGenerator

  **What to do**:
  - 创建 `basic_tool/id_generator/generator.py`
  - 实现 `IDGenerator` 类：
    - `__init__(config: IDConfig)` — 接收 IDConfig，初始化 threading.Lock、sequence、last_ts
    - **移除设计文档中的 `import os`**（未使用）
    - **移除设计文档中 worker_id > _MAX_WORKER_ID 的重复检查**（Pydantic 已验证）
    - **修正 `new()` 的 docstring**：移除 `Raises: RuntimeError` 声明（实际代码是自旋等待，不抛异常）
    - `_current_ms()` — `int(time.time() * 1000)`
    - `_wait_next_ms(ts)` — 自旋等待到下一毫秒
    - `_next_id_unlocked()` — 核心 Snowflake 算法（在锁内调用）
    - `new()` — 生成一个 ID，with lock
    - `batch(count)` — 批量生成，count <= 0 抛 ValueError
    - `new_prefixed(prefix)` — 如 `"ORD_123456789"`
  - 实现 `TraceGenerator` 类：
    - 无状态，无需 __init__ 参数
    - `new_trace()` → `TraceContext.root()`
    - `trace_id()` → `secrets.token_hex(16)`
    - `span_id()` → `secrets.token_hex(8)`
    - `from_traceparent(header)` → `TraceContext.from_traceparent(header)` (staticmethod)

  **Must NOT do**:
  - 不添加 `import os`
  - 不在 IDGenerator.__init__ 中重复验证 worker_id
  - 不实现 RuntimeError 抛出（保留自旋等待行为）
  - 不给 TraceGenerator 添加状态/单例/lifecycle
  - 不使用外部依赖

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **Design Doc References**:
  - `doc/basic_tool_id_generator_design.md:225-427` — 完整的 IDGenerator + TraceGenerator 代码
  - **Bug fixes to apply**:
    - 第 228 行：移除 `import os`
    - 第 270-273 行：移除 worker_id 重复验证
    - 第 322 行：移除 `Raises: RuntimeError` docstring

  **Pattern References**:
  - `basic_tool/redis/client/__init__.py` — threading.Lock 使用模式参考

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: IDGenerator 基本功能
    Tool: Bash
    Steps:
      1. python -c "
from basic_tool.id_generator.config import IDConfig
from basic_tool.id_generator.generator import IDGenerator, TraceGenerator
import sys

# IDGenerator
config = IDConfig(worker_id=1)
gen = IDGenerator(config)

id1 = gen.new()
assert isinstance(id1, int), f'expected int, got {type(id1)}'
assert id1 > 0, f'expected positive, got {id1}'
assert id1 < (1 << 63), f'exceeds 63 bits: {id1}'

id2 = gen.new()
assert id2 > id1, f'not monotonic: {id2} <= {id1}'

# batch
ids = gen.batch(100)
assert len(ids) == 100
assert len(set(ids)) == 100, 'batch has duplicates'
assert all(ids[i] < ids[i+1] for i in range(99)), 'batch not monotonic'

# prefixed
prefixed = gen.new_prefixed('ORD')
assert prefixed.startswith('ORD_'), f'bad prefix: {prefixed}'
assert prefixed[4:].isdigit(), f'bad id part: {prefixed}'

# TraceGenerator
tg = TraceGenerator()
ctx = tg.new_trace()
assert len(ctx.trace_id) == 32
assert len(ctx.span_id) == 16

tid = tg.trace_id()
assert len(tid) == 32
sid = tg.span_id()
assert len(sid) == 16

print('generator ok')
"
    Expected Result: 输出 "generator ok"
    Evidence: .sisyphus/evidence/task-2-generator-basic.txt

  Scenario: batch 无效参数
    Tool: Bash
    Steps:
      1. python -c "
from basic_tool.id_generator.config import IDConfig
from basic_tool.id_generator.generator import IDGenerator
gen = IDGenerator(IDConfig())
try:
    gen.batch(0)
    assert False
except ValueError:
    print('batch(0) rejected ok')
try:
    gen.batch(-1)
    assert False
except ValueError:
    print('batch(-1) rejected ok')
"
    Expected Result: 两条 "rejected ok" 输出
    Evidence: .sisyphus/evidence/task-2-batch-validation.txt
  ```

  **Commit**: NO（与后续任务合并提交）

- [x] 3. 实现 __init__.py + 测试文件 + README.md + pyproject.toml 升级

  **What to do**:

  **Part A: `basic_tool/id_generator/__init__.py`**
  - 模块级 docstring（中文，描述用途 + 使用示例）
  - 绝对导入：IDConfig, IDGenerator, TraceContext, TraceGenerator
  - `__all__` 列出全部公开符号
  - 参考 `basic_tool/task_queue/__init__.py` 的风格

  **Part B: `tests/id_generator/__init__.py`**
  - 空文件（包标记）

  **Part C: `tests/id_generator/test_trace.py`**
  - TraceContext 测试类（class-based grouping）：
    - `test_root` — 新建 trace 的 trace_id/span_id 长度正确，parent_span_id 为空
    - `test_child_span` — 子 span 共享 trace_id，span_id 不同，parent_span_id 指向父
    - `test_to_traceparent` — 格式验证 "00-{trace_id}-{span_id}-01"
    - `test_from_traceparent_valid` — 正确解析合法 header
    - `test_from_traceparent_invalid_format` — 格式错误抛 ValueError（部分数不对、版本号错、长度错）
    - `test_from_traceparent_invalid_hex` — 非 hex 字符抛 ValueError
    - `test_roundtrip` — `from_traceparent(ctx.to_traceparent())` 还原一致
    - `test_repr` — `__repr__` 输出包含 trace_id 和 span_id
  - TraceGenerator 测试类：
    - `test_trace_id_length` — 32 位 hex
    - `test_span_id_length` — 16 位 hex
    - `test_new_trace` — 返回 TraceContext
    - `test_uniqueness` — 生成 10000 个 trace_id 无重复
  - 每个测试类和方法有 docstring

  **Part D: `tests/id_generator/test_generator.py`**
  - IDGenerator 测试类：
    - `test_new_returns_positive_int` — 返回正整数
    - `test_new_64bit` — 值 < 2^63
    - `test_new_unique` — 生成 10000 个 ID 无重复
    - `test_new_monotonic` — 连续生成严格递增
    - `test_batch_count` — batch(100) 返回 100 个元素
    - `test_batch_unique` — 批量内无重复
    - `test_batch_monotonic` — 批量内严格递增
    - `test_batch_zero_raises` — batch(0) 抛 ValueError
    - `test_batch_negative_raises` — batch(-1) 抛 ValueError
    - `test_new_prefixed` — 格式正确 "ORD_123456"
    - `test_different_worker_ids` — 不同 worker_id 生成的 ID 不冲突（同秒内）
    - `test_clock_backward` — 时钟回拨场景（monkeypatch `_current_ms` 返回递减时间戳，验证生成不挂起；mock 需先返回 T，再返回 T-100（回拨），再返回 T+1（恢复），验证 ID 仍能生成）
    - `test_sequence_overflow` — 同毫秒超过 4096 个（mock `_current_ms` 固定返回同一时间戳，直接调用 `_next_id_unlocked` 4097 次触发溢出路径）
  - **重要**：clock_backward 和 sequence_overflow 测试需用 `monkeypatch` 或 `unittest.mock.patch` 替换 `_current_ms`，避免 `_wait_next_ms` 的无限循环

  **Part E: `basic_tool/id_generator/README.md`**
  - 模块概述、安装说明、公开 API 速查表（参考 `basic_tool/redis/README.md` 结构）
  - 包含使用示例：链路追踪、业务 ID、FastAPI 集成

  **Part F: `pyproject.toml`**
  - 检查 version 字段，若已是 `"0.5.0"` 则无需修改；若为 `"0.4.0"` 则升级到 `"0.5.0"`

  **Must NOT do**:
  - 不修改 conftest.py
  - 不修改 basic_tool/__init__.py
  - 不创建 tests/id_generator/conftest.py
  - 不在 clock_backward 测试中让 mock 始终返回过去时间（会挂死测试）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 4 (Final Verification)
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `basic_tool/task_queue/__init__.py` — __init__.py 导出风格（docstring + 绝对导入 + __all__）
  - `basic_tool/redis/README.md` — README.md 结构参考
  - `tests/task_queue/test_queue.py` — 测试 class-based 分组风格
  - `tests/logger/test_logger.py` — 简单模块测试风格参考

  **Design Doc References**:
  - `doc/basic_tool_id_generator_design.md:433-447` — __init__.py 完整代码
  - `doc/basic_tool_id_generator_design.md:449-578` — 使用示例（README 内容来源）
  - `doc/basic_tool_id_generator_design.md:596-629` — 完整测试用例列表

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 模块导入验证
    Tool: Bash
    Steps:
      1. python -c "from basic_tool.id_generator import IDConfig, IDGenerator, TraceContext, TraceGenerator; print('import ok')"
    Expected Result: 输出 "import ok"
    Evidence: .sisyphus/evidence/task-3-import.txt

  Scenario: 新模块测试通过
    Tool: Bash
    Steps:
      1. pytest tests/id_generator/ -v
    Expected Result: 所有测试通过，exit code 0
    Evidence: .sisyphus/evidence/task-3-tests.txt

  Scenario: 全量回归测试
    Tool: Bash
    Steps:
      1. pytest tests/ -v
    Expected Result: 所有测试通过（包括原有 redis/logger/task_queue 等测试），exit code 0
    Evidence: .sisyphus/evidence/task-3-regression.txt

  Scenario: 特殊边界测试 — 时钟回拨不挂起
    Tool: Bash
    Steps:
      1. pytest tests/id_generator/test_generator.py::TestIDGenerator::test_clock_backward -v --timeout=10
    Expected Result: 测试在 10 秒内完成（不会因 _wait_next_ms 无限循环而挂起）
    Evidence: .sisyphus/evidence/task-3-clock-backward.txt

  Scenario: 特殊边界测试 — 序列溢出
    Tool: Bash
    Steps:
      1. pytest tests/id_generator/test_generator.py::TestIDGenerator::test_sequence_overflow -v --timeout=10
    Expected Result: 测试在 10 秒内完成，验证同毫秒 4097+ 个 ID 的溢出处理
    Evidence: .sisyphus/evidence/task-3-sequence-overflow.txt

  Scenario: README.md 存在且内容合理
    Tool: Bash
    Steps:
      1. test -f basic_tool/id_generator/README.md && echo "exists"
      2. grep -c "IDGenerator\|TraceContext\|IDConfig\|TraceGenerator" basic_tool/id_generator/README.md
    Expected Result: Step 1 输出 "exists"；Step 2 输出 >= 4（四个公开 API 都在文档中）
    Evidence: .sisyphus/evidence/task-3-readme.txt
  ```

  **Commit**: YES
  - Message: `feat(id_generator): add W3C trace context and snowflake ID generator`
  - Files: all new files + pyproject.toml
  - Pre-commit: `pytest tests/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v` (full suite). Review all changed files for: `as any`/type ignores, empty catches, unused imports, commented-out code. Check AI slop: excessive comments, over-abstraction, generic names. Verify docstrings on all public classes/methods.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run `python -c "from basic_tool.id_generator import IDConfig, IDGenerator, TraceContext, TraceGenerator; print('import ok')"`. Execute key scenarios: generate 100 IDs, verify uniqueness/monotonicity. Create trace context, serialize/parse roundtrip. Batch generation. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Detect files that shouldn't have been touched (conftest.py, basic_tool/__init__.py). Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Single Commit**: `feat(id_generator): add W3C trace context and snowflake ID generator`
  - Files: all new files + pyproject.toml
  - Pre-commit: `pytest tests/ -v`

---

## Success Criteria

### Verification Commands
```bash
# Import check
python -c "from basic_tool.id_generator import IDConfig, IDGenerator, TraceContext, TraceGenerator; print('import ok')"
# Expected: import ok

# New module tests
pytest tests/id_generator/ -v
# Expected: all tests pass

# Full regression check
pytest tests/ -v
# Expected: all tests pass, zero regressions
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] README.md covers all public APIs
- [ ] Docstrings on all public classes/methods
