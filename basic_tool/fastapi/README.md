# FastAPI 模块

基于 FastAPI 的后端服务封装，提供一行代码创建具备完整中间件栈、鉴权、健康检查和 SDK 模块生命周期管理的 Web 服务。

## 核心价值

| 痛点 | SDK 解决方式 |
|------|-------------|
| 每个项目重复配置 CORS、日志、异常处理、健康检查 | `create_app()` 一行搞定 |
| JWT 鉴权 ~50 行样板代码 | 配置 + 一个 `user_loader` 回调即可 |
| 手动接线 lifespan 来 init/close Cache、HttpClient | 自动集成 |
| 日志需要单独调用 setup() | 嵌入 LogConfig，create_app 时自动配置 |

## 快速开始

```python
from basic_tool.fastapi import create_app, FastApiConfig, AuthConfig, CorsConfig, LogConfig
from basic_tool.redis import Cache, RedisConfig

# 1. 配置
config = FastApiConfig(
    title="用户服务",
    version="1.0.0",
    cors=CorsConfig(allow_origins=["https://app.example.com"]),
    auth=AuthConfig(secret_key="my-secret-key"),
    log=LogConfig(level="INFO", json_output=True),
)

# 2. SDK 模块
cache = Cache(RedisConfig())

# 3. 用户加载器（业务层实现）
async def load_user(user_id: str):
    return await db.get_user(user_id)

# 4. 登录处理（业务层实现）
async def login(username: str, password: str):
    user = await db.authenticate(username, password)
    if user:
        return {"sub": str(user.id), "scopes": user.scopes}
    return None

# 5. 创建应用
app = create_app(
    config,
    cache=cache,
    user_loader=load_user,
    login_handler=login,
    routers=[items_router, users_router],
)

# 6. 运行
# uvicorn main:app --host 0.0.0.0 --port 8000
```

## API 参考

### create_app

```python
def create_app(
    config: FastApiConfig,
    *,
    cache: Any | None = None,
    http_client: Any | None = None,
    task_queue: Any | None = None,
    user_loader: Callable[[str], Awaitable[Any]] | None = None,
    login_handler: Callable[[str, str], Awaitable[dict | None]] | None = None,
    routers: list[APIRouter] | None = None,
    extra_lifespan: Callable[..., AsyncIterator] | None = None,
) -> FastAPI
```

创建并配置 FastAPI 应用实例。

**参数：**
- `config`: 应用配置
- `cache`: Redis Cache 实例，自动在 lifespan 中 init/close
- `http_client`: HttpClient 实例，自动在 lifespan 中 init/close
- `task_queue`: TaskQueue 实例，自动在 lifespan 中 init/close
- `user_loader`: JWT 用户加载回调，传入则启用 JWT 鉴权
- `login_handler`: 登录处理函数，传入则注册 `/auth/token` 端点
- `routers`: 用户自定义路由列表
- `extra_lifespan`: 额外的 lifespan 上下文管理器

### FastApiConfig

```python
class FastApiConfig(BaseModel):
    title: str = "API"
    version: str = "0.1.0"
    debug: bool = False
    cors: CorsConfig = CorsConfig()
    auth: AuthConfig | None = None
    log: LogConfig | None = None           # 日志配置，传入则自动配置 loguru
    health_prefix: str = "/health"
    enable_request_logging: bool = True
    enable_error_handlers: bool = True
    enable_context_middleware: bool = True    # 是否启用请求上下文中间件（W3C Trace Context）
```

### AuthConfig

```python
class AuthConfig(BaseModel):
    secret_key: str                          # JWT 签名密钥
    algorithm: str = "HS256"
    token_expire_minutes: int = 30
    api_keys: dict[str, dict] = {}           # API Key 映射
    token_url: str = "/auth/token"
```

### CorsConfig

```python
class CorsConfig(BaseModel):
    allow_origins: list[str] = ["*"]
    allow_credentials: bool = False
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    expose_headers: list[str] = []
    max_age: int = 600
```

### JWTAuth

JWT 鉴权依赖提供器。

```python
jwt_auth = JWTAuth(config.auth, user_loader=load_user)

# 创建 token
token = jwt_auth.create_token({"sub": "user-1", "scopes": ["read"]})

# 路由中使用
@app.get("/protected")
async def protected(user = Depends(jwt_auth.get_current_user)):
    return {"user": user}

# 权限检查
@app.get("/admin", dependencies=[Depends(jwt_auth.require_scopes("admin"))])
async def admin(): ...
```

### ApiKeyAuth

API Key 鉴权依赖提供器。

```python
api_key_auth = ApiKeyAuth(config.auth)

# 路由中使用
@app.get("/data")
async def data(client_info: dict = Security(api_key_auth.verify)):
    return client_info
```

### AppError

业务异常，自动转换为 JSON 响应。

```python
from basic_tool.fastapi import AppError

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = await db.get(item_id)
    if not item:
        raise AppError(404, "Item not found")
    return item
```

## 自动端点

`create_app` 自动注册以下端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `{health_prefix}` | GET | 存活探针，始终返回 200 |
| `{health_prefix}/ready` | GET | 就绪探针，检查已注入的服务 |
| `/auth/token` | POST | OAuth2 登录端点（需提供 login_handler） |

## 中间件

自动配置的中间件：

1. **CORS** — 跨域资源共享
2. **ContextMiddleware** — 解析 W3C `traceparent` 请求头创建 child span（共享上游 trace_id），缺失时降级为根 trace；注入 trace_id / span_id / client_ip 到请求上下文，响应头回传 `traceparent`。受 `enable_context_middleware` 控制，默认启用
3. **RequestLoggingMiddleware** — 请求日志，记录 method、path、status、耗时，从请求上下文读取 trace_id。受 `enable_request_logging` 控制
4. **全局异常处理器** — AppError、RequestValidationError、Exception。受 `enable_error_handlers` 控制
