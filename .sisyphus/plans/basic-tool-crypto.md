# basic_tool.crypto 模块实现

## TL;DR

> **Quick Summary**: 按照设计文档 `doc/basic_tool_crypto_design.md` 实现 `basic_tool/crypto` 子模块，提供 Argon2id 密码哈希、Fernet 对称加密、HMAC-SHA256 签名、HKDF/PBKDF2 密钥派生、CSPRNG token 生成等密码学能力。TDD 方式：先写测试 → 确认失败 → 实现 → 确认通过。
> 
> **Deliverables**:
> - `basic_tool/crypto/` 子模块（7 个源文件）
> - `tests/crypto/` 测试目录（4 个测试文件，23+ 测试用例）
> - `basic_tool/crypto/README.md` 模块文档
> - `pyproject.toml` 新增依赖
> - `basic_tool/__init__.py` 更新模块描述
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (deps) → Task 2 (config/exceptions) → Task 3-6 (TDD parallel) → Task 7 (init) → Task 8 (README) → Final Verification

---

## Context

### Original Request
按照 `doc/basic_tool_crypto_design.md` 设计文档实现 `basic_tool.crypto` 模块。

### Interview Summary
**Key Discussions**:
- 用户提供了完整的设计文档（含所有源代码、测试用例、执行顺序）
- 测试策略：TDD（测试先行）
- 审查策略：高精度模式（Metis + Momus 双重审查）

**Research Findings**:
- `basic_tool/__init__.py` 是纯 docstring（无 import 语句），只需更新描述文字
- `cryptography` 已通过 `python-jose[cryptography]` 传递安装（v46.0.5），但仍需显式声明为直接依赖
- `argon2-cffi` 尚未安装，需要 `uv sync` 安装
- Argon2id 默认参数（64MB 内存）会导致测试慢，需在测试中使用低开销配置
- TTL 过期测试需要确定性策略（不能用 freezegun，不在 dev deps 中）

### Metis Review
**Identified Gaps** (addressed):
- `basic_tool/__init__.py` 不应添加 import 语句（只更新 docstring）→ 已修正设计文档中 "新增 from basic_tool import crypto" 的说法
- 测试中需使用低开销 CryptoConfig（`memory_cost=1024, time_cost=1, parallelism=1`）→ 已加入任务描述
- TTL 过期测试策略：用 `time.sleep(1.1)` + `ttl=1` 方式 → 已加入测试场景
- 补充缺失测试：异常继承层次、`sha256_hex` 别名、`generate_hex_token` 唯一性、空输入边界

---

## Work Objectives

### Core Objective
在 `basic_tool` SDK 中新增 `crypto` 子模块，封装常用密码学原语，安全默认、防呆设计。

### Concrete Deliverables
- `basic_tool/crypto/__init__.py` — 平铺导出
- `basic_tool/crypto/config.py` — CryptoConfig 配置模型
- `basic_tool/crypto/exceptions.py` — 统一异常类型
- `basic_tool/crypto/password.py` — Argon2id 密码哈希 + token 生成
- `basic_tool/crypto/encrypt.py` — Fernet 对称加密
- `basic_tool/crypto/sign.py` — HMAC-SHA256 签名 + SHA-256 哈希
- `basic_tool/crypto/kdf.py` — HKDF / PBKDF2 密钥派生
- `basic_tool/crypto/README.md` — 模块文档
- `tests/crypto/test_password.py` — 密码哈希测试（用例 1-9 + 补充）
- `tests/crypto/test_encrypt.py` — 加密测试（用例 10-15 + 补充）
- `tests/crypto/test_sign.py` — 签名测试（用例 16-19 + 补充）
- `tests/crypto/test_kdf.py` — 密钥派生测试（用例 20-22 + 补充）
- `pyproject.toml` — 新增 `argon2-cffi` + `cryptography` 依赖
- `basic_tool/__init__.py` — 更新模块描述

### Definition of Done
- [ ] `pytest tests/crypto/ -v` 全部通过（23+ 测试用例）
- [ ] `python -c "from basic_tool.crypto import hash_password, verify_password, needs_rehash, generate_token, generate_hex_token, generate_fernet_key, encrypt, decrypt, encrypt_str, decrypt_str, sign, verify, sha256, derive_key_hkdf, derive_key_pbkdf2, CryptoConfig, CryptoError, DecryptionError, SignatureVerificationError, InvalidKeyError"` 无报错
- [ ] `uv sync` 无报错

### Must Have
- 所有源代码严格按设计文档实现（代码已在文档中完整给出）
- 所有 23 个测试用例按设计文档通过
- 每个公开函数都有完整 docstring（Args/Returns/Raises）
- 异常继承体系：CryptoError → DecryptionError / SignatureVerificationError / InvalidKeyError
- 安全默认参数遵循 OWASP 建议

### Must NOT Have (Guardrails)
- **不修改 `basic_tool/__init__.py` 添加 import 语句** — 只更新 docstring 描述行
- **不修改 `basic_tool/` 下任何其他子模块**
- **不添加 `freezegun` 或其他新测试依赖**
- **不重命名、重排或 "改进" 设计文档中的任何 API**
- **不在源代码中添加设计文档未提及的功能或参数验证**
- **不创建 `tests/crypto/conftest.py`** — 无共享 fixture 需求（各测试独立配置）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio in dev deps)
- **Automated tests**: TDD (tests first)
- **Framework**: pytest
- **TDD Flow**: Write test file → confirm `pytest` fails → implement source → confirm `pytest` passes

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module tests**: `pytest tests/crypto/test_{module}.py -v`
- **Import verification**: `python -c "from basic_tool.crypto import ..."`
- **Dependency check**: `uv sync` + `python -c "import argon2; import cryptography"`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Sequential gate — dependencies + scaffolding):
├── Task 1: pyproject.toml + uv sync [quick]
├── Task 2: config.py + exceptions.py + tests/crypto/__init__.py [quick]
└── (gate: all imports work before proceeding)

Wave 2 (TDD — 4 modules in parallel):
├── Task 3: test_password.py (RED) → password.py (GREEN) [deep]
├── Task 4: test_encrypt.py (RED) → encrypt.py (GREEN) [deep]
├── Task 5: test_sign.py (RED) → sign.py (GREEN) [quick]
└── Task 6: test_kdf.py (RED) → kdf.py (GREEN) [quick]

Wave 3 (Integration + docs):
├── Task 7: __init__.py + basic_tool/__init__.py update [quick]
└── Task 8: README.md [writing]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay

Critical Path: Task 1 → Task 2 → Task 3/4/5/6 → Task 7 → Task 8 → F1-F4 → user okay
Parallel Speedup: Wave 2 saves ~60% time (4 modules in parallel)
Max Concurrent: 4 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2, 3, 4, 5, 6 | 1 |
| 2 | 1 | 3, 4, 5, 6, 7 | 1 |
| 3 | 2 | 7 | 2 |
| 4 | 2 | 7 | 2 |
| 5 | 2 | 7 | 2 |
| 6 | 2 | 7 | 2 |
| 7 | 3, 4, 5, 6 | 8 | 3 |
| 8 | 7 | F1-F4 | 3 |

### Agent Dispatch Summary

- **Wave 1**: 2 tasks — T1 → `quick`, T2 → `quick` (sequential)
- **Wave 2**: 4 tasks — T3 → `deep`, T4 → `deep`, T5 → `quick`, T6 → `quick`
- **Wave 3**: 2 tasks — T7 → `quick`, T8 → `writing`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. 依赖安装与项目配置

  **What to do**:
  - 在 `pyproject.toml` 的 `[project.dependencies]` 中新增两行：
    - `"argon2-cffi>=23.1.0"`
    - `"cryptography>=42.0.0"`
  - 运行 `uv sync` 安装新依赖

  **Must NOT do**:
  - 不修改其他依赖的版本号
  - 不修改 `[project.optional-dependencies]` 部分
  - 不添加 `freezegun` 等新测试依赖

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件编辑 + 一个命令验证
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - 无需特定 skill

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (sequential start)
  - **Blocks**: Tasks 2, 3, 4, 5, 6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pyproject.toml:10-21` — 当前 `[project.dependencies]` 列表，在 `python-jose[cryptography]` 行后追加新依赖

  **External References**:
  - 设计文档 `doc/basic_tool_crypto_design.md:588-606` — 依赖管理章节，明确版本要求

  **WHY Each Reference Matters**:
  - `pyproject.toml:10-21` 确认插入位置和格式（每行 `"package>=version",`）
  - 设计文档 §四 确认最小版本号

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 依赖安装成功
    Tool: Bash
    Preconditions: pyproject.toml 已编辑
    Steps:
      1. 运行 `uv sync`
      2. 检查退出码为 0
      3. 运行 `python -c "import argon2; print(argon2.__version__)"`
      4. 运行 `python -c "import cryptography; print(cryptography.__version__)"`
    Expected Result: 两个命令均输出版本号，无报错
    Failure Indicators: uv sync 失败，或 import 报 ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-1-deps-installed.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add argon2-cffi and cryptography dependencies`
  - Files: `pyproject.toml`, `uv.lock`
  - Pre-commit: `uv sync`

- [x] 2. 配置模型 + 异常类型 + 测试目录初始化

  **What to do**:
  - 创建目录 `basic_tool/crypto/`
  - 创建 `basic_tool/crypto/config.py` — CryptoConfig 配置模型（pydantic BaseModel）
  - 创建 `basic_tool/crypto/exceptions.py` — 统一异常类型（CryptoError 基类 + 3 个子类）
  - 创建 `tests/crypto/` 目录和 `tests/crypto/__init__.py`（空文件）
  - 代码**严格按设计文档** `doc/basic_tool_crypto_design.md:80-133` 实现，一字不改

  **Must NOT do**:
  - 不创建 `__init__.py`（Task 7 统一处理）
  - 不实现 password/encrypt/sign/kdf 模块（后续 Task）
  - 不添加设计文档未提及的字段或异常类型

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 代码已在设计文档中完整给出，只需创建文件
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - 无需特定 skill

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (after Task 1)
  - **Blocks**: Tasks 3, 4, 5, 6, 7
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `basic_tool/redis/config.py` — Pydantic BaseModel 配置类范例
  - `basic_tool/logger/config.py` — dataclass 配置类范例（本项目用 BaseModel）

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:80-109` — CryptoConfig 完整代码
  - `doc/basic_tool_crypto_design.md:111-133` — exceptions.py 完整代码

  **WHY Each Reference Matters**:
  - redis/config.py 展示了 BaseModel 配置类的 docstring 和字段注释风格
  - 设计文档中的代码是最终规格，必须严格遵循

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 模块可导入
    Tool: Bash
    Preconditions: 文件已创建
    Steps:
      1. 运行 `python -c "from basic_tool.crypto.config import CryptoConfig; c = CryptoConfig(); print(c.argon2_memory_cost, c.token_bytes)"`
      2. 检查输出为 "65536 32"（默认值）
      3. 运行 `python -c "from basic_tool.crypto.exceptions import CryptoError, DecryptionError, SignatureVerificationError, InvalidKeyError; assert issubclass(DecryptionError, CryptoError); assert issubclass(SignatureVerificationError, CryptoError); assert issubclass(InvalidKeyError, CryptoError); print('OK')"`
    Expected Result: 两个命令均输出预期内容
    Failure Indicators: ImportError 或 AssertionError
    Evidence: .sisyphus/evidence/task-2-config-exceptions.txt

  Scenario: CryptoConfig 默认值正确
    Tool: Bash
    Preconditions: 文件已创建
    Steps:
      1. 运行 `python -c "from basic_tool.crypto.config import CryptoConfig; c = CryptoConfig(); assert c.argon2_memory_cost == 65536; assert c.argon2_time_cost == 3; assert c.argon2_parallelism == 1; assert c.argon2_hash_len == 32; assert c.argon2_salt_len == 16; assert c.token_bytes == 32; assert c.fernet_key == ''; print('all defaults OK')"`
    Expected Result: "all defaults OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-2-defaults.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add CryptoConfig and exception types`
  - Files: `basic_tool/crypto/config.py`, `basic_tool/crypto/exceptions.py`, `tests/crypto/__init__.py`
  - Pre-commit: `python -c "from basic_tool.crypto.config import CryptoConfig; from basic_tool.crypto.exceptions import CryptoError"`

- [x] 3. TDD: password.py — Argon2id 密码哈希 + Token 生成

  **What to do**:
  1. **RED**: 先编写 `tests/crypto/test_password.py`（9 个核心用例 + 补充用例）
  2. **GREEN**: 实现 `basic_tool/crypto/password.py`
  3. **REFACTOR**: 确认测试全部通过

  **测试用例（来自设计文档 §六 + Metis 补充）**:
  - 用例 1: `hash_password` 生成哈希 — 哈希非空，包含 `$argon2id$` 前缀
  - 用例 2: `verify_password` 正确密码 — 返回 True
  - 用例 3: `verify_password` 错误密码 — 返回 False，不抛异常
  - 用例 4: `verify_password` 篡改哈希 — 返回 False
  - 用例 5: `needs_rehash` 默认参数 — 返回 False
  - 用例 6: `needs_rehash` 不同参数 — 用 `CryptoConfig(argon2_time_cost=10)` 触发返回 True
  - 用例 7: `generate_token` 长度 — 默认 43 字符（32 字节 URL-safe）
  - 用例 8: `generate_token` 唯一性 — 100 次生成无重复
  - 用例 9: `generate_hex_token` 长度 — 默认 64 字符（32 字节 hex）
  - 补充: `generate_hex_token` 唯一性 — 100 次生成无重复
  - 补充: `verify_password` 完全无效的哈希字符串（如 `"not-a-hash"`）— 返回 False

  **关键注意**:
  - 测试中使用低开销配置 `CryptoConfig(memory_cost=1024, time_cost=1, parallelism=1)` 加速 Argon2id
  - `hash_password` 和 `verify_password` 传入此低开销 config
  - 源代码**严格按设计文档** `doc/basic_tool_crypto_design.md:136-255` 实现

  **Must NOT do**:
  - 不添加输入验证（空密码、None 检查等设计文档未提及的逻辑）
  - 不修改 config.py 或 exceptions.py
  - 不在测试中使用默认的 64MB CryptoConfig（太慢）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: TDD 循环（写测试 → 确认失败 → 实现 → 确认通过），需要多步骤验证
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - 无需特定 skill

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: Task 7
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `tests/logger/test_logger.py` — 测试类组织方式（class TestXxx，中文 docstring）
  - `tests/id_generator/test_generator.py` — 另一个测试范例

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:136-255` — password.py 完整代码
  - `basic_tool/crypto/config.py:CryptoConfig` — 配置类（已由 Task 2 创建）
  - `basic_tool/crypto/exceptions.py:CryptoError` — 基础异常

  **Test References**:
  - `doc/basic_tool_crypto_design.md:709-719` — 测试用例 1-9 的验证点描述

  **External References**:
  - argon2-cffi PasswordHasher API: https://argon2-cffi.readthedocs.io/en/stable/api.html

  **WHY Each Reference Matters**:
  - test_logger.py 展示了类名 `TestLogfmtFormatter`、方法名 `test_basic_format` 的命名约定
  - 设计文档中的 password.py 代码是最终规格
  - 低开销 CryptoConfig 是测试性能的关键

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TDD RED 阶段 — 测试文件存在且失败
    Tool: Bash
    Preconditions: password.py 不存在
    Steps:
      1. 确认 `tests/crypto/test_password.py` 已创建
      2. 运行 `pytest tests/crypto/test_password.py -v 2>&1 | head -5`
      3. 确认输出包含 ImportError 或 ModuleNotFoundError（password 模块不存在）
    Expected Result: 测试文件存在，运行时因 import 失败
    Failure Indicators: 测试文件不存在，或测试意外通过（说明没写测试就先实现了）
    Evidence: .sisyphus/evidence/task-3-red-phase.txt

  Scenario: TDD GREEN 阶段 — 所有测试通过
    Tool: Bash
    Preconditions: password.py 已实现
    Steps:
      1. 运行 `pytest tests/crypto/test_password.py -v`
      2. 检查退出码为 0
      3. 检查输出包含 "passed" 且无 "failed" 或 "error"
    Expected Result: 所有 11 个测试用例通过（9 核心 + 2 补充）
    Failure Indicators: 任何测试失败或收集错误
    Evidence: .sisyphus/evidence/task-3-green-phase.txt

  Scenario: 密码哈希往返验证（端到端）
    Tool: Bash
    Preconditions: password.py 已实现
    Steps:
      1. 运行 `python -c "
from basic_tool.crypto.password import hash_password, verify_password
from basic_tool.crypto.config import CryptoConfig
cfg = CryptoConfig(memory_cost=1024, time_cost=1, parallelism=1)
h = hash_password('test123', cfg)
assert h.startswith('\$argon2id\$'), f'bad prefix: {h[:20]}'
assert verify_password('test123', h, cfg), 'should verify'
assert not verify_password('wrong', h, cfg), 'should not verify'
print('roundtrip OK')
"
    Expected Result: "roundtrip OK"
    Failure Indicators: AssertionError 或 ImportError
    Evidence: .sisyphus/evidence/task-3-roundtrip.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add Argon2id password hashing and token generation`
  - Files: `basic_tool/crypto/password.py`, `tests/crypto/test_password.py`
  - Pre-commit: `pytest tests/crypto/test_password.py -v`

- [x] 4. TDD: encrypt.py — Fernet 对称加密

  **What to do**:
  1. **RED**: 先编写 `tests/crypto/test_encrypt.py`（6 个核心用例 + 补充用例）
  2. **GREEN**: 实现 `basic_tool/crypto/encrypt.py`
  3. **REFACTOR**: 确认测试全部通过

  **测试用例（来自设计文档 §六 + Metis 补充）**:
  - 用例 10: `encrypt` + `decrypt` 往返 — 解密后与原文一致
  - 用例 11: `decrypt` 错误密钥 — 抛 `DecryptionError`
  - 用例 12: `decrypt` 篡改密文 — 抛 `DecryptionError`
  - 用例 13: `decrypt` TTL 过期 — 使用 `time.sleep(1.1)` + `ttl=1` 策略
  - 用例 14: `encrypt_str` + `decrypt_str` — 字符串往返一致
  - 用例 15: `generate_fernet_key` — 生成合法 Fernet 密钥（可创建 Fernet 实例）
  - 补充: 空 Fernet key 加密 — 抛 `InvalidKeyError`
  - 补充: 空 bytes 加密解密往返 — `encrypt(b"", config)` 可正常加解密

  **关键注意**:
  - TTL 过期测试策略：先加密，然后 `time.sleep(1.1)`，再 `decrypt(token, config, ttl=1)` 应抛 DecryptionError
  - 源代码**严格按设计文档** `doc/basic_tool_crypto_design.md:257-385` 实现
  - 每个测试需创建有效的 CryptoConfig（含 fernet_key）

  **Must NOT do**:
  - 不添加 freezegun 依赖
  - 不修改 TTL 测试策略（使用 time.sleep）
  - 不添加设计文档未提及的 API

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: TDD 循环 + TTL 测试需要精确的时序控制
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 5, 6)
  - **Blocks**: Task 7
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `tests/logger/test_logger.py` — 测试类组织方式

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:257-385` — encrypt.py 完整代码
  - `basic_tool/crypto/config.py:CryptoConfig` — 配置类，需设置 `fernet_key`
  - `basic_tool/crypto/exceptions.py:DecryptionError` — 解密失败异常
  - `basic_tool/crypto/exceptions.py:InvalidKeyError` — 密钥无效异常

  **Test References**:
  - `doc/basic_tool_crypto_design.md:719-723` — 测试用例 10-15 的验证点描述

  **External References**:
  - cryptography Fernet 文档: https://cryptography.io/en/latest/fernet/

  **WHY Each Reference Matters**:
  - 设计文档中的 encrypt.py 代码是最终规格
  - Fernet 文档确认 TTL 参数行为（秒为单位，基于 token 内嵌时间戳）
  - TTL 测试需要理解 Fernet 的 TTL 是基于加密时的时间戳，不是当前时间

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TDD RED 阶段 — 测试文件存在且失败
    Tool: Bash
    Preconditions: encrypt.py 不存在
    Steps:
      1. 确认 `tests/crypto/test_encrypt.py` 已创建
      2. 运行 `pytest tests/crypto/test_encrypt.py -v 2>&1 | head -5`
      3. 确认输出包含 ImportError
    Expected Result: 测试文件存在，import 失败
    Failure Indicators: 测试文件不存在，或测试意外通过
    Evidence: .sisyphus/evidence/task-4-red-phase.txt

  Scenario: TDD GREEN 阶段 — 所有测试通过
    Tool: Bash
    Preconditions: encrypt.py 已实现
    Steps:
      1. 运行 `pytest tests/crypto/test_encrypt.py -v`
      2. 检查退出码为 0
    Expected Result: 所有 8 个测试用例通过（6 核心 + 2 补充）
    Failure Indicators: 任何测试失败
    Evidence: .sisyphus/evidence/task-4-green-phase.txt

  Scenario: 加密解密往返（端到端）
    Tool: Bash
    Preconditions: encrypt.py 已实现
    Steps:
      1. 运行 `python -c "
from basic_tool.crypto.encrypt import generate_fernet_key, encrypt, decrypt, encrypt_str, decrypt_str
from basic_tool.crypto.config import CryptoConfig
key = generate_fernet_key()
cfg = CryptoConfig(fernet_key=key)
# bytes 往返
ct = encrypt(b'hello world', cfg)
assert decrypt(ct, cfg) == b'hello world'
# str 往返
ct_str = encrypt_str('你好世界', cfg)
assert decrypt_str(ct_str, cfg) == '你好世界'
print('encrypt roundtrip OK')
"
    Expected Result: "encrypt roundtrip OK"
    Failure Indicators: AssertionError 或 ImportError
    Evidence: .sisyphus/evidence/task-4-roundtrip.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add Fernet symmetric encryption`
  - Files: `basic_tool/crypto/encrypt.py`, `tests/crypto/test_encrypt.py`
  - Pre-commit: `pytest tests/crypto/test_encrypt.py -v`

- [x] 5. TDD: sign.py — HMAC-SHA256 签名 + SHA-256 哈希

  **What to do**:
  1. **RED**: 先编写 `tests/crypto/test_sign.py`（4 个核心用例 + 补充用例）
  2. **GREEN**: 实现 `basic_tool/crypto/sign.py`
  3. **REFACTOR**: 确认测试全部通过

  **测试用例（来自设计文档 §六 + Metis 补充）**:
  - 用例 16: `sign` + `verify` 往返 — 验证通过
  - 用例 17: `verify` 错误签名 — 返回 False
  - 用例 18: `verify` 篡改数据 — 返回 False
  - 用例 19: `sha256` 确定性 — 同输入产出相同哈希
  - 补充: `sha256_hex` 别名 — 返回值与 `sha256` 完全相同
  - 补充: `sha256` 输出长度 — 固定 64 字符

  **关键注意**:
  - sign.py 无外部依赖（纯标准库 hashlib + hmac），代码简单
  - 源代码**严格按设计文档** `doc/basic_tool_crypto_design.md:387-450` 实现

  **Must NOT do**:
  - 不删除 `sha256_hex` 函数（即使它是别名，设计文档要求保留）
  - 不添加设计文档未提及的哈希算法

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯标准库，无外部依赖，代码简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4, 6)
  - **Blocks**: Task 7
  - **Blocked By**: Task 2

  **References**:

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:387-450` — sign.py 完整代码

  **Test References**:
  - `doc/basic_tool_crypto_design.md:725-729` — 测试用例 16-19 的验证点描述

  **WHY Each Reference Matters**:
  - 设计文档中的 sign.py 代码是最终规格
  - 注意 `sha256_hex` 是 `sha256` 的别名，需两个都测试

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TDD RED 阶段 — 测试文件存在且失败
    Tool: Bash
    Preconditions: sign.py 不存在
    Steps:
      1. 确认 `tests/crypto/test_sign.py` 已创建
      2. 运行 `pytest tests/crypto/test_sign.py -v 2>&1 | head -5`
      3. 确认输出包含 ImportError
    Expected Result: 测试文件存在，import 失败
    Evidence: .sisyphus/evidence/task-5-red-phase.txt

  Scenario: TDD GREEN 阶段 — 所有测试通过
    Tool: Bash
    Preconditions: sign.py 已实现
    Steps:
      1. 运行 `pytest tests/crypto/test_sign.py -v`
      2. 检查退出码为 0
    Expected Result: 所有 6 个测试用例通过（4 核心 + 2 补充）
    Failure Indicators: 任何测试失败
    Evidence: .sisyphus/evidence/task-5-green-phase.txt

  Scenario: 签名往返验证（端到端）
    Tool: Bash
    Preconditions: sign.py 已实现
    Steps:
      1. 运行 `python -c "
from basic_tool.crypto.sign import sign, verify, sha256
data = b'hello world'
key = b'secret-key-12345678901234567890'
sig = sign(data, key)
assert len(sig) == 64, f'expected 64 chars, got {len(sig)}'
assert verify(data, key, sig), 'should verify'
assert not verify(data, key, 'deadbeef'), 'should not verify wrong sig'
assert not verify(b'other data', key, sig), 'should not verify wrong data'
h = sha256(data)
assert len(h) == 64
assert h == sha256(data), 'sha256 should be deterministic'
print('sign roundtrip OK')
"
    Expected Result: "sign roundtrip OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-5-roundtrip.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add HMAC-SHA256 signing and SHA-256 hashing`
  - Files: `basic_tool/crypto/sign.py`, `tests/crypto/test_sign.py`
  - Pre-commit: `pytest tests/crypto/test_sign.py -v`

- [x] 6. TDD: kdf.py — HKDF / PBKDF2 密钥派生

  **What to do**:
  1. **RED**: 先编写 `tests/crypto/test_kdf.py`（3 个核心用例 + 补充用例）
  2. **GREEN**: 实现 `basic_tool/crypto/kdf.py`
  3. **REFACTOR**: 确认测试全部通过

  **测试用例（来自设计文档 §六 + Metis 补充）**:
  - 用例 20: `derive_key_hkdf` 不同 info — 派生出不同密钥
  - 用例 21: `derive_key_pbkdf2` 确定性 — 同输入产出相同密钥
  - 用例 22: `CryptoConfig` 自定义参数 — Argon2id 参数生效
  - 补充: `derive_key_hkdf` 确定性 — 同输入产出相同密钥
  - 补充: `derive_key_hkdf` 输出长度 — 默认 32 字节

  **关键注意**:
  - 源代码**严格按设计文档** `doc/basic_tool_crypto_design.md:452-521` 实现
  - kdf.py 依赖 cryptography 库（HKDF, PBKDF2HMAC）

  **Must NOT do**:
  - 不添加设计文档未提及的 KDF 算法
  - 不修改默认迭代次数

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 代码简单，仅 2 个函数，测试用例少
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4, 5)
  - **Blocks**: Task 7
  - **Blocked By**: Task 2

  **References**:

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:452-521` — kdf.py 完整代码

  **Test References**:
  - `doc/basic_tool_crypto_design.md:729-732` — 测试用例 20-22 的验证点描述

  **External References**:
  - cryptography HKDF: https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf
  - cryptography PBKDF2: https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#pbkdf2

  **WHY Each Reference Matters**:
  - 设计文档中的 kdf.py 代码是最终规格
  - HKDF/PBKDF2 文档确认参数含义（salt, info, length, iterations）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: TDD RED 阶段 — 测试文件存在且失败
    Tool: Bash
    Preconditions: kdf.py 不存在
    Steps:
      1. 确认 `tests/crypto/test_kdf.py` 已创建
      2. 运行 `pytest tests/crypto/test_kdf.py -v 2>&1 | head -5`
      3. 确认输出包含 ImportError
    Expected Result: 测试文件存在，import 失败
    Evidence: .sisyphus/evidence/task-6-red-phase.txt

  Scenario: TDD GREEN 阶段 — 所有测试通过
    Tool: Bash
    Preconditions: kdf.py 已实现
    Steps:
      1. 运行 `pytest tests/crypto/test_kdf.py -v`
      2. 检查退出码为 0
    Expected Result: 所有 5 个测试用例通过（3 核心 + 2 补充）
    Failure Indicators: 任何测试失败
    Evidence: .sisyphus/evidence/task-6-green-phase.txt

  Scenario: 密钥派生验证（端到端）
    Tool: Bash
    Preconditions: kdf.py 已实现
    Steps:
      1. 运行 `python -c "
from basic_tool.crypto.kdf import derive_key_hkdf, derive_key_pbkdf2
# HKDF: 不同 info 派生不同密钥
key_enc = derive_key_hkdf(b'master-key', b'salt', b'encryption')
key_sign = derive_key_hkdf(b'master-key', b'salt', b'signing')
assert key_enc != key_sign, 'different info should produce different keys'
assert len(key_enc) == 32, f'expected 32 bytes, got {len(key_enc)}'
# HKDF: 确定性
assert derive_key_hkdf(b'master', b'salt', b'info') == derive_key_hkdf(b'master', b'salt', b'info')
# PBKDF2: 确定性
assert derive_key_pbkdf2(b'password', b'salt') == derive_key_pbkdf2(b'password', b'salt')
print('kdf OK')
"
    Expected Result: "kdf OK"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-6-roundtrip.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add HKDF and PBKDF2 key derivation`
  - Files: `basic_tool/crypto/kdf.py`, `tests/crypto/test_kdf.py`
  - Pre-commit: `pytest tests/crypto/test_kdf.py -v`

- [x] 7. __init__.py 导出注册 + 模块描述更新

  **What to do**:
  - 创建 `basic_tool/crypto/__init__.py` — 平铺导出所有公开 API
  - 更新 `basic_tool/__init__.py` docstring — 在 `当前模块:` 列表中新增 `- crypto: 密码学工具集，提供密码哈希、对称加密、签名验证、密钥派生等能力`
  - 代码**严格按设计文档** `doc/basic_tool_crypto_design.md:523-584` 实现 __init__.py

  **Must NOT do**:
  - 不在 `basic_tool/__init__.py` 中添加任何 import 语句
  - 不修改 `basic_tool/__init__.py` 中已有的行（只追加一行 crypto 描述）
  - 不修改其他子模块的 __init__.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 两个文件的小编辑
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Wave 2)
  - **Blocks**: Task 8
  - **Blocked By**: Tasks 3, 4, 5, 6

  **References**:

  **Pattern References**:
  - `basic_tool/logger/__init__.py` — 导出模式范例（docstring + imports + __all__）
  - `basic_tool/id_generator/__init__.py` — 另一个导出范例
  - `basic_tool/__init__.py` — 顶层 docstring 格式（`- name: description` 列表）

  **API/Type References**:
  - `doc/basic_tool_crypto_design.md:523-584` — __init__.py 完整代码

  **WHY Each Reference Matters**:
  - logger/__init__.py 展示了 docstring 中使用示例的写法
  - 顶层 __init__.py 只需在现有列表中追加一行，格式一致

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 全量公开 API 可导入
    Tool: Bash
    Preconditions: __init__.py 已创建
    Steps:
      1. 运行 `python -c "from basic_tool.crypto import hash_password, verify_password, needs_rehash, generate_token, generate_hex_token, generate_fernet_key, encrypt, decrypt, encrypt_str, decrypt_str, sign, verify, sha256, derive_key_hkdf, derive_key_pbkdf2, CryptoConfig, CryptoError, DecryptionError, SignatureVerificationError, InvalidKeyError; print('all imports OK')"`
    Expected Result: "all imports OK"
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-7-all-imports.txt

  Scenario: __all__ 包含所有公开符号
    Tool: Bash
    Preconditions: __init__.py 已创建
    Steps:
      1. 运行 `python -c "import basic_tool.crypto; symbols = basic_tool.crypto.__all__; assert len(symbols) == 17, f'expected 17 symbols, got {len(symbols)}'; print(symbols)"`
    Expected Result: 输出包含 17 个符号名的列表
    Failure Indicators: AssertionError 或数量不符
    Evidence: .sisyphus/evidence/task-7-all-symbols.txt

  Scenario: 顶层 docstring 已更新
    Tool: Bash
    Preconditions: basic_tool/__init__.py 已编辑
    Steps:
      1. 运行 `python -c "import basic_tool; assert 'crypto' in basic_tool.__doc__, 'crypto not in docstring'; print('docstring updated')"`
    Expected Result: "docstring updated"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-7-docstring.txt
  ```

  **Commit**: YES
  - Message: `feat(crypto): add package exports and update module registry`
  - Files: `basic_tool/crypto/__init__.py`, `basic_tool/__init__.py`
  - Pre-commit: `python -c "from basic_tool.crypto import hash_password, encrypt_str, sign"`

- [x] 8. README.md 模块文档

  **What to do**:
  - 创建 `basic_tool/crypto/README.md`
  - 遵循现有 README 格式（参考 `basic_tool/logger/README.md`）
  - 内容包含：标题 + 简介 → `## 依赖` → `## 模块结构` → `## API 文档` → `## 使用示例`
  - API 文档覆盖所有公开函数（签名 + 参数表 + 描述）
  - 使用示例覆盖：密码哈希、Token 生成、对称加密、HMAC 签名、密钥派生

  **Must NOT do**:
  - 不添加设计文档未提及的 API 或用法
  - 不创建使用示例中未用到的虚构场景
  - 不使用 emoji

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档撰写任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Task 7)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 7

  **References**:

  **Pattern References**:
  - `basic_tool/logger/README.md` — README 格式范例
  - `basic_tool/redis/README.md` — 更大的 README 范例（API 文档更完整）
  - `basic_tool/id_generator/README.md` — 另一个 README 范例

  **API/Type References**:
  - `basic_tool/crypto/__init__.py` — `__all__` 列表（所有需文档化的公开 API）
  - `doc/basic_tool_crypto_design.md:607-701` — 使用示例章节（可直接参考）

  **WHY Each Reference Matters**:
  - logger/README.md 的格式是目标格式（Title → 依赖 → 模块结构 → API 文档 → 使用示例）
  - 设计文档 §五 的使用示例可以直接改编入 README

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README 文件存在且格式完整
    Tool: Bash
    Preconditions: README.md 已创建
    Steps:
      1. 运行 `test -f basic_tool/crypto/README.md && echo "exists" || echo "missing"`
      2. 运行 `grep -c "^## " basic_tool/crypto/README.md` 确认至少 4 个二级标题
      3. 运行 `grep -c "^### " basic_tool/crypto/README.md` 确认 API 文档覆盖各模块
    Expected Result: 文件存在，至少有 4 个 ## 标题（依赖、模块结构、API文档、使用示例）
    Failure Indicators: 文件不存在或标题不足
    Evidence: .sisyphus/evidence/task-8-readme.txt

  Scenario: 全量测试最终验证
    Tool: Bash
    Preconditions: 所有源文件和测试已就绪
    Steps:
      1. 运行 `pytest tests/crypto/ -v`
      2. 检查退出码为 0
      3. 统计通过数
    Expected Result: 23+ 测试全部通过
    Failure Indicators: 任何失败
    Evidence: .sisyphus/evidence/task-8-final-tests.txt

  Scenario: 现有测试未受影响
    Tool: Bash
    Preconditions: 所有 crypto 模块已就绪
    Steps:
      1. 运行 `pytest tests/ -v --ignore=tests/crypto 2>&1 | tail -5`
      2. 检查退出码为 0
    Expected Result: 所有非 crypto 测试通过
    Failure Indicators: 任何现有测试失败
    Evidence: .sisyphus/evidence/task-8-existing-tests.txt
  ```

  **Commit**: YES
  - Message: `docs(crypto): add module README`
  - Files: `basic_tool/crypto/README.md`
  - Pre-commit: `pytest tests/crypto/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run import command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/crypto/ -v`. Review all changed files for: missing docstrings, `as any`/type ignores, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-module integration: hash password → encrypt → sign → verify roundtrip. Test edge cases: empty inputs, wrong keys, tampered data. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual files. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Task 1**: `feat(crypto): add argon2-cffi and cryptography dependencies` — pyproject.toml, uv.lock
- **Task 2**: `feat(crypto): add CryptoConfig and exception types` — basic_tool/crypto/config.py, exceptions.py, tests/crypto/__init__.py
- **Task 3**: `feat(crypto): add Argon2id password hashing and token generation` — password.py, test_password.py
- **Task 4**: `feat(crypto): add Fernet symmetric encryption` — encrypt.py, test_encrypt.py
- **Task 5**: `feat(crypto): add HMAC-SHA256 signing and SHA-256 hashing` — sign.py, test_sign.py
- **Task 6**: `feat(crypto): add HKDF and PBKDF2 key derivation` — kdf.py, test_kdf.py
- **Task 7**: `feat(crypto): add package exports and update module registry` — __init__.py (both)
- **Task 8**: `docs(crypto): add module README` — README.md

---

## Success Criteria

### Verification Commands
```bash
# Dependencies installed
uv sync  # Expected: success, no errors

# All tests pass
pytest tests/crypto/ -v  # Expected: 23+ tests, 0 failures

# All public API importable
python -c "from basic_tool.crypto import hash_password, verify_password, needs_rehash, generate_token, generate_hex_token, generate_fernet_key, encrypt, decrypt, encrypt_str, decrypt_str, sign, verify, sha256, derive_key_hkdf, derive_key_pbkdf2, CryptoConfig, CryptoError, DecryptionError, SignatureVerificationError, InvalidKeyError"  # Expected: no output, exit 0

# No other tests broken
pytest tests/ -v --ignore=tests/crypto  # Expected: all existing tests still pass
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] No files modified outside design doc scope
- [ ] README.md follows existing pattern (logger/README.md)
