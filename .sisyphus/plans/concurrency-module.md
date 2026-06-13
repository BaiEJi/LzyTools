# basic_tool.concurrency 模块实现

## TL;DR

> **Quick Summary**: 按 `doc/basic_tool_concurrency_design.md` 设计文档实现 `basic_tool.concurrency` 子模块，包含 8 个源文件 + 31 个 TDD 测试用例。修复设计文档中的两个 bug（`gather_with_retry` re-await 崩溃 + `pool.py` _waiting 死代码）。
>
> **Deliverables**:
> - `basic_tool/concurrency/` — 8 个源文件（config, exceptions, strategy, pool, batch, timeout, task_group, __init__）
> - `tests/concurrency/test_concurrency.py` — 31 个测试用例
> - `basic_tool/concurrency/README.md` — 模块文档
> - `basic_tool/__init__.py` — docstring 新增 concurrency 条目
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1(Types) → T2(Tests) → T3-T6(Impl) → T7(Integration) → FINAL

---

## Context

### Original Request
用户要求按照 `doc/basic_tool_concurrency_design.md`（1120 行完整设计文档）实现 `basic_tool.concurrency` 模块。

### Interview Summary
**Key Discussions**:
- 设计文档包含所有文件的完整实现代码，本质上是精确转录任务
- 测试策略：TDD（Red-Green-Refactor），先写 31 个测试用例，再实现
- 发现两个关键 bug，用户已确认修复方案

**Design Bug Fixes (User Decided)**:
- **Bug 1** — `gather_with_retry` 改用工厂函数 API：`*coro_factories: Callable[[], Coroutine]` 替代 `*coros: Coroutine`，每次重试创建新 coroutine 对象
- **Bug 2** — `pool.py` 实现 `_waiting` 计数追踪：在 semaphore.acquire() 前递增，获取后递减

### Metis Review
**Identified Gaps (addressed)**:
- `gather_with_retry` re-await 崩溃 → 用户决定：改用工厂函数 API
- `_waiting` 计数器死代码 → 用户决定：实现 waiting 追踪
- `ConcurrencyConfig` 定义但未使用 → 保留（按设计文档导出，供未来使用）
- `CompositeError.__str__` 的 zip 不匹配 → 自动修复：guard against mismatched lengths
- `basic_tool/__init__.py` 应改 docstring 而非加 import → 已确认现有模式

---

## Work Objectives

### Core Objective
按设计文档实现 `basic_tool.concurrency` 模块，修复已知 bug，通过全部 31 个测试用例。

### Concrete Deliverables
- `basic_tool/concurrency/config.py` — ConcurrencyConfig 配置模型
- `basic_tool/concurrency/exceptions.py` — CompositeError 聚合异常
- `basic_tool/concurrency/strategy.py` — ErrorStrategy 枚举
- `basic_tool/concurrency/pool.py` — ConcurrencyPool + PoolStats（含 _waiting 修复）
- `basic_tool/concurrency/batch.py` — gather_with_limit / run_in_batches / gather_with_retry（含工厂函数 API 修复）
- `basic_tool/concurrency/timeout.py` — with_timeout
- `basic_tool/concurrency/task_group.py` — TaskGroup
- `basic_tool/concurrency/__init__.py` — 平铺导出
- `basic_tool/concurrency/README.md` — 模块文档
- `tests/concurrency/__init__.py` — 测试包
- `tests/concurrency/test_concurrency.py` — 31 个测试用例
- `basic_tool/__init__.py` — docstring 新增 `- concurrency:` 条目

### Definition of Done
- [ ] `pytest tests/concurrency/ -v` → 31 passed, 0 failed
- [ ] `pytest tests/ -v` → 全部通过（含现有测试）
- [ ] `python -c "from basic_tool.concurrency import gather_with_limit, run_in_batches, gather_with_retry, with_timeout, ErrorStrategy, CompositeError, ConcurrencyPool, PoolStats, TaskGroup, ConcurrencyConfig"` → exit 0
- [ ] `grep "concurrency" basic_tool/__init__.py` → 匹配 docstring 条目

### Must Have
- 所有 31 个测试用例通过
- 设计文档中所有公开 API 可导入
- 每个源文件有 file-level docstring
- 每个公开方法有 docstring
- README.md 包含所有公开 API 文档 + 使用示例
- `gather_with_retry` 使用工厂函数签名：`*coro_factories: Callable[[], Coroutine]`
- `ConcurrencyPool` 正确追踪 `waiting` 计数

### Must NOT Have (Guardrails)
- 不新增任何外部依赖
- 不修改 `pyproject.toml`
- 不修改 `basic_tool/` 下除 `__init__.py` docstring 外的任何现有文件
- 不添加 `@pytest.mark.asyncio` 装饰器（已有 `asyncio_mode = "auto"`）
- 不创建 `tests/concurrency/conftest.py`（不需要 fixtures）
- 不过度抽象或添加设计文档未指定的功能
- 不在生产代码中留 `print()` 语句
- 不添加中文注释（代码注释保持英文）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (`pytest` + `pytest-asyncio` with `asyncio_mode = "auto"`)
- **Automated tests**: YES (TDD)
- **Framework**: pytest
- **TDD Flow**: RED (write 31 tests → all fail) → GREEN (implement → all pass) → REFACTOR (if needed)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module import**: Use Bash (`python -c "from basic_tool.concurrency import ..."`)
- **Test execution**: Use Bash (`pytest tests/concurrency/ -v`)
- **Full regression**: Use Bash (`pytest tests/ -v`)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (RED - Foundation + Tests, 2 tasks):
├── Task 1: Create foundational types [quick]
│   exceptions.py + strategy.py + config.py
│   + tests/concurrency/__init__.py
└── Task 2: Write all 31 test cases [unspecified-high]
    tests/concurrency/test_concurrency.py
    NOTE: Tests will FAIL (imports missing) — this is RED phase

Wave 2 (GREEN - Implementation, 4 tasks, MAX PARALLEL):
├── Task 3: Implement timeout.py [quick]
├── Task 4: Implement pool.py (with _waiting fix) [quick]
├── Task 5: Implement batch.py (with factory API fix) [deep]
└── Task 6: Implement task_group.py [quick]

Wave 3 (Integration + Documentation, 3 tasks):
├── Task 7: Wire up __init__.py exports [quick]
│   (depends: T3-T6 all complete)
├── Task 8: Write README.md [writing]
│   (depends: T7 for accurate API list)
└── Task 9: Update basic_tool/__init__.py docstring [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1 | — | T2, T3-T6 | 1 |
| T2 | T1 | T3-T6 (tests exist for validation) | 1 |
| T3 | T1 (types) | T7 | 2 |
| T4 | T1 (types) | T7 | 2 |
| T5 | T1 (exceptions, strategy) | T7 | 2 |
| T6 | T1 (exceptions) | T7 | 2 |
| T7 | T3, T4, T5, T6 | T8, F1-F4 | 3 |
| T8 | T7 | F1-F4 | 3 |
| T9 | — | F1-F4 | 3 |
| F1-F4 | T7, T8, T9 | User okay | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 2 — T1 → `quick`, T2 → `unspecified-high`
- **Wave 2**: 4 — T3 → `quick`, T4 → `quick`, T5 → `deep`, T6 → `quick`
- **Wave 3**: 3 — T7 → `quick`, T8 → `writing`, T9 → `quick`
- **FINAL**: 4 — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Create Foundational Types (exceptions.py, strategy.py, config.py)

  **What to do**:
  - Create directory `basic_tool/concurrency/`
  - Create `basic_tool/concurrency/exceptions.py` — `CompositeError` class per design doc §3.2
  - Create `basic_tool/concurrency/strategy.py` — `ErrorStrategy` enum per design doc §3.3
  - Create `basic_tool/concurrency/config.py` — `ConcurrencyConfig` pydantic model per design doc §3.1
  - Create `tests/concurrency/__init__.py` — empty file
  - **Fix**: In `CompositeError.__str__`, guard against `failed_indices` shorter than `errors`:
    ```python
    for i in range(len(self.errors)):
        idx = self.failed_indices[i] if i < len(self.failed_indices) else i
        err = self.errors[i]
        lines.append(f"  [{idx}] {type(err).__name__}: {err}")
    ```

  **Must NOT do**:
  - 不添加设计文档以外的功能
  - 不创建 conftest.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 3 个小文件，代码直接从设计文档转录
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (only with T2 if T1 starts first)
  - **Blocks**: T2, T3, T4, T5, T6
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `basic_tool/crypto/exceptions.py` — 异常类组织模式（docstring + class 定义）
  - `basic_tool/crypto/config.py` — pydantic Config 类模式
  - `basic_tool/logger/config.py` — 另一个 pydantic Config 参考模式

  **API/Type References** (contracts to implement):
  - `doc/basic_tool_concurrency_design.md:69-106` — config.py 完整代码
  - `doc/basic_tool_concurrency_design.md:108-147` — exceptions.py 完整代码
  - `doc/basic_tool_concurrency_design.md:149-173` — strategy.py 完整代码

  **WHY Each Reference Matters**:
  - `crypto/exceptions.py` 和 `crypto/config.py`: 展示现有代码中异常类和配置类的标准模式，确保新代码风格一致
  - 设计文档的对应行号: 包含完整的实现代码，直接转录即可（注意 CompositeError.__str__ 的修复）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Types are importable
    Tool: Bash
    Preconditions: basic_tool/concurrency/ directory exists with 3 files
    Steps:
      1. Run: python -c "from basic_tool.concurrency.exceptions import CompositeError; from basic_tool.concurrency.strategy import ErrorStrategy; from basic_tool.concurrency.config import ConcurrencyConfig; print('OK')"
      2. Assert output contains "OK"
    Expected Result: Exit code 0, output "OK"
    Failure Indicators: ImportError, ModuleNotFoundError, exit code != 0
    Evidence: .sisyphus/evidence/task-1-import-check.txt

  Scenario: CompositeError __str__ works with mismatched lengths
    Tool: Bash
    Preconditions: exceptions.py created
    Steps:
      1. Run: python -c "from basic_tool.concurrency.exceptions import CompositeError; e = CompositeError([ValueError('a'), TypeError('b')]); print(str(e))"
      2. Assert output contains "2 task(s) failed"
    Expected Result: Exit code 0, shows error summary without crash
    Failure Indicators: IndexError, exit code != 0
    Evidence: .sisyphus/evidence/task-1-composite-error.txt

  Scenario: ErrorStrategy has all three values
    Tool: Bash
    Preconditions: strategy.py created
    Steps:
      1. Run: python -c "from basic_tool.concurrency.strategy import ErrorStrategy; assert ErrorStrategy.FAIL_FAST.value == 'fail_fast'; assert ErrorStrategy.COLLECT_ALL.value == 'collect_all'; assert ErrorStrategy.SKIP_FAILED.value == 'skip_failed'; print('OK')"
    Expected Result: Exit code 0, output "OK"
    Failure Indicators: AssertionError, AttributeError, exit code != 0
    Evidence: .sisyphus/evidence/task-1-strategy-check.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): add foundational types (config, exceptions, strategy)`
  - Files: `basic_tool/concurrency/config.py`, `basic_tool/concurrency/exceptions.py`, `basic_tool/concurrency/strategy.py`, `tests/concurrency/__init__.py`

- [x] 2. Write All 31 Test Cases (RED Phase)

  **What to do**:
  - Create `tests/concurrency/test_concurrency.py` with 31 test cases per design doc §7
  - **CRITICAL**: Because `gather_with_retry` API changed to factory functions, the related test cases (17-21) must use `Callable[[], Coroutine]` pattern:
    ```python
    # Instead of:
    # results = await gather_with_retry(fetch(u), ...)
    # Use:
    results = await gather_with_retry(lambda u=u: fetch(u), ...)
    ```
  - Test cases must cover ALL scenarios in design doc table (用例 1-31)
  - Tests should FAIL at this point (no implementation files yet for batch.py, pool.py, etc.)
  - Tests DO NOT need `@pytest.mark.asyncio` decorator (asyncio_mode = "auto")
  - **Test case list with exact descriptions**:
    1. `test_gather_with_limit_basic` — 返回值顺序与输入一致
    2. `test_gather_with_limit_concurrency_limit` — 实际并发数不超过 max_concurrency
    3. `test_gather_with_limit_fail_fast` — 第一个异常后取消其余任务
    4. `test_gather_with_limit_collect_all` — 等所有任务完成，抛出 CompositeError
    5. `test_gather_with_limit_skip_failed` — 跳过失败任务
    6. `test_gather_with_limit_empty` — 空输入返回空列表
    7. `test_gather_with_limit_progress_callback` — on_progress 被正确调用
    8. `test_gather_with_limit_invalid_concurrency` — max_concurrency < 1 抛 ValueError
    9. `test_run_in_batches_basic` — 分批执行，结果顺序正确
    10. `test_run_in_batches_inter_batch_delay` — 实际延迟存在（计时验证）
    11. `test_run_in_batches_empty` — 空输入返回空列表
    12. `test_run_in_batches_invalid_batch_size` — batch_size < 1 抛 ValueError
    13. `test_with_timeout_normal` — 正常完成返回结果
    14. `test_with_timeout_exceeds` — 超时抛 TimeoutError
    15. `test_with_timeout_invalid_timeout` — timeout <= 0 抛 ValueError
    16. `test_with_timeout_custom_message` — TimeoutError 包含自定义消息
    17. `test_gather_with_retry_first_success` — 首次成功不重试
    18. `test_gather_with_retry_retry_then_success` — 第 N 次尝试成功
    19. `test_gather_with_retry_all_fail` — 全部重试失败抛 CompositeError
    20. `test_gather_with_retry_non_retryable` — 非 retryable 类型不重试
    21. `test_gather_with_retry_skip_failed` — SKIP_FAILED 策略跳过失败
    22. `test_pool_basic` — run() 返回协程结果
    23. `test_pool_concurrency_limit` — 同时运行任务数不超过 max_concurrency
    24. `test_pool_stats` — stats 返回正确 total/used/waiting
    25. `test_pool_invalid_concurrency` — max_concurrency < 1 抛 ValueError
    26. `test_task_group_async_with` — 所有任务完成后退出
    27. `test_task_group_task_failure` — 任一任务失败取消其余
    28. `test_task_group_manual_wait` — wait() 返回所有结果
    29. `test_composite_error_attributes` — errors 和 failed_indices 正确
    30. `test_composite_error_str_format` — 包含错误数量和摘要
    31. `test_error_strategy_values` — 三个枚举值正确

  **Must NOT do**:
  - 不添加 `@pytest.mark.asyncio`
  - 不创建 conftest.py
  - 不跳过任何测试用例
  - 不 mock 外部服务（所有测试用纯 asyncio 原语）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 31 个测试用例，需要仔细对齐设计文档 + 适配工厂函数 API 变更
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1 for types to import)
  - **Parallel Group**: Wave 1 (sequential after T1)
  - **Blocks**: T3, T4, T5, T6 (tests validate their output)
  - **Blocked By**: T1

  **References**:

  **Pattern References** (existing tests to follow):
  - `tests/redis/test_cache.py` — 测试组织模式（class-based grouping 或 flat functions）
  - `tests/logger/test_logger.py` — 异步测试模式
  - `tests/crypto/test_password.py` — 另一个测试风格参考

  **API/Type References** (contracts being tested):
  - `doc/basic_tool_concurrency_design.md:1046-1081` — 完整测试用例表（31 个用例）
  - `doc/basic_tool_concurrency_design.md:786-849` — 公开 API 速查表（签名和返回值）

  **External References**:
  - `pytest-asyncio` auto mode: tests 目录下无需 `@pytest.mark.asyncio` 装饰器

  **WHY Each Reference Matters**:
  - 现有测试文件: 展示项目的测试风格（assert 风格、fixture 使用、组织方式）
  - 设计文档测试用例表: 每个测试的验证点和预期行为
  - API 速查表: 函数签名确保测试调用正确

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Test file exists and all 31 tests are collected
    Tool: Bash
    Preconditions: T1 complete (types exist for import)
    Steps:
      1. Run: pytest tests/concurrency/test_concurrency.py --collect-only -q
      2. Assert output contains "31 tests collected"
    Expected Result: 31 tests collected, 0 errors during collection
    Failure Indicators: Import errors, "0 tests collected", syntax errors
    Evidence: .sisyphus/evidence/task-2-test-collection.txt

  Scenario: All tests FAIL (RED phase verification)
    Tool: Bash
    Preconditions: T1 complete, no implementation files (pool.py, batch.py, etc.)
    Steps:
      1. Run: pytest tests/concurrency/test_concurrency.py -v --tb=no 2>&1 | head -50
      2. Assert: some tests show FAILED or ERROR (because implementations don't exist)
    Expected Result: NOT all pass — confirms RED phase. Some import errors expected.
    Failure Indicators: ALL 31 pass (means implementations already exist — wrong state)
    Evidence: .sisyphus/evidence/task-2-red-phase.txt
  ```

  **Commit**: YES
  - Message: `test(concurrency): add 31 test cases (RED phase)`
  - Files: `tests/concurrency/test_concurrency.py`

- [x] 3. Implement timeout.py

  **What to do**:
  - Create `basic_tool/concurrency/timeout.py` per design doc §3.6
  - Single function: `with_timeout(coro, timeout, *, message="") -> T`
  - Uses `asyncio.wait_for` internally
  - Converts `asyncio.TimeoutError` to built-in `TimeoutError` with custom message
  - File-level docstring + function docstring required

  **Must NOT do**:
  - 不添加设计文档以外的功能
  - 不使用 `asyncio.timeout()` (Python 3.11+) — 设计文档指定用 `asyncio.wait_for`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个函数，~30 行代码，直接转录
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T4, T5, T6)
  - **Blocks**: T7
  - **Blocked By**: T1

  **References**:

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:586-635` — timeout.py 完整代码

  **Pattern References**:
  - `basic_tool/logger/logger.py` — loguru logger 使用模式

  **WHY Each Reference Matters**:
  - 设计文档 §3.6: 包含完整的实现代码，直接转录
  - logger.py: 确认项目中 loguru 的使用方式（from loguru import logger）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: with_timeout passes for fast coroutine
    Tool: Bash
    Preconditions: timeout.py created, T1 complete
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.timeout import with_timeout
      async def main():
          result = await with_timeout(asyncio.sleep(0.01), timeout=5.0)
          print(f'result={result}')
      asyncio.run(main())"
      2. Assert output contains "result=None"
    Expected Result: Exit code 0, coroutine completes within timeout
    Failure Indicators: TimeoutError, exit code != 0
    Evidence: .sisyphus/evidence/task-3-timeout-pass.txt

  Scenario: with_timeout raises TimeoutError for slow coroutine
    Tool: Bash
    Preconditions: timeout.py created
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.timeout import with_timeout
      async def main():
          try:
              await with_timeout(asyncio.sleep(100), timeout=0.1, message='test timeout')
              print('NO ERROR')
          except TimeoutError as e:
              print(f'OK: {e}')
      asyncio.run(main())"
      2. Assert output contains "test timeout"
    Expected Result: Exit code 0, TimeoutError raised with custom message
    Failure Indicators: "NO ERROR" in output, exit code != 0
    Evidence: .sisyphus/evidence/task-3-timeout-fail.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): implement with_timeout`
  - Files: `basic_tool/concurrency/timeout.py`

- [x] 4. Implement pool.py

  **What to do**:
  - Create `basic_tool/concurrency/pool.py` per design doc §3.4
  - **BUG FIX**: Implement `_waiting` counter properly:
    ```python
    async def run(self, coro: Coroutine[Any, Any, T]) -> T:
        # Track waiting BEFORE acquiring semaphore
        async with self._lock:
            self._waiting += 1
        try:
            async with self._semaphore:
                # Acquired semaphore — no longer waiting, now running
                async with self._lock:
                    self._waiting -= 1
                    self._used += 1
                try:
                    logger.debug("pool task started | used={}/{}", self._used, self._max)
                    return await coro
                finally:
                    async with self._lock:
                        self._used -= 1
                    logger.debug("pool task finished | used={}/{}", self._used, self._max)
        except BaseException:
            # If we were waiting but got cancelled before acquiring
            async with self._lock:
                if self._waiting > 0:
                    self._waiting -= 1
            raise
    ```
  - Classes: `PoolStats` (dataclass) + `ConcurrencyPool`
  - File-level docstring + all method docstrings required

  **Must NOT do**:
  - 不使用 `_waiting` 死代码版本（设计文档原版）
  - 不添加设计文档以外的功能（如优先级队列）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个类，中等复杂度，设计文档有完整代码只需修改 _waiting 追踪逻辑
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T3, T5, T6)
  - **Blocks**: T7
  - **Blocked By**: T1

  **References**:

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:175-294` — pool.py 完整代码（需修改 _waiting 逻辑）

  **Pattern References**:
  - `basic_tool/redis/client/__init__.py` — 长生命周期对象模式（init/close/run）

  **WHY Each Reference Matters**:
  - 设计文档 §3.4: 包含 ConcurrencyPool 和 PoolStats 的完整代码基础，需在此基础上添加 _waiting 追踪
  - redis/client: 展示项目中长生命周期对象的生命周期管理模式

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Pool tracks waiting count correctly
    Tool: Bash
    Preconditions: pool.py created
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.pool import ConcurrencyPool
      async def main():
          pool = ConcurrencyPool(max_concurrency=1)
          stats = pool.stats
          print(f'init: total={stats.total}, used={stats.used}, waiting={stats.waiting}, available={stats.available}')
          assert stats.total == 1
          assert stats.used == 0
          assert stats.waiting == 0
          assert stats.available == 1
          print('Pool stats OK')
      asyncio.run(main())"
      2. Assert output contains "Pool stats OK"
    Expected Result: Exit code 0, initial stats correct
    Failure Indicators: AssertionError, AttributeError, exit code != 0
    Evidence: .sisyphus/evidence/task-4-pool-stats.txt

  Scenario: Pool run returns coroutine result
    Tool: Bash
    Preconditions: pool.py created
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.pool import ConcurrencyPool
      async def fetch(n):
          await asyncio.sleep(0.01)
          return n * 2
      async def main():
          pool = ConcurrencyPool(max_concurrency=5)
          result = await pool.run(fetch(21))
          assert result == 42, f'Expected 42, got {result}'
          print('OK')
      asyncio.run(main())"
      2. Assert output contains "OK"
    Expected Result: Exit code 0, result is 42
    Failure Indicators: AssertionError, exit code != 0
    Evidence: .sisyphus/evidence/task-4-pool-run.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): implement ConcurrencyPool with waiting tracking`
  - Files: `basic_tool/concurrency/pool.py`

- [x] 5. Implement batch.py

  **What to do**:
  - Create `basic_tool/concurrency/batch.py` per design doc §3.5
  - **BUG FIX**: `gather_with_retry` must use factory function signature:
    ```python
    async def gather_with_retry(
        *coro_factories: Callable[[], Coroutine[Any, Any, T]],
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_cap: float = 60.0,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
        strategy: ErrorStrategy = ErrorStrategy.COLLECT_ALL,
    ) -> list[T]:
    ```
  - In `_run_with_retry`, create fresh coroutine for each attempt:
    ```python
    async def _run_with_retry(idx: int, coro_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        last_error: BaseException | None = None
        for attempt in range(max_retries + 1):
            coro = coro_factory()  # Create fresh coroutine each attempt
            try:
                return await coro
            except retryable_exceptions as e:
                ...
    ```
  - `gather_with_limit` and `run_in_batches` remain unchanged from design doc
  - Private helpers: `_gather_fail_fast`, `_gather_collect_all`, `_gather_skip_failed`
  - File-level docstring + all function docstrings required
  - **NOTE**: `gather_with_limit` signature uses `*coros` (not factories). Only `gather_with_retry` uses factories.

  **Must NOT do**:
  - 不修改 `gather_with_limit` 或 `run_in_batches` 的签名（它们不涉及重试）
  - 不使用原始 `*coros` 签名在 `gather_with_retry`（会导致 re-await 崩溃）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 最复杂的文件，3 个公开函数 + 3 个私有辅助函数 + 需要修改 retry 的 API 设计
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T3, T4, T6)
  - **Blocks**: T7
  - **Blocked By**: T1 (needs exceptions.py, strategy.py)

  **References**:

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:296-584` — batch.py 完整代码（需修改 gather_with_retry 签名和内部逻辑）
  - `basic_tool/concurrency/exceptions.py` — CompositeError import
  - `basic_tool/concurrency/strategy.py` — ErrorStrategy import

  **Pattern References**:
  - `basic_tool/redis/decorators.py` — 复杂函数的 docstring 模式

  **WHY Each Reference Matters**:
  - 设计文档 §3.5: 包含所有 3 个函数的完整代码基础，gather_with_retry 需要改为工厂函数 API
  - exceptions.py + strategy.py: batch.py 的 import 依赖，确认正确的 import 路径

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: gather_with_limit basic execution preserves order
    Tool: Bash
    Preconditions: batch.py created, T1 complete
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.batch import gather_with_limit
      async def val(n):
          await asyncio.sleep(0.01)
          return n
      async def main():
          results = await gather_with_limit(val(1), val(2), val(3), max_concurrency=2)
          assert results == [1, 2, 3], f'Expected [1,2,3], got {results}'
          print('OK')
      asyncio.run(main())"
      2. Assert output contains "OK"
    Expected Result: Exit code 0, results in correct order
    Failure Indicators: AssertionError, wrong order, exit code != 0
    Evidence: .sisyphus/evidence/task-5-batch-basic.txt

  Scenario: gather_with_retry works with factory functions
    Tool: Bash
    Preconditions: batch.py created with factory API
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.batch import gather_with_retry
      call_count = 0
      async def flaky():
          global call_count
          call_count += 1
          if call_count < 3:
              raise ValueError('not yet')
          return 'success'
      async def main():
          results = await gather_with_retry(lambda: flaky(), max_retries=3, strategy='collect_all')
          # This will NOT work because strategy param is ErrorStrategy enum
          print('test needs adjustment')
      asyncio.run(main())" 2>&1 || true
      2. Verify gather_with_retry accepts factory functions without crash
    Expected Result: Factory function pattern works without RuntimeError
    Failure Indicators: "coroutine already awaited" RuntimeError
    Evidence: .sisyphus/evidence/task-5-retry-factory.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): implement batch execution with factory-based retry`
  - Files: `basic_tool/concurrency/batch.py`

- [x] 6. Implement task_group.py

  **What to do**:
  - Create `basic_tool/concurrency/task_group.py` per design doc §3.7
  - Class: `TaskGroup` — wraps `asyncio.TaskGroup` with better error aggregation
  - Supports `async with` pattern and manual `create()` + `wait()` pattern
  - `__aexit__` converts `BaseExceptionGroup` to `CompositeError`
  - File-level docstring + all method docstrings required

  **Must NOT do**:
  - 不使用 Python <3.11 兼容代码（项目已锁定 >=3.11）
  - 不添加设计文档以外的方法

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个类，设计文档有完整代码
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T3, T4, T5)
  - **Blocks**: T7
  - **Blocked By**: T1 (needs exceptions.py)

  **References**:

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:637-740` — task_group.py 完整代码

  **WHY Each Reference Matters**:
  - 设计文档 §3.7: 包含 TaskGroup 的完整实现代码，直接转录

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TaskGroup async with pattern works
    Tool: Bash
    Preconditions: task_group.py created
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.task_group import TaskGroup
      async def val(n):
          await asyncio.sleep(0.01)
          return n
      async def main():
          async with TaskGroup() as tg:
              t1 = tg.create(val(1))
              t2 = tg.create(val(2))
              t3 = tg.create(val(3))
          assert t1.result() == 1
          assert t2.result() == 2
          assert t3.result() == 3
          print('OK')
      asyncio.run(main())"
      2. Assert output contains "OK"
    Expected Result: Exit code 0, all results correct
    Failure Indicators: Exception, wrong results, exit code != 0
    Evidence: .sisyphus/evidence/task-6-taskgroup-basic.txt

  Scenario: TaskGroup converts errors to CompositeError
    Tool: Bash
    Preconditions: task_group.py created
    Steps:
      1. Run: python -c "
      import asyncio
      from basic_tool.concurrency.task_group import TaskGroup
      from basic_tool.concurrency.exceptions import CompositeError
      async def fail():
          raise ValueError('boom')
      async def main():
          try:
              async with TaskGroup() as tg:
                  tg.create(fail())
                  tg.create(asyncio.sleep(10))
          except CompositeError as e:
              print(f'OK: {repr(e)}')
              return
          print('NO ERROR RAISED')
      asyncio.run(main())"
      2. Assert output contains "OK" and "CompositeError"
    Expected Result: CompositeError raised with correct error info
    Failure Indicators: "NO ERROR RAISED", wrong exception type, exit code != 0
    Evidence: .sisyphus/evidence/task-6-taskgroup-error.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): implement TaskGroup`
  - Files: `basic_tool/concurrency/task_group.py`

- [x] 7. Wire Up __init__.py Exports

  **What to do**:
  - Create `basic_tool/concurrency/__init__.py` per design doc §3.8
  - Flat re-export of all public APIs
  - Module docstring describing the package
  - `__all__` list with all 10 public names
  - After this task, ALL 31 tests should transition from FAIL/ERROR to PASS (GREEN phase)

  **Must NOT do**:
  - 不导出私有符号（_gather_fail_fast 等）
  - 不添加设计文档未指定的导出

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个文件，~30 行代码
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (depends on ALL Wave 2 tasks)
  - **Blocks**: T8, F1-F4
  - **Blocked By**: T3, T4, T5, T6

  **References**:

  **Pattern References**:
  - `basic_tool/crypto/__init__.py` — __init__.py 组织模式（docstring → imports → __all__）
  - `basic_tool/redis/__init__.py` — 另一个 __init__.py 模式参考

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:742-783` — __init__.py 完整代码

  **WHY Each Reference Matters**:
  - 现有 __init__.py 文件: 确保新文件的 docstring/imports/__all__ 风格一致
  - 设计文档 §3.8: 包含完整的导出列表和 docstring

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All 31 tests pass (GREEN phase verification)
    Tool: Bash
    Preconditions: All source files created, __init__.py wired up
    Steps:
      1. Run: pytest tests/concurrency/test_concurrency.py -v
      2. Assert output shows "31 passed"
      3. Assert output shows "0 failed", "0 errors"
    Expected Result: 31 passed, 0 failed, 0 errors
    Failure Indicators: Any FAILED or ERROR in output
    Evidence: .sisyphus/evidence/task-7-green-phase.txt

  Scenario: All public names in __all__
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python -c "
      import basic_tool.concurrency
      expected = sorted(['CompositeError', 'ConcurrencyConfig', 'ConcurrencyPool', 'ErrorStrategy', 'PoolStats', 'TaskGroup', 'gather_with_limit', 'gather_with_retry', 'run_in_batches', 'with_timeout'])
      actual = sorted(basic_tool.concurrency.__all__)
      assert actual == expected, f'Missing: {set(expected)-set(actual)}, Extra: {set(actual)-set(expected)}'
      print('OK')"
      2. Assert output contains "OK"
    Expected Result: All 10 public names exported
    Failure Indicators: AssertionError, missing names
    Evidence: .sisyphus/evidence/task-7-exports.txt
  ```

  **Commit**: YES
  - Message: `feat(concurrency): wire up __init__.py exports`
  - Files: `basic_tool/concurrency/__init__.py`

- [x] 8. Write README.md

  **What to do**:
  - Create `basic_tool/concurrency/README.md` per project convention
  - Sections: 概述、依赖、模块结构、公开 API 文档（含签名和说明）、使用示例
  - Follow the pattern of `basic_tool/redis/README.md` and `basic_tool/crypto/README.md`
  - Include the 7 usage examples from design doc §5
  - **IMPORTANT**: Update `gather_with_retry` examples to use factory function pattern:
    ```python
    results = await gather_with_retry(
        *[lambda u=u: fetch_with_retry(u) for u in urls],
        max_retries=3,
    )
    ```

  **Must NOT do**:
  - 不写英文（项目 README 统一使用中文描述）
  - 不添加设计文档以外的 API 说明

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 文档任务，需要组织 API 参考和示例
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after T7)
  - **Blocks**: F1-F4
  - **Blocked By**: T7 (for accurate API list)

  **References**:

  **Pattern References**:
  - `basic_tool/redis/README.md` — README 结构模式（概述 → 依赖 → 结构 → API → 示例）
  - `basic_tool/crypto/README.md` — 另一个 README 参考

  **API/Type References**:
  - `doc/basic_tool_concurrency_design.md:786-1033` — API 速查表 + 使用示例

  **WHY Each Reference Matters**:
  - 现有 README 文件: 确保文档结构和风格与项目一致
  - 设计文档 §4-5: 所有 API 签名和使用示例的来源

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README exists and is non-empty
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: test -s basic_tool/concurrency/README.md && echo "EXISTS" || echo "MISSING"
      2. Run: wc -l basic_tool/concurrency/README.md
      3. Assert: EXISTS and line count > 50 (meaningful content)
    Expected Result: File exists with substantial content
    Failure Indicators: "MISSING", very small file (< 50 lines)
    Evidence: .sisyphus/evidence/task-8-readme.txt

  Scenario: README contains key API names
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: grep -c "gather_with_limit\|run_in_batches\|gather_with_retry\|with_timeout\|ConcurrencyPool\|TaskGroup\|CompositeError\|ErrorStrategy" basic_tool/concurrency/README.md
      2. Assert: count >= 8 (all major APIs documented)
    Expected Result: All major API names mentioned in README
    Failure Indicators: count < 8 (some APIs missing from docs)
    Evidence: .sisyphus/evidence/task-8-readme-apis.txt
  ```

  **Commit**: YES (groups with T9)
  - Message: `docs(concurrency): add README and update package docstring`
  - Files: `basic_tool/concurrency/README.md`, `basic_tool/__init__.py`

- [x] 9. Update basic_tool/__init__.py Docstring

  **What to do**:
  - Update `basic_tool/__init__.py` module docstring to add concurrency entry
  - Add a line: `- concurrency: 异步并发工具集，提供批量并发执行、并发限流、超时保护、重试和错误聚合能力`
  - Follow existing docstring pattern (other modules listed with Chinese descriptions)

  **Must NOT do**:
  - 不添加 import 语句（现有文件无任何 import）
  - 不修改现有条目

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单行修改
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T7, T8)
  - **Blocks**: F1-F4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/__init__.py` — 当前 docstring 格式（4 行模块列表）

  **WHY Each Reference Matters**:
  - 现有 __init__.py: 展示确切的 docstring 格式，新条目必须匹配风格

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Docstring contains concurrency entry
    Tool: Bash
    Preconditions: __init__.py updated
    Steps:
      1. Run: grep "concurrency" basic_tool/__init__.py
      2. Assert: line contains "concurrency" and a Chinese description
    Expected Result: Match found with concurrency description
    Failure Indicators: No match, exit code 1
    Evidence: .sisyphus/evidence/task-9-docstring.txt
  ```

  **Commit**: YES (groups with T8)
  - Message: `docs(concurrency): add README and update package docstring`
  - Files: `basic_tool/__init__.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, import module, run test). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/concurrency/ -v` + `pytest tests/ -v`. Review all files under `basic_tool/concurrency/` for: missing docstrings, `as any`/type ignores, empty catches, `print()` statements, unused imports, code not in design doc. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Tests [31/31 pass] | Regression [N/N pass] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean Python environment. Execute: (1) Import all public APIs. (2) Run a quick integration test using gather_with_limit + with_timeout. (3) Verify CompositeError contains correct errors and indices. (4) Verify ConcurrencyPool.stats reports correct waiting counts. (5) Verify gather_with_retry works with factory functions. Save evidence.
  Output: `Imports [OK/FAIL] | Integration [N/N pass] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual files. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Verify the two bug fixes are correctly applied. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Bug fixes [2/2 verified] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(concurrency): add foundational types (config, exceptions, strategy)` - basic_tool/concurrency/config.py, basic_tool/concurrency/exceptions.py, basic_tool/concurrency/strategy.py, tests/concurrency/__init__.py
- **T2**: `test(concurrency): add 31 test cases (RED phase)` - tests/concurrency/test_concurrency.py
- **T3**: `feat(concurrency): implement with_timeout` - basic_tool/concurrency/timeout.py
- **T4**: `feat(concurrency): implement ConcurrencyPool with waiting tracking` - basic_tool/concurrency/pool.py
- **T5**: `feat(concurrency): implement batch execution with factory-based retry` - basic_tool/concurrency/batch.py
- **T6**: `feat(concurrency): implement TaskGroup` - basic_tool/concurrency/task_group.py
- **T7**: `feat(concurrency): wire up __init__.py exports` - basic_tool/concurrency/__init__.py
- **T8+T9**: `docs(concurrency): add README and update package docstring` - basic_tool/concurrency/README.md, basic_tool/__init__.py

---

## Success Criteria

### Verification Commands
```bash
# 1. All concurrency tests pass
pytest tests/concurrency/ -v
# Expected: 31 passed, 0 failed

# 2. Full regression passes
pytest tests/ -v
# Expected: ALL passed, 0 failed

# 3. All public APIs importable
python -c "from basic_tool.concurrency import gather_with_limit, run_in_batches, gather_with_retry, with_timeout, ErrorStrategy, CompositeError, ConcurrencyPool, PoolStats, TaskGroup, ConcurrencyConfig"
# Expected: exit 0

# 4. __all__ completeness
python -c "import basic_tool.concurrency; print(sorted(basic_tool.concurrency.__all__))"
# Expected: ['CompositeError', 'ConcurrencyConfig', 'ConcurrencyPool', 'ErrorStrategy', 'PoolStats', 'TaskGroup', 'gather_with_limit', 'gather_with_retry', 'run_in_batches', 'with_timeout']

# 5. No new dependencies
grep "concurrency" pyproject.toml
# Expected: exit 1 (no matches)

# 6. README exists
test -s basic_tool/concurrency/README.md
# Expected: exit 0

# 7. Package docstring updated
grep "concurrency" basic_tool/__init__.py
# Expected: match found
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All 31 tests pass
- [ ] Full regression passes
- [ ] gather_with_retry uses Callable[[], Coroutine] factory API
- [ ] ConcurrencyPool.stats.waiting accurately tracks waiting count
