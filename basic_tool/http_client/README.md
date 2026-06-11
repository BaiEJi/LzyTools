# http_client — HTTP 客户端 SDK

基于 [httpx](https://github.com/encode/httpx) 的异步 HTTP 客户端封装，提供自动重试、熔断器、结构化日志、健康检查和生命周期管理。

## 核心价值

| httpx 原生痛点 | SDK 解决方案 |
|---|---|
| 无状态码重试（`retries=N` 只重试 TCP） | `RetryTransport` 自定义 transport |
| 无熔断器 | `CircuitBreakerTransport` 自定义 transport |
| 无结构化日志 | event_hooks 记录请求/响应日志 |
| 配置分散（20+ 构造参数） | Pydantic `HttpConfig` 统一管理 |

**设计思路：不包装 httpx 的 HTTP 方法。** 用户拿到的就是 `httpx.AsyncClient`，用原生 API 发请求。SDK 的价值在 transport 层。

## 快速开始

```python
from basic_tool.http_client import HttpClient, HttpConfig, RetryConfig, CircuitBreakerConfig

config = HttpConfig(
    base_url="https://api.example.com",
    retry=RetryConfig(max_retries=3, retryable_status_codes=frozenset({429, 502, 503, 504})),
    circuit_breaker=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30.0),
)

async with HttpClient(config) as http:
    # 用原生 httpx API 发请求
    resp = await http.client.get("/users/1")
    resp = await http.client.post("/users", json={"name": "test"})
    print(resp.status_code, resp.json())
```

## API 参考

### HttpConfig

```python
class HttpConfig(BaseModel):
    base_url: str = ""
    timeout: float = 30.0
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    max_connections: int = 100
    max_keepalive: int = 20
    headers: dict[str, str] = {}
    follow_redirects: bool = False
    http2: bool = False
    retry: RetryConfig | None = None
    circuit_breaker: CircuitBreakerConfig | None = None
    log_requests: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    max_body_log_size: int = 500
```

### RetryConfig

```python
class RetryConfig(BaseModel):
    max_retries: int = 3
    backoff_factor: float = 1.0
    retryable_status_codes: frozenset[int] = frozenset({429, 502, 503, 504})
```

重试延迟 = `backoff_factor * 2^attempt`（指数退避）。

### CircuitBreakerConfig

```python
class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
```

状态机：`closed`（正常）→ `open`（熔断，拒绝请求）→ `half_open`（试探恢复）→ `closed`

### HttpClient

```python
http = HttpClient(config)
await http.init()           # 初始化 httpx.AsyncClient
client = http.client        # 原生 httpx.AsyncClient，用法完全一致
await http.close()          # 关闭客户端

# 或用 async with
async with HttpClient(config) as http:
    resp = await http.client.get("/api")
```

### HttpHealth

```python
from basic_tool.http_client import HttpHealth

http = HttpClient(config)
await http.init()
health = HttpHealth(http, health_path="/health")
result = await health.check()
# {"status": "healthy", "status_code": 200, "latency_ms": 42.1, "circuit_breaker": "closed"}
```

### RetryTransport / CircuitBreakerTransport

可单独使用，不依赖 HttpClient：

```python
from basic_tool.http_client import RetryTransport, CircuitBreakerTransport, RetryConfig, CircuitBreakerConfig

transport = httpx.AsyncHTTPTransport()
transport = CircuitBreakerTransport(transport, CircuitBreakerConfig(failure_threshold=5))
transport = RetryTransport(transport, RetryConfig(max_retries=3))

async with httpx.AsyncClient(transport=transport) as client:
    resp = await client.get("https://api.example.com/data")
```

## Transport 组装顺序

```
用户请求 → RetryTransport → CircuitBreakerTransport → httpx.AsyncHTTPTransport → 网络
```

外层重试 → 内层熔断 → 实际网络。重试可以利用熔断器快速失败。

## 依赖

- `httpx>=0.27.0`
- `pydantic>=2.0.0`
- `loguru>=0.7.0`
