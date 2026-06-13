# basic_tool.storage 模块实现

## TL;DR

> **Quick Summary**: 在 basic_tool SDK 中新增 `storage` 子模块，提供统一文件存储抽象，第一期实现本地文件系统后端（LocalBackend），使用 aiofiles 异步 I/O。严格遵循设计文档，TDD 模式开发。
> 
> **Deliverables**:
> - 5 个源文件：config.py, backend.py, local.py, storage.py, __init__.py
> - 1 个 README.md 模块文档
> - 测试文件：tests/storage/conftest.py + tests/storage/test_storage.py（~20 个测试用例）
> - pyproject.toml 新增 aiofiles 依赖
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (dependency) → Task 2 (types+config) → Task 3/4 (tests) → Task 5/6/7 (impl) → Task 8 (README+exports) → Task 9 (integration QA)

---

## Context

### Original Request
按 `doc/basic_tool_storage_design.md` 设计文档实现 `basic_tool/storage` 模块，提供统一文件存储接口，第一期只实现本地文件系统后端。

### Interview Summary
**Key Discussions**:
- 设计文档为指导，允许微调（如安全修复、一致性改进）
- TDD 模式：先写测试再实现
- 需要 Agent QA 验证

**Research Findings**:
- basic_tool/ 有 7 个子模块，遵循一致的 flat __init__.py 导出模式
- 所有配置类用 Pydantic BaseModel（RedisConfig、IDConfig），LogConfig 是唯一例外用 dataclass
- 测试用 pytest + pytest-asyncio，asyncio_mode="auto"，class 分组 + 中文 docstring
- aiofiles 不在当前依赖中，需新增
- Python 版本要求 >=3.11

### Metis Review
**Identified Gaps** (addressed):
- **路径遍历漏洞**: `startswith()` 改为 `Path.is_relative_to()`（3.11+ 可用）
- **`list()` 不读 .ct sidecar**: 修改为读取，保持与 `info()` 一致
- **`metadata` 静默丢弃**: v1 限制，在 docstring 中明确标注
- **空 key 风险**: `put("")` 应拒绝，抛 ValueError
- **缺少边缘测试**: 补充覆盖覆盖写入、空数据、删除后读取、前缀为单文件等

---

## Work Objectives

### Core Objective
实现完整的 `basic_tool/storage` 模块，包含本地文件系统后端、配置模型、抽象基类、门面类和完整测试覆盖。

### Concrete Deliverables
- `basic_tool/storage/config.py` — StorageConfig 配置模型
- `basic_tool/storage/backend.py` — StorageBackend ABC + FileInfo
- `basic_tool/storage/local.py` — LocalBackend 本地文件系统实现
- `basic_tool/storage/storage.py` — Storage 门面类
- `basic_tool/storage/__init__.py` — 平铺导出
- `basic_tool/storage/README.md` — 模块文档
- `tests/storage/conftest.py` — 测试 fixtures
- `tests/storage/test_storage.py` — 完整测试
- `pyproject.toml` — 新增 aiofiles 依赖

### Definition of Done
- [x] `pytest tests/storage/test_storage.py -v` → ~20 tests passed
- [x] `pytest tests/ -v` → 全部通过，无回归
- [x] `python -c "from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo"` → OK
- [x] 所有源文件有模块级 docstring

### Must Have
- 完整的 StorageBackend ABC（init/close/put/get/delete/exists/info/list）
- LocalBackend 实现所有 ABC 方法
- Storage 门面类委托给后端
- 路径遍历安全防护（使用 `Path.is_relative_to()`）
- content_type 通过 .ct sidecar 文件持久化
- url() 方法生成访问 URL
- 设计文档中 14 个测试用例 + Metis 建议的 6 个额外边缘用例
- README.md 遵循现有模块文档格式
- 每个文件有模块级 docstring

### Must NOT Have (Guardrails)
- ❌ MinIO/S3 后端实现（只预留接口）
- ❌ 流式/分块 I/O（put/get 只接受/返回完整 bytes）
- ❌ 文件大小限制（由调用方控制）
- ❌ 自动 content-type 推断（调用方必须提供）
- ❌ 目录管理操作（mkdir/rmdir/list_dirs）
- ❌ 覆盖保护（put 静默覆盖）
- ❌ 校验和/ETag 支持
- ❌ 并发写入保护/锁
- ❌ 修改 `basic_tool/__init__.py`（顶层 docstring 未维护）
- ❌ AI slop：过度注释、过度抽象、不必要的泛型化
- ❌ 在 LocalBackend 中持久化 metadata（v1 是 no-op）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES（pytest + pytest-asyncio 已配置）
- **Automated tests**: TDD（先写测试，再实现）
- **Framework**: pytest + pytest-asyncio (asyncio_mode="auto")

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module/Library**: Use Bash — Import, call functions, compare output, run pytest
- **Config**: Use Bash — Verify Pydantic validation, default values

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - foundation):
├── Task 1: Add aiofiles dependency [quick]
├── Task 2: Implement config.py + backend.py (types & ABC) [quick]
└── Task 3: Write test file (TDD - RED phase) [unspecified-high]

Wave 2 (After Wave 1 - core implementation):
├── Task 4: Implement local.py (depends: 2, 3) [deep]
├── Task 5: Implement storage.py (depends: 2) [quick]
└── Task 6: Create __init__.py exports (depends: 4, 5) [quick]

Wave 3 (After Wave 2 - documentation + integration):
├── Task 7: Create README.md (depends: 6) [writing]
└── Task 8: Integration QA — full test suite + import verification (depends: 6, 1) [unspecified-high]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay

Critical Path: Task 1/2 → Task 3 → Task 4 → Task 6 → Task 8 → FINAL
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | - | 8 | 1 |
| 2 | - | 3, 4, 5 | 1 |
| 3 | 2 | 4 | 1 |
| 4 | 2, 3 | 6 | 2 |
| 5 | 2 | 6 | 2 |
| 6 | 4, 5 | 7, 8 | 2 |
| 7 | 6 | - | 3 |
| 8 | 6, 1 | - | 3 |

### Agent Dispatch Summary

- **Wave 1**: **3 tasks** — T1 → `quick`, T2 → `quick`, T3 → `unspecified-high`
- **Wave 2**: **3 tasks** — T4 → `deep`, T5 → `quick`, T6 → `quick`
- **Wave 3**: **2 tasks** — T7 → `writing`, T8 → `unspecified-high`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Add aiofiles dependency to pyproject.toml

  **What to do**:
  - 在 `pyproject.toml` 的 `dependencies` 列表中新增 `"aiofiles>=23.0.0"`
  - 运行 `pip install -e ".[dev]"` 验证安装成功
  - 运行 `python -c "import aiofiles; print(aiofiles.__version__)"` 确认可用

  **Must NOT do**:
  - 不要修改其他依赖项
  - 不要修改 dev dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件单行修改，极简任务
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Task 8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pyproject.toml:11-19` — 现有 dependencies 列表格式，新依赖加在末尾

  **External References**:
  - aiofiles PyPI: 异步文件 I/O 库，纯 Python，无传递依赖

  **WHY Each Reference Matters**:
  - `pyproject.toml` 的格式：需要保持现有的引号风格、版本约束格式

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: aiofiles dependency installed and importable
    Tool: Bash
    Preconditions: pyproject.toml updated
    Steps:
      1. Run: pip install -e ".[dev]"
      2. Run: python -c "import aiofiles; print(aiofiles.__version__)"
      3. Assert output contains version string >= 23.0
    Expected Result: Version string printed, exit code 0
    Failure Indicators: ImportError, exit code non-zero
    Evidence: .sisyphus/evidence/task-1-aiofiles-install.txt

  Scenario: pyproject.toml syntax valid
    Tool: Bash
    Preconditions: pyproject.toml modified
    Steps:
      1. Run: python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
    Expected Result: No exception, exit code 0
    Failure Indicators: tomllib.TOMLDecodeError
    Evidence: .sisyphus/evidence/task-1-toml-valid.txt
  ```

  **Commit**: NO (groups with all tasks in single commit)

- [x] 2. Implement config.py and backend.py (types & ABC)

  **What to do**:
  - 创建 `basic_tool/storage/config.py`：StorageConfig（Pydantic BaseModel），字段：backend、base_dir、url_prefix、auto_create_dir，以及注释掉的 MinIO 预留字段
  - 创建 `basic_tool/storage/backend.py`：FileInfo（__slots__ 类）和 StorageBackend（ABC），包含 init/close/put/get/delete/exists/info/list 抽象方法
  - 每个文件必须有模块级 docstring
  - 每个类和方法必须有 docstring（参数、返回值、异常）
  - 创建 `basic_tool/storage/` 目录（如果不存在）

  **Must NOT do**:
  - 不要实现 LocalBackend（Task 4）
  - 不要实现 Storage 门面类（Task 5）
  - 不要持久化 metadata（v1 no-op，接口预留即可）
  - 不要创建 __init__.py（Task 6）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 两个纯定义文件，无复杂逻辑，按设计文档实现
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/redis/config.py` — Pydantic BaseModel 配置类模式，docstring 格式
  - `basic_tool/id_generator/config.py` — 另一个 Pydantic BaseModel 配置类示例

  **API/Type References**:
  - `doc/basic_tool_storage_design.md:52-78` — StorageConfig 完整定义（字段名、类型、默认值、注释）
  - `doc/basic_tool_storage_design.md:84-223` — FileInfo + StorageBackend ABC 完整定义

  **External References**:
  - Python abc 模块：ABC + abstractmethod 标准用法

  **WHY Each Reference Matters**:
  - `redis/config.py`：复制 Pydantic BaseModel 的 import 风格和字段定义格式
  - 设计文档第 52-78 行：StorageConfig 的字段名和默认值必须精确匹配
  - 设计文档第 84-223 行：ABC 方法的签名、参数、返回值、异常声明必须精确匹配

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Files created with correct structure
    Tool: Bash
    Preconditions: basic_tool/storage/ directory created
    Steps:
      1. Run: test -f basic_tool/storage/config.py && echo "config.py exists"
      2. Run: test -f basic_tool/storage/backend.py && echo "backend.py exists"
      3. Run: python -c "from basic_tool.storage.config import StorageConfig; c = StorageConfig(); print(c.backend, c.base_dir)"
      4. Assert output: "local ./uploads"
    Expected Result: Both files exist, StorageConfig has correct defaults
    Failure Indicators: File not found, import error, wrong defaults
    Evidence: .sisyphus/evidence/task-2-files-exist.txt

  Scenario: StorageBackend is abstract and cannot be instantiated
    Tool: Bash
    Preconditions: backend.py created
    Steps:
      1. Run: python -c "from basic_tool.storage.backend import StorageBackend; StorageBackend()" 2>&1 || true
      2. Assert output contains "abstract" or "instantiate"
    Expected Result: TypeError about abstract class
    Failure Indicators: No error (class instantiated successfully = ABC broken)
    Evidence: .sisyphus/evidence/task-2-abstract-check.txt

  Scenario: Docstrings present on all public classes and methods
    Tool: Bash
    Preconditions: Both files created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.config import StorageConfig
         from basic_tool.storage.backend import FileInfo, StorageBackend
         assert StorageConfig.__doc__, 'StorageConfig missing docstring'
         assert FileInfo.__doc__, 'FileInfo missing docstring'
         assert StorageBackend.__doc__, 'StorageBackend missing docstring'
         for name in ['init','close','put','get','delete','exists','info','list']:
             m = getattr(StorageBackend, name, None)
             assert m and m.__doc__, f'{name} missing docstring'
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: AssertionError on any docstring check
    Evidence: .sisyphus/evidence/task-2-docstrings.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 3. Write complete test file (TDD - RED phase)

  **What to do**:
  - 创建 `tests/storage/` 目录
  - 创建 `tests/storage/conftest.py`：定义 `storage` fixture（使用 `tmp_path` 创建临时 Storage 实例）和 `storage_config` fixture
  - 创建 `tests/storage/test_storage.py`：编写设计文档中的 14 个测试用例 + Metis 建议的 6 个额外边缘用例，共 ~20 个测试
  - 所有测试用例使用 class 分组，中文 docstring
  - **此时所有测试应该 FAIL**（因为实现尚未编写）— 这是 TDD RED 阶段
  - 运行 `pytest tests/storage/test_storage.py -v` 确认测试被发现但失败

  **测试用例列表**（设计文档 14 个 + 额外 6 个）：
  
  设计文档测试（14）：
  1. test_init_creates_dir — auto_create_dir=True 自动创建目录
  2. test_init_missing_dir_raises — auto_create_dir=False 目录不存在抛异常
  3. test_put_and_get — 写入后读取内容一致
  4. test_put_with_content_type — content_type 正确存储和读取
  5. test_delete — 删除后文件不存在
  6. test_delete_not_found — 删除不存在文件抛 FileNotFoundError
  7. test_exists — 存在返回 True，不存在返回 False
  8. test_info — 返回正确的 size、content_type、last_modified
  9. test_list — 列出指定前缀下的文件
  10. test_list_empty_prefix — 前缀为空列出所有文件
  11. test_list_nonexistent_prefix — 不存在前缀返回空列表
  12. test_url — url() 正确拼接 url_prefix 和 key
  13. test_url_no_prefix — url_prefix 为空返回 key 本身
  14. test_path_traversal — key 包含 ../ 抛 ValueError

  额外边缘测试（6）：
  15. test_put_overwrite — 覆盖已存在文件，数据为新内容
  16. test_put_empty_data — put(key, b"") 创建 0 字节文件
  17. test_get_after_delete_raises — 删除后 get() 抛 FileNotFoundError
  18. test_list_with_ct_sidecar — list() 返回正确的 content_type（从 .ct 读取）
  19. test_key_with_leading_slash — "/etc/passwd" 被路径遍历检查拦截
  20. test_delete_removes_ct_file — delete 同时清理 .ct sidecar

  **Must NOT do**:
  - 不要实现任何被测代码（只写测试）
  - 不要修改 tests/conftest.py（全局 fixtures 与 storage 无关）
  - 不要创建 tests/storage/__init__.py（查看现有 tests/redis/ 也没有）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: ~20 个测试用例编写，需要仔细覆盖各种边缘场景
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 4
  - **Blocked By**: Task 2（需要知道 config 和 backend 的精确接口）

  **References**:

  **Pattern References**:
  - `tests/redis/test_client.py` — 异步测试 class 分组模式，中文 docstring 格式
  - `tests/id_generator/test_generator.py` — 更简单的测试示例
  - `tests/conftest.py` — fixture 定义模式（但 storage 需要自己的 conftest）

  **API/Type References**:
  - `doc/basic_tool_storage_design.md:689-704` — 设计文档中的 14 个测试用例定义
  - `basic_tool/storage/config.py`（Task 2 产出）— StorageConfig 字段和默认值
  - `basic_tool/storage/backend.py`（Task 2 产出）— StorageBackend ABC 接口签名

  **Test References**:
  - `tests/conftest.py` — pytest fixture 定义模式（async fixture 用 `@pytest.fixture`）

  **WHY Each Reference Matters**:
  - `test_client.py`：复制 class 分组结构、async def test、assert 风格
  - 设计文档测试列表：14 个测试用例是硬性要求
  - Task 2 产出：测试必须精确匹配接口签名

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Test file created with correct number of tests
    Tool: Bash
    Preconditions: Task 2 completed (config.py + backend.py exist)
    Steps:
      1. Run: test -f tests/storage/test_storage.py && echo "exists"
      2. Run: test -f tests/storage/conftest.py && echo "conftest exists"
      3. Run: grep -c "async def test_\|def test_" tests/storage/test_storage.py
      4. Assert count >= 20
    Expected Result: Both files exist, at least 20 test functions
    Failure Indicators: File missing, fewer than 20 tests
    Evidence: .sisyphus/evidence/task-3-test-count.txt

  Scenario: Tests discovered by pytest but fail (TDD RED phase)
    Tool: Bash
    Preconditions: Tests written, implementation NOT yet done
    Steps:
      1. Run: pytest tests/storage/test_storage.py --collect-only 2>&1
      2. Assert output shows collected tests (>= 20)
      3. Run: pytest tests/storage/test_storage.py -v 2>&1 | head -5
      4. Assert tests fail (import error or assertion error)
    Expected Result: Tests collected, all FAIL (RED phase)
    Failure Indicators: Tests pass unexpectedly (wrong test) or 0 collected (syntax error)
    Evidence: .sisyphus/evidence/task-3-red-phase.txt

  Scenario: Tests use class grouping and Chinese docstrings
    Tool: Bash
    Preconditions: test_storage.py created
    Steps:
      1. Run: grep -c "^class Test" tests/storage/test_storage.py
      2. Assert count >= 3 (multiple test classes)
      3. Run: grep -c '"""' tests/storage/test_storage.py
      4. Assert count >= 20 (docstrings on tests)
    Expected Result: Multiple test classes, docstrings present
    Failure Indicators: Single class or no docstrings
    Evidence: .sisyphus/evidence/task-3-test-structure.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 4. Implement local.py (LocalBackend)

  **What to do**:
  - 创建 `basic_tool/storage/local.py`：LocalBackend 类，继承 StorageBackend
  - 实现 `_resolve()` 安全路径解析（使用 `Path.is_relative_to()`，不用 `startswith()`）
  - 实现 `init()` — 创建 base_dir 目录（如 auto_create_dir=True）
  - 实现 `close()` — 空操作
  - 实现 `put()` — 异步写入文件，存储 content_type 到 .ct sidecar
  - 实现 `get()` — 异步读取文件，不存在抛 FileNotFoundError
  - 实现 `delete()` — 删除文件 + .ct sidecar
  - 实现 `exists()` — 检查文件存在
  - 实现 `info()` — 返回 FileInfo，从 .ct sidecar 读取 content_type
  - 实现 `list()` — 递归列出文件，**也读取 .ct sidecar 获取 content_type**
  - 验证 key 非空（空 key 抛 ValueError）
  - 每个方法有完整 docstring

  **Must NOT do**:
  - 不要用 `str.startswith()` 做路径遍历检查（必须用 `Path.is_relative_to()`）
  - 不要持久化 metadata（v1 no-op）
  - 不要添加流式 I/O
  - 不要添加文件大小检查
  - 不要修改 config.py 或 backend.py

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心实现文件，涉及安全检查、异步 I/O、sidecar 文件管理，需要仔细处理
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 Task 5 可并行）
  - **Parallel Group**: Wave 2 (with Tasks 5)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 2, 3

  **References**:

  **Pattern References**:
  - `basic_tool/redis/client/__init__.py` — init/close 生命周期模式，loguru 日志使用

  **API/Type References**:
  - `doc/basic_tool_storage_design.md:229-369` — LocalBackend 完整实现代码（参考，需微调）
  - `basic_tool/storage/backend.py`（Task 2）— StorageBackend ABC 接口签名

  **External References**:
  - Python pathlib.Path.is_relative_to(): 3.9+ 安全路径检查
  - aiofiles 文档：异步文件 I/O

  **WHY Each Reference Matters**:
  - 设计文档第 229-369 行：实现逻辑参考，但需修改 `_resolve()` 用 `is_relative_to()`
  - backend.py：必须精确实现所有 abstract 方法
  - `is_relative_to()`：替代不安全的 `startswith()` 检查

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: LocalBackend implements all abstract methods
    Tool: Bash
    Preconditions: backend.py and local.py created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.local import LocalBackend
         lb = LocalBackend('/tmp/test_storage')
         # Verify no abstract methods remain
         for name in ['init','close','put','get','delete','exists','info','list']:
             assert hasattr(lb, name), f'{name} not implemented'
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: Abstract method error or missing method
    Evidence: .sisyphus/evidence/task-4-abstract-impl.txt

  Scenario: Path traversal is blocked with is_relative_to
    Tool: Bash
    Preconditions: local.py created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.local import LocalBackend
         lb = LocalBackend('/tmp/safe_dir')
         import asyncio
         try:
             asyncio.run(lb._resolve('../../../etc/passwd'))
             print('FAIL: path traversal not caught')
         except ValueError as e:
             print(f'OK: {e}')
         "
    Expected Result: ValueError raised with path traversal message
    Failure Indicators: No exception (path traversal allowed)
    Evidence: .sisyphus/evidence/task-4-path-traversal.txt

  Scenario: Key with leading slash blocked
    Tool: Bash
    Preconditions: local.py created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.local import LocalBackend
         lb = LocalBackend('/tmp/safe_dir')
         import asyncio
         try:
             asyncio.run(lb._resolve('/etc/passwd'))
             print('FAIL: absolute path not caught')
         except ValueError as e:
             print(f'OK: {e}')
         "
    Expected Result: ValueError raised
    Failure Indicators: No exception
    Evidence: .sisyphus/evidence/task-4-leading-slash.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 5. Implement storage.py (Storage facade)

  **What to do**:
  - 创建 `basic_tool/storage/storage.py`：Storage 门面类
  - 实现 `_create_backend()` — 根据 config.backend 创建后端实例（lazy import）
  - 实现 `init()` / `close()` — 生命周期管理
  - 实现 `backend` property — 检查 _initialized 后返回后端
  - 实现所有委托方法：put/get/delete/exists/info/list
  - 实现 `url()` — 拼接 url_prefix 和 key
  - 每个方法有完整 docstring

  **Must NOT do**:
  - 不要在 put/get 等方法中加 init guard（v1 简化）
  - 不要实现 MinIO 后端创建分支
  - 不要修改 config.py 或 backend.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 门面类主要是委托逻辑，按设计文档实现即可
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 Task 4 可并行）
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:

  **API/Type References**:
  - `doc/basic_tool_storage_design.md:376-524` — Storage 门面类完整定义
  - `basic_tool/storage/backend.py`（Task 2）— 委托目标接口
  - `basic_tool/storage/config.py`（Task 2）— StorageConfig 字段

  **Pattern References**:
  - `basic_tool/redis/client/__init__.py` — Cache 类的 init/close 生命周期 + Mixin 组合模式

  **WHY Each Reference Matters**:
  - 设计文档第 376-524 行：Storage 类的完整实现参考
  - backend.py：确保委托方法的签名与 ABC 一致
  - config.py：url() 方法需要用到 url_prefix

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Storage facade creates correct backend
    Tool: Bash
    Preconditions: config.py, backend.py, storage.py, local.py exist
    Steps:
      1. Run: python -c "
         import asyncio
         from basic_tool.storage.storage import Storage
         from basic_tool.storage.config import StorageConfig
         s = Storage(StorageConfig(base_dir='/tmp/test_facade'))
         assert s._config.backend == 'local'
         assert 'LocalBackend' in type(s._backend).__name__
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: Wrong backend type or import error

  Scenario: Storage unsupported backend raises ValueError
    Tool: Bash
    Preconditions: storage.py created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.storage import Storage
         from basic_tool.storage.config import StorageConfig
         try:
             Storage(StorageConfig(backend='minio'))
             print('FAIL: no error for unsupported backend')
         except ValueError as e:
             print(f'OK: {e}')
         "
    Expected Result: ValueError about unsupported backend
    Failure Indicators: No exception raised
    Evidence: .sisyphus/evidence/task-5-backend-validation.txt

  Scenario: url() concatenation correct
    Tool: Bash
    Preconditions: storage.py created
    Steps:
      1. Run: python -c "
         from basic_tool.storage.storage import Storage
         from basic_tool.storage.config import StorageConfig
         s1 = Storage(StorageConfig(url_prefix='http://cdn.example.com'))
         assert s1.url('photos/img.jpg') == 'http://cdn.example.com/photos/img.jpg'
         s2 = Storage(StorageConfig(url_prefix=''))
         assert s2.url('photos/img.jpg') == 'photos/img.jpg'
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: AssertionError on URL format
    Evidence: .sisyphus/evidence/task-5-url.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 6. Create __init__.py exports

  **What to do**:
  - 创建 `basic_tool/storage/__init__.py`
  - 模块级 docstring（描述 storage 模块 + 简要使用示例）
  - 平铺导出：StorageConfig, Storage, StorageBackend, FileInfo
  - 定义 `__all__` 列表
  - 遵循 `basic_tool/redis/__init__.py` 的格式

  **Must NOT do**:
  - 不要导出 LocalBackend（内部实现细节）
  - 不要修改 basic_tool/__init__.py（顶层 docstring 未维护）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件，按现有模式复制即可
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Tasks 4, 5)
  - **Blocks**: Tasks 7, 8
  - **Blocked By**: Tasks 4, 5

  **References**:

  **Pattern References**:
  - `basic_tool/redis/__init__.py` — canonical flat export pattern with __all__
  - `basic_tool/logger/__init__.py` — simpler export pattern example
  - `basic_tool/id_generator/__init__.py` — another export pattern

  **WHY Each Reference Matters**:
  - `redis/__init__.py`：最完整的导出模式，包含 docstring + flat imports + __all__
  - 需要精确复制其格式

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All public exports importable from basic_tool.storage
    Tool: Bash
    Preconditions: All source files created
    Steps:
      1. Run: python -c "
         from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-6-imports.txt

  Scenario: __all__ matches actual exports
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python -c "
         import basic_tool.storage as s
         assert set(s.__all__) == {'Storage', 'StorageConfig', 'StorageBackend', 'FileInfo'}
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-6-all.txt

  Scenario: Module docstring present
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python -c "
         import basic_tool.storage
         assert basic_tool.storage.__doc__
         assert len(basic_tool.storage.__doc__) > 50
         print('OK')
         "
    Expected Result: "OK" printed
    Evidence: .sisyphus/evidence/task-6-docstring.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 7. Create README.md module documentation

  **What to do**:
  - 创建 `basic_tool/storage/README.md`
  - 遵循现有模块 README 格式（参考 `basic_tool/redis/README.md` 或 `basic_tool/id_generator/README.md`）
  - 必须包含以下章节：标题、概述、依赖、模块结构、API 文档（每个公共类/方法）、使用示例
  - API 文档中每个方法需要：签名、参数说明、返回值、异常
  - 使用示例要可运行（与设计文档第五章一致）

  **Must NOT do**:
  - 不要提及 .ct sidecar 机制（内部实现细节）
  - 不要写 MinIO 使用示例（未实现）
  - 不要过度文档化私有方法

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档任务，需要清晰的技术写作
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 6

  **References**:

  **Pattern References**:
  - `basic_tool/redis/README.md` — canonical README 格式（最完整的示例）
  - `basic_tool/id_generator/README.md` — 较简单的 README 格式

  **API/Type References**:
  - `doc/basic_tool_storage_design.md:545-672` — API 速查表和使用示例
  - `basic_tool/storage/__init__.py`（Task 6）— 导出的公共 API 列表

  **WHY Each Reference Matters**:
  - `redis/README.md`：必须匹配的格式结构
  - 设计文档 API 速查表：准确的 API 签名和描述

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README has required sections
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: grep -q "## 依赖" basic_tool/storage/README.md
      2. Run: grep -q "## 模块结构\|## 模块" basic_tool/storage/README.md
      3. Run: grep -q "## API" basic_tool/storage/README.md
      4. Run: grep -q "## 使用示例\|## 使用" basic_tool/storage/README.md
      5. All exit codes must be 0
    Expected Result: All sections found
    Failure Indicators: Any grep exits non-zero
    Evidence: .sisyphus/evidence/task-7-readme-sections.txt

  Scenario: README documents all public APIs
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: grep -c "Storage\b" basic_tool/storage/README.md (>= 5 occurrences)
      2. Run: grep -c "StorageConfig" basic_tool/storage/README.md (>= 2)
      3. Run: grep -c "put\|get\|delete\|exists\|info\|list\|url" basic_tool/storage/README.md (>= 14)
    Expected Result: All public APIs documented
    Failure Indicators: Missing API documentation
    Evidence: .sisyphus/evidence/task-7-readme-api.txt
  ```

  **Commit**: NO (groups with all tasks)

- [x] 8. Integration QA — full test suite + import verification

  **What to do**:
  - 运行 `pytest tests/storage/test_storage.py -v` — 所有 ~20 个测试必须通过
  - 运行 `pytest tests/ -v` — 完整测试套件，无回归
  - 运行 `python -c "from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo"` — 导入验证
  - 运行 docstring 检查：每个 .py 文件有模块级 docstring
  - 验证路径遍历安全性测试通过
  - 如果测试失败，修复实现代码直到通过

  **Must NOT do**:
  - 不要修改测试用例来适配错误实现（修复实现，不修复测试）
  - 不要跳过失败的测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要运行完整测试套件，可能需要调试和修复
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Task 6, with Task 7)
  - **Blocks**: FINAL wave
  - **Blocked By**: Tasks 1, 6

  **References**:

  **Test References**:
  - `tests/storage/test_storage.py`（Task 3）— 测试用例
  - `tests/storage/conftest.py`（Task 3）— 测试 fixtures

  **API/Type References**:
  - `basic_tool/storage/` — 所有实现文件

  **WHY Each Reference Matters**:
  - 测试文件：验收标准定义
  - 实现文件：如果测试失败需要检查和修复

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All storage tests pass
    Tool: Bash
    Preconditions: All source files and tests complete
    Steps:
      1. Run: pytest tests/storage/test_storage.py -v 2>&1
      2. Assert all tests pass (look for "passed" and no "failed")
      3. Assert test count >= 20
    Expected Result: >= 20 passed, 0 failed
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-8-storage-tests.txt

  Scenario: Full regression suite passes
    Tool: Bash
    Preconditions: All changes complete
    Steps:
      1. Run: pytest tests/ -v 2>&1
      2. Assert all tests pass
    Expected Result: ALL passed, 0 failed
    Failure Indicators: Any regression in existing tests
    Evidence: .sisyphus/evidence/task-8-regression.txt

  Scenario: Import path works
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python -c "from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo; print('OK')"
    Expected Result: "OK" printed
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-8-import.txt

  Scenario: All files have docstrings
    Tool: Bash
    Preconditions: All source files created
    Steps:
      1. Run: python -c "
         for name in ['config', 'backend', 'local', 'storage']:
             m = __import__(f'basic_tool.storage.{name}', fromlist=[name])
             assert m.__doc__, f'{name}.py missing docstring'
         print('OK')
         "
    Expected Result: "OK" printed
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-8-docstrings.txt

  Scenario: Path traversal security test passes
    Tool: Bash
    Preconditions: Tests complete
    Steps:
      1. Run: pytest tests/storage/test_storage.py -k "test_path_traversal" -v 2>&1
      2. Assert PASSED
    Expected Result: Path traversal test passes
    Failure Indicators: FAILED (security vulnerability)
    Evidence: .sisyphus/evidence/task-8-security.txt
  ```

  **Commit**: YES
  - Message: `feat(storage): add file storage module with local backend`
  - Files: All new files + pyproject.toml
  - Pre-commit: `pytest tests/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v` + check all source files for: missing docstrings, `as any`/type issues, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Single commit**: `feat(storage): add file storage module with local backend`
  - Files: All new files + pyproject.toml
  - Pre-commit: `pytest tests/ -v`

---

## Success Criteria

### Verification Commands
```bash
pytest tests/storage/test_storage.py -v   # Expected: ~20 passed, 0 failed
pytest tests/ -v                           # Expected: ALL passed, no regression
python -c "from basic_tool.storage import Storage, StorageConfig, StorageBackend, FileInfo; print('OK')"  # Expected: OK
pip install -e ".[dev]"                    # Expected: success
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] Every .py file has module-level docstring
- [x] README.md follows existing module README format
- [x] Path traversal security check uses `Path.is_relative_to()`
