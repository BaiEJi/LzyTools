# basic_tool.id_generator — 分布式链路追踪与唯一 ID 生成

提供分布式链路追踪（W3C Trace Context）和业务唯一 ID 生成（Snowflake）两大能力，纯 Python 实现，零外部依赖。

## 依赖

- `pydantic>=2.0.0` — 配置校验

## 模块结构

```
basic_tool/id_generator/
├── __init__.py        # 统一导出
├── config.py          # IDConfig 配置类
├── trace.py           # TraceContext 链路追踪上下文
├── generator.py       # IDGenerator + TraceGenerator
└── README.md          # 本文档
```

## API 文档

---

### `config.py` — IDConfig

```python
class IDConfig(BaseModel):
    worker_id: int = 0       # 工作节点 ID（0-1023），分布式部署时必须唯一
    epoch: int = 1704067200000  # 自定义 epoch（毫秒），默认 2024-01-01
```

---

### `trace.py` — TraceContext

```python
class TraceContext:
    __slots__ = ("trace_id", "span_id", "parent_span_id")
```

| 方法 | 签名 | 说明 |
|---|---|---|
| `root()` | `@classmethod -> TraceContext` | 创建新根 trace |
| `child_span()` | `-> TraceContext` | 创建子 span，共享 trace_id |
| `to_traceparent()` | `-> str` | 序列化为 W3C traceparent header |
| `from_traceparent()` | `@classmethod (header: str) -> TraceContext` | 从 header 解析 |

**属性**：`trace_id: str`（32 位 hex）、`span_id: str`（16 位 hex）、`parent_span_id: str`

---

### `generator.py` — IDGenerator

```python
class IDGenerator:
    def __init__(self, config: IDConfig)
```

| 方法 | 签名 | 说明 |
|---|---|---|
| `new()` | `-> int` | 生成一个 64-bit 唯一 ID |
| `batch(count)` | `(count: int) -> list[int]` | 批量生成，减少锁竞争 |
| `new_prefixed(prefix)` | `(prefix: str) -> str` | 带业务前缀的字符串 ID |

64-bit 布局：`[1 bit unused][41 bits timestamp][10 bits worker_id][12 bits sequence]`

---

### `generator.py` — TraceGenerator

```python
class TraceGenerator:
    ...
```

| 方法 | 签名 | 说明 |
|---|---|---|
| `new_trace()` | `-> TraceContext` | 创建全新根 trace |
| `trace_id()` | `-> str` | 生成 32 位 hex trace_id |
| `span_id()` | `-> str` | 生成 16 位 hex span_id |
| `from_traceparent()` | `@staticmethod (header: str) -> TraceContext` | 从 header 解析 |

---

## 使用示例

### 链路追踪

```python
from basic_tool.id_generator import TraceGenerator, TraceContext

gen = TraceGenerator()

# 入口服务：创建新的 trace
ctx = gen.new_trace()

# 传播到下游：写入 HTTP header
headers = {"traceparent": ctx.to_traceparent()}

# 下游服务：从 header 解析并创建子 span
ctx = TraceContext.from_traceparent(headers["traceparent"])
child = ctx.child_span()
```

### 业务唯一 ID

```python
from basic_tool.id_generator import IDGenerator, IDConfig

config = IDConfig(worker_id=1)
gen = IDGenerator(config)

# 单个生成
order_id = gen.new()              # 7350283750400000001

# 批量生成
ids = gen.batch(1000)             # 1000 个唯一 ID

# 带前缀的业务 ID
order_no = gen.new_prefixed("ORD")   # "ORD_7350283750400000001"
```

### FastAPI 集成

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from basic_tool.id_generator import IDGenerator, IDConfig, TraceGenerator, TraceContext

config = IDConfig(worker_id=1)
id_gen = IDGenerator(config)
trace_gen = TraceGenerator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    tp = request.headers.get("traceparent")
    if tp:
        ctx = TraceContext.from_traceparent(tp).child_span()
    else:
        ctx = trace_gen.new_trace()
    request.state.trace = ctx
    response = await call_next(request)
    response.headers["traceparent"] = ctx.to_traceparent()
    return response

@app.post("/orders")
async def create_order(request: Request):
    ctx: TraceContext = request.state.trace
    order_id = id_gen.new_prefixed("ORD")
    return {"order_id": order_id, "trace_id": ctx.trace_id}
```
