# basic_tool.metrics — 指标可观测性

指标采集、Redis Streams 缓冲、VictoriaMetrics 持久化、PromQL 查询、告警评估、健康检查。

提供完整的指标可观测性链路：内存采集 → 缓冲 → 持久化 → 查询 → 告警。

## 依赖

- `redis[hiredis]>=5.0.0` — Redis 异步客户端（Stream 缓冲）
- `httpx>=0.27.0` — VictoriaMetrics HTTP API 调用
- `orjson>=3.9.0` — 高性能 JSON 序列化
- `pydantic>=2.0.0` — 数据模型校验
- `loguru>=0.7.0` — 结构化日志

## 模块结构

```
basic_tool/metrics/
├── __init__.py        # 统一导出（14 个公开名称）
├── config.py          # MetricsConfig 配置类
├── models.py          # 数据模型（MetricPoint/MetricBatch/TimeRange/QueryResult/Alert*）
├── collector.py       # MetricsCollector 采集器
├── writer.py          # MetricsWriter 写入器
├── reader.py          # MetricsReader 查询器
├── alerter.py         # AlertEvaluator 告警评估器
├── scraper.py         # generate_exposition 便捷函数（内部，不导出）
└── health.py          # MetricsHealth 健康检查
```

## API 文档

---

### `config.py` — MetricsConfig

```python
class MetricsConfig(BaseModel):
    vm_url: str = "http://localhost:8428"      # VictoriaMetrics 地址
    redis_url: str = "redis://localhost:6379/0" # Redis 连接（Stream 缓冲）
    service_name: str = "default"              # 当前服务名（作为指标 label）
    flush_interval: float = 5.0                # 自动刷新间隔（秒）
    flush_batch_size: int = 1000               # 每批最大刷新点数
    stream_prefix: str = "metrics"             # Redis Stream key 前缀
    stream_max_len: int = 100_000              # Redis Stream 最大长度
    alert_interval: float = 30.0               # 告警评估间隔（秒）
```

---

### `models.py` — 数据模型

#### MetricType（指标类型枚举）

```python
class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
```

#### MetricPoint（单个指标数据点）

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str` | 指标名称 |
| `value` | `float` | 指标值 |
| `type` | `MetricType` | 指标类型，默认 GAUGE |
| `labels` | `dict[str, str]` | 标签键值对，默认空字典 |
| `timestamp` | `datetime \| None` | 时间戳，默认 None（写入时由后端补全） |

#### MetricBatch（指标批次）

| 字段 | 类型 | 说明 |
|---|---|---|
| `points` | `list[MetricPoint]` | 数据点列表 |
| `source` | `str` | 数据来源标识，默认 "unknown" |

#### TimeRange（查询时间范围）

| 字段 | 类型 | 说明 |
|---|---|---|
| `start` | `datetime` | 起始时间 |
| `end` | `datetime` | 结束时间 |
| `step` | `str` | 步长（PromQL 格式，如 "1m"），默认 "1m" |

#### QueryResult（查询结果）

| 字段 | 类型 | 说明 |
|---|---|---|
| `metric` | `dict[str, str]` | 指标名及标签（如 `{"__name__": "up", "job": "node"}`） |
| `values` | `list[list[Any]]` | 时间序列数据点列表，每项为 `[timestamp, value]` |

#### AlertRule（告警规则）

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str` | 规则名称 |
| `metric` | `str` | 监控的指标名 |
| `condition` | `str` | 触发条件（如 `"> 80"`、`"<= 0.1"`） |
| `duration` | `str` | 持续时间阈值（如 `"5m"`），默认 "5m" |
| `cooldown` | `str` | 冷却时间（避免重复告警，如 `"10m"`），默认 "10m" |
| `enabled` | `bool` | 是否启用，默认 True |
| `channels` | `list[str]` | 通知渠道列表，默认空 |

#### AlertState（告警状态枚举）

```python
class AlertState(str, Enum):
    OK = "ok"
    PENDING = "pending"
    FIRING = "firing"
```

#### AlertEvent（告警事件）

| 字段 | 类型 | 说明 |
|---|---|---|
| `rule_name` | `str` | 触发的规则名 |
| `state` | `AlertState` | 当前告警状态 |
| `value` | `float` | 触发时的指标值 |
| `threshold` | `float` | 规则阈值 |
| `fired_at` | `datetime \| None` | 告警触发时间 |
| `resolved_at` | `datetime \| None` | 告警恢复时间（未恢复时为 None） |

---

### `collector.py` — MetricsCollector

```python
class MetricsCollector:
    def __init__(self, config: MetricsConfig, endpoint: str)
```

内存采集器，提供 counter/gauge/histogram 记录、Prometheus exposition 输出、后台定时刷新。

#### 生命周期

| 方法 | 说明 |
|---|---|
| `async init() -> None` | 初始化 httpx 客户端，启动后台定时刷新任务 |
| `async close() -> None` | 取消后台任务，释放 httpx 客户端（幂等） |

#### 采集方法

| 方法 | 说明 |
|---|---|
| `counter(name, value=1.0, labels=None) -> None` | 记录 counter 类型指标点 |
| `gauge(name, value, labels=None) -> None` | 记录 gauge 类型指标点 |
| `histogram(name, value, labels=None) -> None` | 记录 histogram 类型指标点 |
| `prometheus_exposition() -> str` | 生成 Prometheus text exposition 格式文本（相同标签集合聚合求和） |

---

### `writer.py` — MetricsWriter

```python
class MetricsWriter:
    def __init__(self, config: MetricsConfig, cache: Cache | None = None)
```

指标写入器，双写 Redis Streams（缓冲）和 VictoriaMetrics（持久化）。

#### 生命周期

| 方法 | 说明 |
|---|---|
| `async init() -> None` | 初始化 httpx 客户端（指向 VictoriaMetrics） |
| `async close() -> None` | 关闭 httpx 客户端（幂等） |
| `cache -> Cache` | Redis Cache 属性，未初始化时抛 RuntimeError |

#### 写入方法

| 方法 | 说明 |
|---|---|
| `async write_batch(batch: MetricBatch) -> int` | 将一批指标点写入 Redis Stream（每个 point 序列化为一个 entry） |
| `async flush_to_vm(batch: MetricBatch) -> int` | 将一批指标点以 Prometheus exposition 格式 POST 到 VictoriaMetrics |

---

### `reader.py` — MetricsReader

```python
class MetricsReader:
    def __init__(self, config: MetricsConfig)
```

指标查询器，通过 VictoriaMetrics HTTP API 执行 PromQL 查询。

#### 生命周期

| 方法 | 说明 |
|---|---|
| `async init() -> None` | 初始化 httpx 客户端（指向 VictoriaMetrics） |
| `async close() -> None` | 关闭 httpx 客户端（幂等） |
| `client -> httpx.AsyncClient` | 已初始化的 httpx 客户端属性，未初始化时抛 RuntimeError |

#### 查询方法

| 方法 | 说明 |
|---|---|
| `async query_range(query: str, time_range: TimeRange) -> list[QueryResult]` | PromQL 范围查询（matrix），返回时间序列列表 |
| `async query_instant(query: str) -> list[QueryResult]` | PromQL 瞬时查询（vector），每个结果恰好 1 个数据点 |
| `async label_values(label: str) -> list[str]` | 标签值查询，返回指定 label 的所有可选值 |

---

### `alerter.py` — AlertEvaluator

```python
class AlertEvaluator:
    def __init__(self)
```

告警评估器，管理状态机（OK → PENDING → FIRING → OK），纯同步逻辑，不依赖 async/网络。

状态流转：
- **OK → PENDING**：指标首次触发阈值，记录首次违规时间
- **PENDING → FIRING**：违规持续超过 `duration` 阈值
- **PENDING/FIRING → OK**：指标恢复正常，返回 resolved 事件
- **FIRING + 冷却**：冷却期内抑制重复告警

| 方法 | 说明 |
|---|---|
| `evaluate(rule: AlertRule, current_value: float, now=None) -> AlertEvent \| None` | 评估规则，返回状态变化事件或 None（无变化/被冷却抑制） |
| `get_state(rule_name: str) -> AlertState` | 获取指定规则的当前状态（未跟踪返回 OK） |
| `get_all_states() -> dict[str, AlertState]` | 获取所有规则状态（防御性拷贝） |

条件格式支持：`> >= < <= == !=` 配合数字阈值（如 `"> 80"`、`"<= 0.1"`）。
时长格式支持：`s m h d`（如 `"5m"`、`"30s"`、`"2h"`、`"1d"`）。

---

### `health.py` — MetricsHealth

```python
class MetricsHealth:
    def __init__(self, writer: MetricsWriter | None = None, reader: MetricsReader | None = None)
```

健康检查器，检查 VictoriaMetrics（reader）和 Redis（writer）连接状态。

| 方法 | 说明 |
|---|---|
| `async check() -> dict` | 返回 `{"ok": bool, "components": {...}}`，ok 为所有组件健康的 AND。writer/reader 为 None 时跳过该组件 |

返回示例：

```python
{
    "ok": True,
    "components": {
        "victoriametrics": {"ok": True},
        "redis": {"ok": True},
    },
}
```

---

## 使用示例

### 采集 + Prometheus exposition 输出

```python
from basic_tool.metrics import MetricsCollector, MetricsConfig

config = MetricsConfig(service_name="my_app", flush_interval=10.0)
collector = MetricsCollector(config, endpoint="http://vm:8428/api/v1/import/prometheus")
await collector.init()

collector.counter("http_requests_total", labels={"method": "GET"})
collector.gauge("queue_depth", 42)
collector.histogram("request_duration_seconds", 0.15)

text = collector.prometheus_exposition()  # Prometheus 格式输出（pull 抓取）
await collector.close()
```

### 双写 Redis Streams + VictoriaMetrics

```python
from basic_tool.metrics import MetricsWriter, MetricBatch, MetricPoint
from basic_tool.redis import Cache, RedisConfig

cache = Cache(RedisConfig(url="redis://localhost:6379/0"))
await cache.init()

writer = MetricsWriter(MetricsConfig(vm_url="http://vm:8428"), cache=cache)
await writer.init()

batch = MetricBatch(
    points=[
        MetricPoint(name="cpu_usage", value=80.5, labels={"host": "node1"}),
        MetricPoint(name="mem_usage", value=60.0, labels={"host": "node1"}),
    ],
    source="my_app",
)
await writer.write_batch(batch)    # 写入 Redis Stream（缓冲）
await writer.flush_to_vm(batch)    # 刷新到 VictoriaMetrics（持久化）
await writer.close()
```

### PromQL 查询

```python
from datetime import datetime
from basic_tool.metrics import MetricsReader, TimeRange

reader = MetricsReader(MetricsConfig(vm_url="http://vm:8428"))
await reader.init()

# 范围查询
results = await reader.query_range(
    "rate(http_requests_total[5m])",
    TimeRange(start=datetime(2024, 1, 1), end=datetime(2024, 1, 2), step="1m"),
)
for r in results:
    print(r.metric, r.values)

# 瞬时查询
now_results = await reader.query_instant("up")

# 标签值查询
names = await reader.label_values("__name__")
await reader.close()
```

### 告警评估

```python
from basic_tool.metrics import AlertEvaluator, AlertRule, AlertState

evaluator = AlertEvaluator()
rule = AlertRule(name="high_cpu", metric="cpu_usage", condition="> 80", duration="5m", cooldown="10m")

# 连续违规：OK → PENDING → FIRING
event1 = evaluator.evaluate(rule, current_value=95.0)  # PENDING
event2 = evaluator.evaluate(rule, current_value=95.0)  # None（等待 duration）
# ... 持续违规超过 duration 后 ...
event3 = evaluator.evaluate(rule, current_value=95.0)  # FIRING

if event3 and event3.state == AlertState.FIRING:
    send_notification(event3)

# 恢复正常
event4 = evaluator.evaluate(rule, current_value=50.0)  # OK（resolved 事件）
```

### 健康检查

```python
from basic_tool.metrics import MetricsHealth

health = MetricsHealth(writer=writer, reader=reader)
result = await health.check()
# {"ok": True, "components": {"victoriametrics": {"ok": True}, "redis": {"ok": True}}}
```
