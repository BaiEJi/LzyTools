# basic_tool.context — 请求级上下文管理

基于 `ContextVar` 的请求级上下文管理，支持日志注入、HTTP 头透传、任务队列序列化与 FastAPI 中间件集成。

## 依赖

- `loguru>=0.7.0` — 日志上下文注入
- `fastapi>=0.100.0` — 中间件集成
- `httpx>=0.24.0` — HTTP 头透传

## 模块结构

```
basic_tool/context/
├── __init__.py        # 统一导出
├── ctx.py             # ContextManager + request_context
├── log_extra.py       # 日志上下文注入
├── propagation.py     # HTTP 头 + 任务队列透传
└── middleware.py      # FastAPI 中间件
```

## API 文档

---

### `ctx.py` — ContextManager + request_context

```python
class ContextManager:
    def get(key: str, default: Any = None) -> Any
    def set(key: str, value: Any) -> None
    def getall() -> dict[str, Any]
    def dump() -> str
    def clear() -> None

ctx = ContextManager()  # 模块级单例

def request_context(**kwargs) -> _RequestContext
```

| 方法 | 说明 |
|---|---|
| `ctx.get(key, default=None) -> Any` | 获取单个上下文值，不存在时返回 default |
| `ctx.set(key, value) -> None` | 动态添加/更新上下文键值 |
| `ctx.getall() -> dict` | 返回完整上下文快照（副本），无活跃上下文时返回 `{}` |
| `ctx.dump() -> str` | 人类可读的上下文转储 |
| `ctx.clear() -> None` | 清空当前上下文 |
| `request_context(**kwargs) -> _RequestContext` | 创建请求上下文。未提供 `trace_id` 时自动生成 128-bit hex（W3C trace_id）。支持 `with` 和 `async with` |

---

### `log_extra.py` — 日志上下文注入

```python
def enable_log_injection() -> None
```

| 函数 | 说明 |
|---|---|
| `enable_log_injection() -> None` | 启用全局日志上下文注入。所有 loguru 日志记录会自动包含当前上下文字段。用户显式传入的 extra 优先级更高。**幂等**：多次调用不会叠加 patcher |

---

### `propagation.py` — HTTP 头 + 任务队列透传

```python
_DEFAULT_HEADER_MAP = {
    "trace_id": "X-Trace-Id",
    "span_id": "X-Span-Id",
    "tenant_id": "X-Tenant-Id",
    "user_id": "X-User-Id",
}

def get_propagation_headers(header_map=None) -> dict[str, str]
def inject_headers_to_httpx(headers=None) -> dict[str, str]
def serialize_context() -> dict[str, Any]
def deserialize_context(data: dict) -> _RequestContext
```

| 函数 | 说明 |
|---|---|
| `get_propagation_headers(header_map=None) -> dict` | 从当前上下文提取传播头。默认使用 `_DEFAULT_HEADER_MAP`，只包含当前上下文中存在的键。当 `trace_id` 与 `span_id` 同时存在时，额外重建 W3C `traceparent` 头（`00-{trace_id}-{span_id}-01`） |
| `inject_headers_to_httpx(headers=None) -> dict` | 合并上下文传播头与用户头。用户头优先（不被覆盖） |
| `serialize_context() -> dict` | 序列化当前上下文（返回副本），用于任务队列传递 |
| `deserialize_context(data) -> _RequestContext` | 从序列化数据恢复上下文，返回上下文管理器 |

---

### `middleware.py` — FastAPI 中间件

```python
class ContextMiddleware: ...          # 纯 ASGI 中间件
def setup_context_middleware(app: FastAPI) -> None
```

| 组件 | 说明 |
|---|---|
| `ContextMiddleware` | 纯 ASGI 实现。从 W3C `traceparent` 请求头解析链路上下文并创建 child span（共享上游 trace_id）；缺失或 malformed 时降级为根 trace。提取 client_ip（优先 `X-Forwarded-For`），创建请求上下文，响应头添加 `traceparent`。同时将 traceparent 写入 `scope["basic_tool.traceparent"]`，供 `ServerErrorMiddleware` 中的异常处理器读取——因为异常发生时 `BaseHTTPMiddleware` 会重新抛出异常，导致 `ServerErrorMiddleware` 生成的错误响应绕过中间件 |
| `setup_context_middleware(app)` | 便捷注册函数 |

---

## 使用示例

```python
from basic_tool.context import ctx, request_context

# 1. 基本同步上下文生命周期
with request_context(user_id=123, tenant_id="acme"):
    ctx.set("action", "login")
    assert ctx.get("user_id") == 123
    assert ctx.getall() == {"user_id": 123, "tenant_id": "acme", "trace_id": "...", "action": "login"}

# 2. 嵌套上下文（继承父上下文）
with request_context(user_id=1):
    assert ctx.get("user_id") == 1
    with request_context(user_id=2):
        assert ctx.get("user_id") == 2  # 内层覆盖
    assert ctx.get("user_id") == 1  # 退出后恢复

# 3. 异步上下文
async with request_context(trace_id="abc-123"):
    assert ctx.get("trace_id") == "abc-123"

# 4. 日志注入
from basic_tool.context import enable_log_injection
from basic_tool.logger import setup, get

setup()
enable_log_injection()
log = get()
with request_context(user_id=42, action="checkout"):
    log.info("processing payment")
    # 输出自动包含 user_id=42||action=checkout

# 5. HTTP 头传播
import httpx
from basic_tool.context import inject_headers_to_httpx

with request_context(trace_id="req-1", user_id=42):
    headers = inject_headers_to_httpx({"Accept": "application/json"})
    # headers = {"X-Trace-Id": "req-1", "X-User-Id": "42", "Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://api/users", headers=headers)

# 6. 任务队列序列化
from basic_tool.context import serialize_context, deserialize_context

with request_context(trace_id="job-1", user_id=99):
    payload = serialize_context()
    # payload 可放入 Celery/RQ 任务参数中

# 消费端（worker 进程）
with deserialize_context(payload):
    assert ctx.get("user_id") == 99

# 7. FastAPI 中间件
from fastapi import FastAPI
from basic_tool.context import setup_context_middleware

app = FastAPI()
setup_context_middleware(app)

@app.get("/api/me")
async def me():
    # 中间件已自动注入 trace_id / span_id / client_ip
    return {"trace_id": ctx.get("trace_id")}
```
