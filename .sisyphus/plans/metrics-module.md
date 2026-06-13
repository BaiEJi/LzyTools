# basic_tool.metrics 模块实施计划

## TL;DR

> **Quick Summary**: 在 `basic_tool` SDK 中新增 `metrics` 子模块，提供指标采集、Redis Streams 缓冲、VictoriaMetrics 持久化、PromQL 查询、告警评估、健康检查等能力。同时新增 Redis StreamMixin（xadd 前置依赖）。
> 
> **Deliverables**:
> - `basic_tool/metrics/` 完整子模块（9 个文件）
> - `basic_tool/redis/client/_stream.py` StreamMixin
> - `tests/metrics/` 完整测试套件
> - Redis StreamMixin 测试
> - README.md、版本升级、模块注册
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: Task 1 (StreamMixin) → Task 5 (Writer) → Task 9 (Health) → Task 10-11 (Integration) → Final

---

## Context

### Original Request
用户提供了完整的 `basic_tool.metrics` 模块设计文档（`doc/basic_tool_metrics_design.md`），包含所有文件的代码、API 设计、使用方式。要求按文档实现，并允许审查优化。

### Interview Summary
**Key Discussions**:
- 实现模式：实现 + 审查优化（允许修正明显问题）
- 测试策略：TDD（先写测试再实现）
- 安全修复：替换 collector.py 中的 `eval()` 调用
- 发现 Redis Cache 缺少 `xadd` 方法，需先创建 StreamMixin

**Research Findings**:
- Redis `Cache.xadd()` 不存在，需创建 `_stream.py` Mixin
- 项目版本 0.4.0，测试框架 pytest + pytest-asyncio (auto mode)
- 测试模式：class-based、Chinese docstrings、fakeredis、httpx.MockTransport、plain assert
- 无需新增依赖（httpx/orjson/pydantic/loguru 均已存在）

### Metis Review
**Identified Gaps** (addressed):
- `flush_to_vm` 每次创建新 httpx 客户端 → 改为复用客户端
- `_do_flush` 中 `_buffers.pop()` 在 POST 前执行导致失败丢数据 → 改为 copy-then-pop
- `eval()` 替换 → 重构聚合 key 策略，避免 stringify/eval 往返
- 测试文件路径应为 `tests/metrics/test_metrics.py`（非 `tests/test_metrics.py`）
- 所有新文件需 module-level docstring

---

## Work Objectives

### Core Objective
实现 `basic_tool.metrics` 子模块的全部代码，包含配置、数据模型、采集器、写入器、查询器、告警评估器、Prometheus exposition、健康检查，以及前置依赖 Redis StreamMixin。

### Concrete Deliverables
- `basic_tool/redis/client/_stream.py` — StreamMixin（xadd）
- `basic_tool/redis/client/__init__.py` — 添加 StreamMixin 继承
- `basic_tool/redis/README.md` — 添加 Stream 操作文档
- `basic_tool/metrics/__init__.py` — 模块导出
- `basic_tool/metrics/config.py` — MetricsConfig
- `basic_tool/metrics/models.py` — 数据模型
- `basic_tool/metrics/collector.py` — 采集器
- `basic_tool/metrics/writer.py` — Redis + VM 写入
- `basic_tool/metrics/reader.py` — PromQL 查询
- `basic_tool/metrics/alerter.py` — 告警评估
- `basic_tool/metrics/scraper.py` — Prometheus exposition 输出
- `basic_tool/metrics/health.py` — 健康检查
- `basic_tool/metrics/README.md` — 模块文档
- `tests/metrics/test_metrics.py` — 完整测试
- `tests/redis/test_stream.py` — StreamMixin 测试
- `basic_tool/__init__.py` — 添加 metrics 模块描述
- `pyproject.toml` — 版本 0.4.0 → 0.5.0

### Definition of Done
- [ ] `pytest tests/ -v` 全部通过
- [ ] `python -c "from basic_tool.metrics import MetricsCollector, MetricsConfig, ...; print('ok')"` 成功
- [ ] `collector.py` 中无 `eval(` 调用
- [ ] `pyproject.toml` 版本为 `0.5.0`

### Must Have
- 所有设计文档中定义的公开 API
- 每个组件的 TDD 测试（先测试后实现）
- `eval()` 安全问题修复
- `flush_to_vm` 客户端复用修复
- `_do_flush` 数据丢失修复（copy-then-pop）
- 每个文件有 module-level docstring
- README.md 文档
- Redis StreamMixin（xadd 前置依赖）

### Must NOT Have (Guardrails)
- 不修改 `basic_tool/redis/` 现有代码（仅添加 StreamMixin 继承行）
- 不添加新依赖到 `pyproject.toml`
- 不给 `__init__.py` 添加 `generate_exposition` 导出（设计文档未包含）
- 不给 `AlertEvaluator` 添加 async、持久化、调度
- 不添加重试逻辑、熔断器、自定义异常类
- 不给 StreamMixin 添加 xadd 以外的流操作（最小化）
- 不触碰 `basic_tool/` 下其他子模块的代码
- 版本号仅修改 version 字段，不改其他 pyproject.toml 内容

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio + fakeredis)
- **Automated tests**: YES (TDD)
- **Framework**: pytest >= 8 + pytest-asyncio >= 0.23 (asyncio_mode = "auto")
- **TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Unit tests**: pytest (class-based, Chinese docstrings, fakeredis/httpx.MockTransport)
- **Import verification**: `python -c "from basic_tool.metrics import ..."`
- **Static checks**: `ast_grep_search` for eval(, module docstrings

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (Prerequisite - StreamMixin):
└── Task 1: Redis StreamMixin xadd + test + Cache 继承更新 [quick]

Wave 1 (Foundation - parallel, no dependencies):
├── Task 2: MetricsConfig + tests [quick]
└── Task 3: Data models + tests [quick]

Wave 2 (Core - parallel, depends Wave 0+1):
├── Task 4: MetricsCollector + tests (depends: 2, 3) [deep]
├── Task 5: MetricsWriter + tests (depends: 2, 3, 1) [deep]
├── Task 6: MetricsReader + tests (depends: 2, 3) [unspecified-high]
└── Task 7: AlertEvaluator + tests (depends: 3) [deep]

Wave 3 (Support + Integration - depends Wave 2):
├── Task 8: Scraper + tests (depends: 4) [quick]
├── Task 9: Health + tests (depends: 5, 6) [quick]
├── Task 10: __init__.py exports (depends: 4-9) [quick]
└── Task 11: README.md + pyproject.toml + module registry (depends: 10) [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T5 → T9 → T10 → T11 → F1-F4 → user okay
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | - | 5 | 0 |
| 2 | - | 4, 5, 6 | 1 |
| 3 | - | 4, 5, 6, 7 | 1 |
| 4 | 2, 3 | 8, 10 | 2 |
| 5 | 1, 2, 3 | 9, 10 | 2 |
| 6 | 2, 3 | 9, 10 | 2 |
| 7 | 3 | 10 | 2 |
| 8 | 4 | 10 | 3 |
| 9 | 5, 6 | 10 | 3 |
| 10 | 4-9 | 11 | 3 |
| 11 | 10 | F1-F4 | 3 |

### Agent Dispatch Summary

- **Wave 0**: 1 task — T1 → `quick`
- **Wave 1**: 2 tasks — T2 → `quick`, T3 → `quick`
- **Wave 2**: 4 tasks — T4 → `deep`, T5 → `deep`, T6 → `unspecified-high`, T7 → `deep`
- **Wave 3**: 4 tasks — T8 → `quick`, T9 → `quick`, T10 → `quick`, T11 → `quick`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Redis StreamMixin（xadd 前置依赖）

  **What to do**:
  - TDD: 先写 `tests/redis/test_stream.py` 测试 `Cache.xadd()` 方法
  - 创建 `basic_tool/redis/client/_stream.py`，包含 `StreamMixin` 类
  - `StreamMixin` 提供 `async def xadd(self, name, fields, id="*", maxlen=None, approximate=True)` 方法
  - 每个方法有 docstring（Args/Returns），遵循 `_pubsub.py` 模式
  - 在 `basic_tool/redis/client/__init__.py` 中添加 `from basic_tool.redis.client._stream import StreamMixin` 并加入 `Cache` 继承列表
  - 更新 `basic_tool/redis/README.md` 添加 Stream 操作表格
  - 测试使用 fakeredis 验证 xadd 功能，包括 maxlen 参数

  **Must NOT do**:
  - 不修改 `client/__init__.py` 中任何现有代码（仅添加 1 行 import + 继承列表追加）
  - 不添加 xadd 以外的 Stream 操作（xread/xreadgroup 等）
  - 不重构现有 Mixin 或 Cache 代码

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件添加 + 继承行修改，模式清晰
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: 不涉及 git 操作

  **Parallelization**:
  - **Can Run In Parallel**: NO (prerequisite for Task 5)
  - **Parallel Group**: Wave 0 (solo)
  - **Blocks**: Task 5 (Writer)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/redis/client/_pubsub.py` — Mixin 模式参考（class 结构、self.client 用法、async 方法、docstring 风格）
  - `basic_tool/redis/client/__init__.py` — Cache 类继承列表（需追加 StreamMixin）
  - `basic_tool/redis/README.md` — 文档格式参考（表格结构）

  **API/Type References**:
  - redis-py `xadd` 签名: `xadd(name, fields, id='*', maxlen=None, approximate=True)` → returns stream entry ID

  **Test References**:
  - `tests/redis/test_client.py` — fakeredis fixture 使用方式
  - `tests/conftest.py` — shared cache fixture（async yield pattern）

  **WHY Each Reference Matters**:
  - `_pubsub.py` 是最接近的 Mixin 模板，每行结构都可以复制
  - `client/__init__.py` 的继承列表是唯一需要修改的位置
  - `test_client.py` 展示了如何用 fakeredis 测试 Cache 方法

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: xadd 写入 Stream 并返回 entry ID
    Tool: Bash
    Preconditions: fakeredis 环境可用
    Steps:
      1. 创建 Cache 实例，注入 FakeRedis
      2. result = await cache.xadd("test_stream", {"field1": "value1", "field2": "value2"})
      3. assert result 是有效的 stream entry ID（格式 "1234567890-0"）
    Expected Result: xadd 返回非空字符串，格式匹配 r"\d+-\d+"
    Failure Indicators: AttributeError（方法不存在）、异常
    Evidence: .sisyphus/evidence/task-1-xadd-basic.txt

  Scenario: xadd 带 maxlen 参数限制 Stream 长度
    Tool: Bash
    Preconditions: fakeredis 环境可用
    Steps:
      1. 创建 Cache 实例
      2. 循环写入 15 条数据到 stream，maxlen=10
      3. xlen_result = await cache.client.xlen("test_stream")
      4. assert xlen_result <= 15（approximate=True 允许略超）
    Expected Result: stream 长度不超过 maxlen 太多（fakeredis approximate 行为）
    Failure Indicators: xlen 远超 maxlen
    Evidence: .sisyphus/evidence/task-1-xadd-maxlen.txt

  Scenario: Cache 类包含 StreamMixin
    Tool: Bash
    Steps:
      1. python -c "from basic_tool.redis import Cache; assert 'xadd' in dir(Cache); print('ok')"
    Expected Result: 输出 "ok"
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-1-mixin-integration.txt
  ```

  **Commit**: YES (独立提交)
  - Message: `feat(redis): add StreamMixin with xadd method`
  - Files: `basic_tool/redis/client/_stream.py`, `basic_tool/redis/client/__init__.py`, `basic_tool/redis/README.md`, `tests/redis/test_stream.py`
  - Pre-commit: `pytest tests/redis/test_stream.py -v`

- [x] 2. MetricsConfig 配置模型

  **What to do**:
  - TDD: 先写测试验证 MetricsConfig 默认值、自定义值、Pydantic 验证
  - 创建 `basic_tool/metrics/config.py`，包含 `MetricsConfig(BaseModel)` 类
  - 字段：vm_url, redis_url, service_name, flush_interval, flush_batch_size, stream_prefix, stream_max_len, alert_interval
  - 添加 module-level docstring 和 class docstring（含 Attributes 说明）
  - 测试覆盖：默认值验证、自定义值、无效类型校验

  **Must NOT do**:
  - 不添加环境变量读取逻辑
  - 不添加验证器（validator）或自定义类型
  - 不添加设计文档未定义的字段

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件 Pydantic 模型，模式明确
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 3)
  - **Blocks**: Tasks 4, 5, 6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/redis/config.py` — Pydantic config 模式（class docstring + Attributes 列表）
  - `basic_tool/http_client/config.py` — 嵌套 Pydantic config 示例
  - `basic_tool/metrics/config.py` (设计文档) — 完整代码在第 34-60 行

  **Test References**:
  - `tests/redis/test_client.py` — config 实例化测试模式

  **WHY Each Reference Matters**:
  - `redis/config.py` 是 config.py 的标准模板
  - 设计文档第 34-60 行提供了完整实现代码

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: MetricsConfig 默认值正确
    Tool: Bash
    Steps:
      1. config = MetricsConfig()
      2. assert config.vm_url == "http://localhost:8428"
      3. assert config.redis_url == "redis://localhost:6379/0"
      4. assert config.flush_interval == 5.0
      5. assert config.flush_batch_size == 1000
      6. assert config.stream_prefix == "metrics"
      7. assert config.stream_max_len == 100_000
      8. assert config.alert_interval == 30.0
    Expected Result: 所有默认值匹配
    Evidence: .sisyphus/evidence/task-2-config-defaults.txt

  Scenario: MetricsConfig 自定义值
    Tool: Bash
    Steps:
      1. config = MetricsConfig(vm_url="http://vm:8428", service_name="agent", flush_interval=10.0)
      2. assert config.vm_url == "http://vm:8428"
      3. assert config.service_name == "agent"
      4. assert config.flush_interval == 10.0
    Expected Result: 自定义值正确
    Evidence: .sisyphus/evidence/task-2-config-custom.txt

  Scenario: MetricsConfig 无效类型校验
    Tool: Bash
    Steps:
      1. with pytest.raises(ValidationError): MetricsConfig(flush_interval="not_a_number")
    Expected Result: Pydantic ValidationError
    Evidence: .sisyphus/evidence/task-2-config-validation.txt
  ```

  **Commit**: YES (与 Task 3 合并)
  - Message: `feat(metrics): add config and data models`
  - Files: `basic_tool/metrics/config.py`
  - Pre-commit: `pytest tests/metrics/test_metrics.py -v -k "Config"`

- [x] 3. 数据模型（models.py）

  **What to do**:
  - TDD: 先写测试验证所有模型创建、字段验证、枚举值
  - 创建 `basic_tool/metrics/models.py`，包含：MetricType(Enum), MetricPoint, MetricBatch, TimeRange, QueryResult, AlertRule, AlertState(Enum), AlertEvent
  - 添加 module-level docstring
  - 所有 Pydantic model 都有 class docstring
  - 测试覆盖：各模型创建、必填/选填字段、MetricType 枚举值、AlertState 枚举值

  **Must NOT do**:
  - 不添加自定义验证器
  - 不修改设计文档中定义的字段
  - 不添加序列化/反序列化方法

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯 Pydantic 模型定义，无外部依赖
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 4, 5, 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `basic_tool/metrics/models.py` (设计文档) — 完整代码在第 66-140 行

  **Test References**:
  - `tests/logger/test_logger.py` — 简单模型测试模式（inline 对象构造）

  **WHY Each Reference Matters**:
  - 设计文档第 66-140 行提供了完整实现代码，包括所有 8 个类/枚举

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: MetricPoint 创建和字段验证
    Tool: Bash
    Steps:
      1. point = MetricPoint(name="test_metric", value=42.0)
      2. assert point.name == "test_metric"
      3. assert point.value == 42.0
      4. assert point.type == MetricType.GAUGE  # 默认
      5. assert point.labels == {}
      6. assert point.timestamp is None
      7. point_with_labels = MetricPoint(name="req", value=1.0, type=MetricType.COUNTER, labels={"method": "GET"})
      8. assert point_with_labels.labels == {"method": "GET"}
    Expected Result: 所有字段正确
    Evidence: .sisyphus/evidence/task-3-metric-point.txt

  Scenario: MetricBatch 包含多个 MetricPoint
    Tool: Bash
    Steps:
      1. batch = MetricBatch(points=[MetricPoint(name="a", value=1), MetricPoint(name="b", value=2)], source="test")
      2. assert len(batch.points) == 2
      3. assert batch.source == "test"
    Expected Result: batch 包含 2 个 point
    Evidence: .sisyphus/evidence/task-3-metric-batch.txt

  Scenario: AlertRule 解析和默认值
    Tool: Bash
    Steps:
      1. rule = AlertRule(name="high_cpu", metric="cpu_usage", condition="> 80")
      2. assert rule.duration == "5m"  # 默认
      3. assert rule.cooldown == "10m"  # 默认
      4. assert rule.enabled is True
      5. assert rule.channels == []
    Expected Result: 默认值正确
    Evidence: .sisyphus/evidence/task-3-alert-rule.txt

  Scenario: 枚举值正确
    Tool: Bash
    Steps:
      1. assert MetricType.COUNTER.value == "counter"
      2. assert MetricType.GAUGE.value == "gauge"
      3. assert MetricType.HISTOGRAM.value == "histogram"
      4. assert AlertState.OK.value == "ok"
      5. assert AlertState.PENDING.value == "pending"
      6. assert AlertState.FIRING.value == "firing"
    Expected Result: 所有枚举值匹配
    Evidence: .sisyphus/evidence/task-3-enums.txt
  ```

  **Commit**: YES (与 Task 2 合并)
  - Message: `feat(metrics): add config and data models`
  - Files: `basic_tool/metrics/models.py`
  - Pre-commit: `pytest tests/metrics/test_metrics.py -v -k "Model or Metric or Alert"`

- [x] 4. MetricsCollector 采集器

  **What to do**:
  - TDD: 先写测试验证 counter/gauge/histogram 方法、prometheus_exposition 输出、flush 行为
  - 创建 `basic_tool/metrics/collector.py`，包含 `MetricsCollector` 类
  - 实现 `init()/close()` 生命周期、`counter()/gauge()/histogram()` 方法
  - 实现 `prometheus_exposition()` — **修复 eval() 安全问题**：重构聚合 key 策略
    - 将 `key = str(sorted(p.labels.items()))` + `dict(eval(key))` 改为使用 `tuple(sorted(p.labels.items()))` 作为 key（原生 hashable，无需 stringify/eval 往返）
  - 修复 `_do_flush` 数据丢失问题：先复制 buffer 再 pop，POST 失败时保留数据
  - 添加 module-level docstring
  - 测试使用 `httpx.MockTransport` mock HTTP flush
  - 测试覆盖：counter/gauge/histogram 记录、exposition 输出、flush 失败不丢数据、空 buffer exposition

  **Must NOT do**:
  - 不添加 buffer 大小限制或背压机制
  - 不给 counter 添加单调递增校验
  - 不添加 `eval()` 或 `ast.literal_eval` — 使用 tuple key 方案
  - 不修改设计文档中定义的公开 API 签名

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 异步生命周期管理 + eval() 修复 + flush 修复，需要仔细处理
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Tasks 8, 10
  - **Blocked By**: Tasks 2, 3

  **References**:

  **Pattern References**:
  - `basic_tool/http_client/client.py` — 异步 init/close 生命周期模式
  - `basic_tool/metrics/collector.py` (设计文档) — 完整代码在第 148-293 行

  **API/Type References**:
  - `basic_tool/metrics/config.py` (Task 2) — MetricsConfig
  - `basic_tool/metrics/models.py` (Task 3) — MetricBatch, MetricPoint, MetricType

  **Test References**:
  - `tests/http_client/test_client.py` — httpx MockTransport 使用模式

  **WHY Each Reference Matters**:
  - `http_client/client.py` 展示了 `init()/close()` + `asyncio.create_task` 的生命周期管理
  - 设计文档第 148-293 行提供了完整实现，但需修复 eval() 和 flush 问题
  - MockTransport 是 mock HTTP flush 的正确方式

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: counter/gauge/histogram 方法记录指标
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999/ingest")
      2. collector.counter("http_requests", labels={"method": "GET"})
      3. collector.gauge("queue_depth", value=42)
      4. collector.histogram("latency_ms", value=123.4)
      5. assert len(collector._buffers["http_requests"]) == 1
      6. assert len(collector._buffers["queue_depth"]) == 1
      7. assert len(collector._buffers["latency_ms"]) == 1
    Expected Result: 3 个指标分别记录到对应 buffer
    Evidence: .sisyphus/evidence/task-4-collector-buffer.txt

  Scenario: prometheus_exposition 输出格式正确（无 eval）
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999/ingest")
      2. collector.counter("http_requests_total", labels={"method": "GET"})
      3. collector.counter("http_requests_total", labels={"method": "POST"})
      4. collector.gauge("queue_depth", value=42)
      5. output = collector.prometheus_exposition()
      6. assert "# HELP http_requests_total" in output
      7. assert "# TYPE http_requests_total counter" in output
      8. assert 'method="GET"' in output
      9. assert 'method="POST"' in output
      10. assert "queue_depth 42" in output
      11. grep -c 'eval(' basic_tool/metrics/collector.py → 必须返回 0
    Expected Result: exposition 格式正确，无 eval 调用
    Failure Indicators: eval( 出现在代码中、label 不在输出中
    Evidence: .sisyphus/evidence/task-4-exposition.txt

  Scenario: flush 失败不丢失数据
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999/ingest")
      2. 用 MockTransport 返回 500 错误
      3. collector.counter("test_metric", value=1)
      4. await collector._do_flush()
      5. 验证 buffer 仍保留数据（修复后行为）
    Expected Result: flush 失败时数据保留在 buffer 中
    Evidence: .sisyphus/evidence/task-4-flush-failure.txt

  Scenario: 空 buffer exposition 输出
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999/ingest")
      2. output = collector.prometheus_exposition()
      3. assert output == "\n"
    Expected Result: 空 buffer 返回仅换行符
    Evidence: .sisyphus/evidence/task-4-empty-exposition.txt
  ```

  **Commit**: YES (与 Tasks 5-7 合并)
  - Message: `feat(metrics): add collector, writer, reader, alerter`
  - Files: `basic_tool/metrics/collector.py`

- [x] 5. MetricsWriter Redis + VM 写入器

  **What to do**:
  - TDD: 先写测试验证 write_batch（Redis Streams）和 flush_to_vm（VictoriaMetrics）行为
  - 创建 `basic_tool/metrics/writer.py`，包含 `MetricsWriter` 类
  - 实现 `init()/close()` 生命周期、`write_batch()`、`flush_to_vm()` 方法
  - **修复 flush_to_vm 客户端复用**：不在每次调用时创建新 `httpx.AsyncClient`，改为在 `init()` 中创建
  - 添加 `cache` property（初始化检查）
  - 测试使用 fakeredis mock Redis、httpx.MockTransport mock VM
  - 测试覆盖：write_batch 写入 Stream、flush_to_vm 格式化、空 batch 处理、Redis pub/sub 通知

  **Must NOT do**:
  - 不添加重试逻辑
  - 不修改 `write_batch` 的 Redis Stream 操作方式（必须用 xadd）
  - 不添加自定义异常类

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 双写逻辑（Redis + VM）+ 客户端生命周期修复 + Stream 交互
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `basic_tool/redis/client/_pubsub.py` — Redis 操作 Mixin 模式
  - `basic_tool/metrics/writer.py` (设计文档) — 完整代码在第 301-407 行

  **API/Type References**:
  - `basic_tool/metrics/config.py` (Task 2) — MetricsConfig
  - `basic_tool/metrics/models.py` (Task 3) — MetricBatch, MetricPoint
  - `basic_tool/redis/client/_stream.py` (Task 1) — Cache.xadd() 方法

  **Test References**:
  - `tests/redis/test_client.py` — fakeredis Cache fixture
  - `tests/http_client/test_client.py` — MockTransport 模式

  **WHY Each Reference Matters**:
  - 设计文档第 301-407 行提供了基础实现，但需修复 flush_to_vm 的客户端创建问题
  - fakeredis 用于 mock Redis Stream 操作
  - MockTransport 用于 mock VictoriaMetrics HTTP API

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: write_batch 写入 Redis Stream
    Tool: Bash
    Preconditions: fakeredis 环境可用
    Steps:
      1. 创建 MetricsWriter 实例，注入 fakeredis Cache
      2. batch = MetricBatch(points=[MetricPoint(name="cpu", value=80.5)], source="test_svc")
      3. count = await writer.write_batch(batch)
      4. assert count == 1
      5. 验证 Redis Stream 中存在数据
    Expected Result: 1 条数据写入 Stream
    Evidence: .sisyphus/evidence/task-5-write-batch.txt

  Scenario: write_batch 空 batch 短路
    Tool: Bash
    Steps:
      1. batch = MetricBatch(points=[], source="test")
      2. count = await writer.write_batch(batch)
      3. assert count == 0
    Expected Result: 空 batch 返回 0，不报错
    Evidence: .sisyphus/evidence/task-5-empty-batch.txt

  Scenario: flush_to_vm 格式化 Prometheus exposition
    Tool: Bash
    Steps:
      1. 用 MockTransport mock VictoriaMetrics /api/v1/import/prometheus 端点
      2. batch = MetricBatch(points=[MetricPoint(name="req", value=100, labels={"method": "GET"}, type=MetricType.COUNTER)])
      3. count = await writer.flush_to_vm(batch)
      4. assert count == 1
      5. 验证 MockTransport 收到的请求体包含 Prometheus exposition 格式
    Expected Result: 正确格式化为 Prometheus text format 并发送
    Evidence: .sisyphus/evidence/task-5-flush-to-vm.txt

  Scenario: flush_to_vm 复用 httpx 客户端
    Tool: Bash
    Steps:
      1. writer = MetricsWriter(config)
      2. await writer.init()
      3. 验证 writer._http 存在（init 时创建，非 flush_to_vm 内创建）
    Expected Result: httpx.AsyncClient 在 init() 时创建一次
    Evidence: .sisyphus/evidence/task-5-client-reuse.txt
  ```

  **Commit**: YES (与 Tasks 4, 6, 7 合并)
  - Message: `feat(metrics): add collector, writer, reader, alerter`
  - Files: `basic_tool/metrics/writer.py`

- [x] 6. MetricsReader 查询层

  **What to do**:
  - TDD: 先写测试验证 query_range、query_instant、label_values、series 方法
  - 创建 `basic_tool/metrics/reader.py`，包含 `MetricsReader` 类
  - 实现 `init()/close()` 生命周期、`query_range()/query_instant()/label_values()/series()` 方法
  - 添加 `client` property（初始化检查）
  - 测试使用 `httpx.MockTransport` mock VictoriaMetrics API 响应
  - 测试覆盖：范围查询、瞬时查询、label 查询、series 查询、错误响应处理

  **Must NOT do**:
  - 不添加 PromQL 语法验证
  - 不添加缓存层
  - 不添加自定义异常类（使用 httpx 的 raise_for_status）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 4 个查询方法 + Mock 响应构造，工作量适中
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 2, 3

  **References**:

  **Pattern References**:
  - `basic_tool/metrics/reader.py` (设计文档) — 完整代码在第 413-525 行

  **API/Type References**:
  - `basic_tool/metrics/config.py` (Task 2) — MetricsConfig
  - `basic_tool/metrics/models.py` (Task 3) — QueryResult, TimeRange

  **Test References**:
  - `tests/http_client/test_client.py` — httpx MockTransport 模式

  **WHY Each Reference Matters**:
  - 设计文档第 413-525 行提供了完整实现
  - MockTransport 用于模拟 VictoriaMetrics API 响应

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: query_range 返回结构化结果
    Tool: Bash
    Steps:
      1. Mock VictoriaMetrics /api/v1/query_range 返回标准响应
      2. reader = MetricsReader(config); await reader.init()
      3. results = await reader.query_range("up", TimeRange(start=..., end=..., step="1m"))
      4. assert len(results) > 0
      5. assert isinstance(results[0], QueryResult)
      6. assert results[0].metric["__name__"] == "up"
    Expected Result: QueryResult 列表包含 metric 和 values
    Evidence: .sisyphus/evidence/task-6-query-range.txt

  Scenario: query_instant 瞬时查询
    Tool: Bash
    Steps:
      1. Mock VictoriaMetrics /api/v1/query 响应
      2. results = await reader.query_instant("up")
      3. assert len(results) > 0
      4. assert len(results[0].values) == 1  # 瞬时只有一个点
    Expected Result: 单个时间点的 QueryResult
    Evidence: .sisyphus/evidence/task-6-query-instant.txt

  Scenario: label_values 获取标签值
    Tool: Bash
    Steps:
      1. Mock /api/v1/label/__name__/values 响应
      2. values = await reader.label_values("__name__")
      3. assert "up" in values
    Expected Result: 字符串列表
    Evidence: .sisyphus/evidence/task-6-label-values.txt

  Scenario: 未初始化时访问 client 报错
    Tool: Bash
    Steps:
      1. reader = MetricsReader(config)  # 不调用 init()
      2. with pytest.raises(RuntimeError, match="未初始化"): _ = reader.client
    Expected Result: RuntimeError
    Evidence: .sisyphus/evidence/task-6-not-initialized.txt
  ```

  **Commit**: YES (与 Tasks 4, 5, 7 合并)
  - Message: `feat(metrics): add collector, writer, reader, alerter`
  - Files: `basic_tool/metrics/reader.py`

- [x] 7. AlertEvaluator 告警评估器

  **What to do**:
  - TDD: 先写测试验证条件解析、告警触发、pending→firing 转换、cooldown、恢复、边界情况
  - 创建 `basic_tool/metrics/alerter.py`，包含 `AlertEvaluator` 类
  - 实现 `evaluate()/get_state()/get_all_states()` 方法
  - 实现 `_parse_condition()` 和 `_parse_duration()` 静态方法
  - 添加 module-level docstring
  - 测试覆盖：条件解析（>/>=/</<=/==/!=/）、状态转换（OK→PENDING→FIRING→OK）、cooldown、duration 阈值、无效条件/时长格式、NaN 值行为
  - **注意**：纯同步逻辑，不依赖 async、数据库或网络

  **Must NOT do**:
  - 不添加 async 方法
  - 不添加持久化（Redis/DB）
  - 不添加调度（定时调用）
  - 不添加通知发送逻辑
  - 不支持负数阈值（设计文档 regex 不支持，这是已知限制）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 状态机逻辑复杂（pending/firing/cooldown/resolved 转换），需仔细测试边界
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: Task 10
  - **Blocked By**: Task 3 (models)

  **References**:

  **Pattern References**:
  - `basic_tool/metrics/alerter.py` (设计文档) — 完整代码在第 532-674 行

  **API/Type References**:
  - `basic_tool/metrics/models.py` (Task 3) — AlertRule, AlertEvent, AlertState

  **WHY Each Reference Matters**:
  - 设计文档第 532-674 行提供了完整实现
  - AlertRule 和 AlertState 是 evaluate 方法的输入输出

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 条件触发 — 首次进入 PENDING
    Tool: Bash
    Steps:
      1. evaluator = AlertEvaluator()
      2. rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80")
      3. event = evaluator.evaluate(rule, current_value=95.0, now=datetime(2024, 1, 1, 12, 0))
      4. assert event is not None
      5. assert event.state == AlertState.PENDING
      6. assert event.value == 95.0
      7. assert event.threshold == 80.0
    Expected Result: 首次超阈值返回 PENDING 事件
    Evidence: .sisyphus/evidence/task-7-pending.txt

  Scenario: 持续超阈值 — PENDING → FIRING（持续时间达标）
    Tool: Bash
    Steps:
      1. evaluator = AlertEvaluator()
      2. rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80", duration="5m")
      3. first = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
      4. assert first.state == AlertState.PENDING
      5. second = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 5))
      6. assert second.state == AlertState.FIRING
    Expected Result: 持续 5 分钟后触发 FIRING
    Evidence: .sisyphus/evidence/task-7-firing.txt

  Scenario: 恢复正常 — FIRING → OK
    Tool: Bash
    Steps:
      1. 先触发到 FIRING 状态
      2. event = evaluator.evaluate(rule, 50.0, now=datetime(2024, 1, 1, 12, 10))
      3. assert event.state == AlertState.OK
      4. assert event.resolved_at is not None
    Expected Result: 值恢复正常返回 OK 事件
    Evidence: .sisyphus/evidence/task-7-resolved.txt

  Scenario: cooldown 期间抑制重复告警
    Tool: Bash
    Steps:
      1. 先触发 FIRING
      2. 在 cooldown 时间内的再次评估返回 None
      3. event = evaluator.evaluate(rule, 95.0, now=cooldown 内的时间)
      4. assert event is None
    Expected Result: 冷却期内返回 None
    Evidence: .sisyphus/evidence/task-7-cooldown.txt

  Scenario: 无效条件格式报错
    Tool: Bash
    Steps:
      1. rule = AlertRule(name="bad", metric="x", condition="invalid")
      2. with pytest.raises(ValueError, match="Invalid condition"): evaluator.evaluate(rule, 50.0)
    Expected Result: ValueError
    Evidence: .sisyphus/evidence/task-7-invalid-condition.txt

  Scenario: NaN 值不触发告警
    Tool: Bash
    Steps:
      1. event = evaluator.evaluate(rule, float('nan'))
      2. assert event is None  # NaN > 80 为 False
    Expected Result: NaN 比较为 False，不触发
    Evidence: .sisyphus/evidence/task-7-nan.txt
  ```

  **Commit**: YES (与 Tasks 4-6 合并)
  - Message: `feat(metrics): add collector, writer, reader, alerter`
  - Files: `basic_tool/metrics/alerter.py`

- [x] 8. Scraper（Prometheus exposition 便捷函数）

  **What to do**:
  - TDD: 先写测试验证 `generate_exposition()` 委托调用
  - 创建 `basic_tool/metrics/scraper.py`，包含 `generate_exposition()` 函数
  - 添加 module-level docstring
  - 测试：验证函数正确调用 `collector.prometheus_exposition()` 并返回结果

  **Must NOT do**:
  - 不添加配置或抽象层
  - 不添加 `generate_exposition` 到 `__init__.py` 导出（设计文档未包含）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单函数文件，逻辑极简
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11)
  - **Blocks**: Task 10
  - **Blocked By**: Task 4 (collector)

  **References**:

  **Pattern References**:
  - `basic_tool/metrics/scraper.py` (设计文档) — 完整代码在第 680-692 行

  **API/Type References**:
  - `basic_tool/metrics/collector.py` (Task 4) — MetricsCollector.prometheus_exposition()

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: generate_exposition 委托调用
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999")
      2. collector.counter("test", value=5)
      3. output = generate_exposition(collector)
      4. assert "test" in output
      5. assert "5" in output
    Expected Result: 返回 collector 的 prometheus_exposition() 输出
    Evidence: .sisyphus/evidence/task-8-scraper.txt

  Scenario: 空 collector 返回空 exposition
    Tool: Bash
    Steps:
      1. collector = MetricsCollector(MetricsConfig(service_name="test"), endpoint="http://localhost:9999")
      2. output = generate_exposition(collector)
      3. assert output == "\n"
    Expected Result: 仅换行符
    Evidence: .sisyphus/evidence/task-8-scraper-empty.txt
  ```

  **Commit**: YES (与 Tasks 9-11 合并)
  - Message: `feat(metrics): complete module with scraper, health, exports, docs`
  - Files: `basic_tool/metrics/scraper.py`

- [x] 9. MetricsHealth 健康检查

  **What to do**:
  - TDD: 先写测试验证 check() 方法的健康状态返回
  - 创建 `basic_tool/metrics/health.py`，包含 `MetricsHealth` 类
  - 实现 `__init__(writer, reader)` 和 `async def check()` 方法
  - check() 返回 dict，检查 VictoriaMetrics 和 Redis 连接状态
  - 测试 mock writer 和 reader 的内部属性
  - 测试覆盖：正常健康、VM 不可用、Redis 不可用、writer/reader 为 None

  **Must NOT do**:
  - 不修改 writer/reader 的封装来添加 property（保留按设计访问内部属性）
  - 不添加 alert evaluator 到 health check（设计文档未包含）
  - 不抛出异常（返回 dict）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单类文件，模式与现有 health.py 一致
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 10, 11)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 5, 6

  **References**:

  **Pattern References**:
  - `basic_tool/redis/health.py` — 现有健康检查模式（返回 dict，不抛异常）
  - `basic_tool/metrics/health.py` (设计文档) — 完整代码在第 698-753 行

  **API/Type References**:
  - `basic_tool/metrics/writer.py` (Task 5) — MetricsWriter
  - `basic_tool/metrics/reader.py` (Task 6) — MetricsReader

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 全部健康
    Tool: Bash
    Steps:
      1. Mock writer（_initialized=True, cache.client.ping() 返回 True）
      2. Mock reader（_http 存在, client.get() 返回 status_code=200）
      3. health = MetricsHealth(writer, reader)
      4. result = await health.check()
      5. assert result["ok"] is True
      6. assert result["components"]["victoriametrics"]["ok"] is True
      7. assert result["components"]["redis"]["ok"] is True
    Expected Result: ok=True, 两个组件都健康
    Evidence: .sisyphus/evidence/task-9-health-ok.txt

  Scenario: VictoriaMetrics 不可用
    Tool: Bash
    Steps:
      1. Mock reader client.get() 抛出异常
      2. result = await health.check()
      3. assert result["ok"] is False
      4. assert result["components"]["victoriametrics"]["ok"] is False
    Expected Result: ok=False, VM 组件标记为不健康
    Evidence: .sisyphus/evidence/task-9-health-vm-down.txt

  Scenario: writer/reader 为 None
    Tool: Bash
    Steps:
      1. health = MetricsHealth()
      2. result = await health.check()
      3. assert result["ok"] is True  # 无组件检查
      4. assert result["components"] == {}
    Expected Result: 无组件时 ok=True
    Evidence: .sisyphus/evidence/task-9-health-none.txt
  ```

  **Commit**: YES (与 Tasks 8, 10, 11 合并)
  - Message: `feat(metrics): complete module with scraper, health, exports, docs`
  - Files: `basic_tool/metrics/health.py`

- [x] 10. __init__.py 模块导出

  **What to do**:
  - 创建 `basic_tool/metrics/__init__.py`
  - 遵循 SDK 惯例：module docstring（中文描述 + Usage example 用 `::`）+ re-exports + `__all__`
  - 导出所有设计文档 `__all__` 中列出的公开 API（13 个名称）
  - **不**导出 `generate_exposition`（设计文档 `__all__` 未包含）

  **Must NOT do**:
  - 不添加 `generate_exposition` 到导出
  - 不添加设计文档未定义的导出名称

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件导出，模式明确
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (依赖所有 Wave 2 组件)
  - **Parallel Group**: Wave 3 (after Tasks 8, 9)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 4, 5, 6, 7, 8, 9

  **References**:

  **Pattern References**:
  - `basic_tool/redis/__init__.py` — `__init__.py` 模板（docstring + imports + `__all__`）
  - `basic_tool/http_client/__init__.py` — 另一个参考（包含 usage example `::`）
  - `basic_tool/metrics/__init__.py` (设计文档) — 完整代码在第 759-791 行

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 完整导入测试
    Tool: Bash
    Steps:
      1. python -c "from basic_tool.metrics import MetricsCollector, MetricsConfig, MetricsWriter, MetricsReader, AlertEvaluator, MetricsHealth, MetricPoint, MetricBatch, MetricType, TimeRange, QueryResult, AlertRule, AlertState, AlertEvent; print('ok')"
    Expected Result: 输出 "ok"
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-10-full-import.txt

  Scenario: __all__ 包含 13 个名称
    Tool: Bash
    Steps:
      1. python -c "from basic_tool.metrics import __all__; assert len(__all__) == 13; print(f'exports: {len(__all__)}')"
    Expected Result: 输出 "exports: 13"
    Evidence: .sisyphus/evidence/task-10-all-count.txt

  Scenario: generate_exposition 不在公开导出中
    Tool: Bash
    Steps:
      1. python -c "from basic_tool.metrics import __all__; assert 'generate_exposition' not in __all__; print('ok')"
    Expected Result: 输出 "ok"
    Evidence: .sisyphus/evidence/task-10-no-scraper-export.txt
  ```

  **Commit**: YES (与 Tasks 8, 9, 11 合并)
  - Message: `feat(metrics): complete module with scraper, health, exports, docs`
  - Files: `basic_tool/metrics/__init__.py`

- [x] 11. README.md + pyproject.toml + 模块注册

  **What to do**:
  - 创建 `basic_tool/metrics/README.md`，遵循 CLAUDE.md 要求：
    - 模块功能描述
    - 所有公开 API 签名和说明
    - 使用示例
  - 更新 `pyproject.toml`：仅修改 `version = "0.4.0"` → `version = "0.5.0"`
  - 更新 `basic_tool/__init__.py`：在 docstring 中添加 `metrics` 模块描述
  - 验证所有最终检查命令

  **Must NOT do**:
  - 不修改 pyproject.toml 中 version 以外的任何内容
  - 不给 `basic_tool/__init__.py` 添加 `__all__`、imports 或 exports（仅修改 docstring）
  - 不添加新依赖

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 文档编写 + 单行版本修改
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `writing`: 文档简短，quick 即可

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9 — 但 Task 10 必须先完成)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 10

  **References**:

  **Pattern References**:
  - `basic_tool/redis/README.md` — README 格式参考（表格 + API 列表）
  - `basic_tool/__init__.py` — 现有 docstring 格式（模块列表）
  - `pyproject.toml` — 当前版本字段位置

  **WHY Each Reference Matters**:
  - `redis/README.md` 是 README 模板
  - `__init__.py` 展示了在哪里添加 metrics 描述

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README.md 存在且非空
    Tool: Bash
    Steps:
      1. test -f basic_tool/metrics/README.md
      2. wc -l basic_tool/metrics/README.md → 行数 > 20
    Expected Result: README.md 存在且内容充实
    Evidence: .sisyphus/evidence/task-11-readme-exists.txt

  Scenario: 版本号正确
    Tool: Bash
    Steps:
      1. python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['version']=='0.5.0'; print('version ok')"
    Expected Result: 输出 "version ok"
    Evidence: .sisyphus/evidence/task-11-version.txt

  Scenario: 模块注册
    Tool: Bash
    Steps:
      1. grep -c "metrics" basic_tool/__init__.py → 至少 1 行
    Expected Result: docstring 中包含 metrics 描述
    Evidence: .sisyphus/evidence/task-11-module-registered.txt

  Scenario: 全量测试通过
    Tool: Bash
    Steps:
      1. pytest tests/ -v --tb=short
    Expected Result: 所有测试通过（包括现有测试 + 新测试）
    Evidence: .sisyphus/evidence/task-11-full-tests.txt
  ```

  **Commit**: YES (与 Tasks 8, 9, 10 合并)
  - Message: `feat(metrics): complete module with scraper, health, exports, docs`
  - Files: `basic_tool/metrics/README.md`, `basic_tool/metrics/__init__.py`, `basic_tool/__init__.py`, `pyproject.toml`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run import command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v --tb=short`. Review all changed files for: `as any`/type ignores, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify module-level docstrings on all new files. Verify no `eval(` in collector.py.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute key verification scenarios: (1) full import test, (2) MetricsConfig instantiation, (3) AlertEvaluator condition parsing, (4) Collector buffer + prometheus exposition, (5) no eval() in codebase. Save evidence to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual files. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Verify only StreamMixin line was added to redis client/__init__.py (no other changes). Verify pyproject.toml only changed version.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Task 1**: `feat(redis): add StreamMixin with xadd method` — `basic_tool/redis/client/_stream.py`, `basic_tool/redis/client/__init__.py`, `basic_tool/redis/README.md`, `tests/redis/test_stream.py`
- **Tasks 2-3**: `feat(metrics): add config and data models` — `basic_tool/metrics/config.py`, `basic_tool/metrics/models.py`
- **Tasks 4-7**: `feat(metrics): add collector, writer, reader, alerter` — 4 files
- **Tasks 8-11**: `feat(metrics): complete module with scraper, health, exports, docs` — remaining files + updates
- Pre-commit: `pytest tests/ -v`

---

## Success Criteria

### Verification Commands
```bash
pytest tests/ -v                                                    # Expected: all pass
python -c "from basic_tool.metrics import MetricsCollector, MetricsConfig, MetricsWriter, MetricsReader, AlertEvaluator, MetricsHealth, MetricPoint, MetricBatch, MetricType, TimeRange, QueryResult, AlertRule, AlertState, AlertEvent; print('ok')"  # Expected: ok
python -c "from basic_tool.redis import Cache; assert 'xadd' in dir(Cache); print('StreamMixin ok')"  # Expected: StreamMixin ok
grep -c 'eval(' basic_tool/metrics/collector.py                     # Expected: 0
python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['version']=='0.5.0'; print('version ok')"  # Expected: version ok
test -f basic_tool/metrics/README.md && echo "README ok"            # Expected: README ok
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] No eval() in collector.py
- [x] Version 0.5.0
- [x] README.md exists
