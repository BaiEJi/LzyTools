# basic_tool.errors — 标准化错误码与异常处理

提供统一的业务异常 `AppError`、错误码注册表、15 个预定义错误码 `CommonErrors`、FastAPI 全局异常处理器和 loguru 日志集成。

## 依赖

- `pydantic>=2.0.0` — `ErrorConfig` 配置校验
- `loguru>=0.7.0` — 错误日志记录
- `fastapi>=0.100.0` — `setup_error_handlers` 注册全局异常处理器

## 解决什么问题

| 痛点 | SDK 解决方式 |
|---|---|
| 异常处理散落各处、响应格式不一致 | `AppError` 统一异常 + `setup_error_handlers` 统一拦截，响应固定为 `{"code": "...", "message": "..."}` |
| 错误码硬编码、重复定义 | `ErrorEntry` 自动注册到全局注册表，重复注册立即报错 |
| 每个项目重新定义一套错误码 | `CommonErrors` 内置 15 个覆盖参数、认证、授权、资源、限流、系统等场景的标准错误码 |
| 未捕获异常暴露内部细节 | `Exception` 兜底处理器返回 500 + 通用错误信息，5xx 记录完整堆栈 |

## 模块结构

```
basic_tool/errors/
├── __init__.py      # 统一导出
├── app_error.py     # AppError 业务异常
├── config.py        # ErrorConfig 配置类
├── registry.py      # ErrorEntry / ErrorRegistry / check_conflicts / get_all_entries / clear_registry
├── codes.py         # CommonErrors 预定义错误码
├── handler.py       # setup_error_handlers FastAPI 异常处理器
└── log.py           # 内部日志集成（不对外暴露）
```

## API 文档

---

### `app_error.py` — AppError

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400, context: dict | None = None)
```

业务异常基类。被 FastAPI 异常处理器捕获后自动转换为标准化 JSON 响应。

| 属性 / 方法 | 说明 |
|---|---|
| `.code` | 错误码字符串（如 `"PARAM_MISSING"`） |
| `.message` | 人类可读的错误消息 |
| `.http_status` | HTTP 状态码，默认 400 |
| `.context` | 额外上下文字典（可选） |
| `.detail` | 向后兼容别名，返回 `.message` |
| `.status_code` | 向后兼容别名，返回 `.http_status` |
| `.to_dict(include_context=False)` | 转为 `{"code": ..., "message": ...}` 字典，`include_context=True` 时附加 `context` 字段 |

```python
from basic_tool.errors import AppError

# 基本构造
raise AppError(code="CUSTOM", message="something went wrong", http_status=400)

# 带上下文（响应默认不返回 context，需 ErrorConfig.include_context=True）
raise AppError(code="CUSTOM", message="fail", context={"user_id": 123})

# 转字典
err = AppError(code="X", message="y", context={"k": 1})
err.to_dict()                      # {"code": "X", "message": "y"}
err.to_dict(include_context=True)  # {"code": "X", "message": "y", "context": {"k": 1}}
```

---

### `config.py` — ErrorConfig

```python
class ErrorConfig(BaseModel):
    include_context: bool = False
    log_5xx_stack: bool = True
    log_4xx_summary: bool = True
```

控制错误响应内容和日志详细程度。

| 字段 | 默认值 | 说明 |
|---|---|---|
| `include_context` | `False` | 响应体是否包含 `context` 字段 |
| `log_5xx_stack` | `True` | 5xx 错误是否记录完整堆栈 |
| `log_4xx_summary` | `True` | 4xx 错误是否记录摘要（而非完整堆栈） |

```python
from basic_tool.errors import ErrorConfig

# 默认配置（不暴露 context，5xx 记堆栈，4xx 记摘要）
config = ErrorConfig()

# 调试场景：响应体携带 context
config = ErrorConfig(include_context=True)
```

---

### `registry.py` — ErrorEntry / ErrorRegistry

#### ErrorEntry

```python
@dataclass(frozen=True)
class ErrorEntry:
    code: str
    message_template: str
    http_status: int = 400
```

错误码定义条目。创建实例时自动注册到全局注册表，重复注册会抛出 `ValueError`。

`message_template` 支持 `str.format` 风格的占位符，调用时用 `**kwargs` 填充。

| 操作 | 说明 |
|---|---|
| `entry(**kwargs) -> AppError` | 渲染模板生成 `AppError`，`kwargs` 同时存入 `.context` |

```python
from basic_tool.errors import ErrorEntry

# 定义并自动注册
MY_ERROR = ErrorEntry("MY_ERROR", "操作失败: {action}", 400)

# 调用生成 AppError（kwargs 填充模板并存入 context）
raise MY_ERROR(action="delete")
# AppError(code="MY_ERROR", message="操作失败: delete", http_status=400, context={"action": "delete"})

# 重复注册会报错
ErrorEntry("MY_ERROR", "another", 400)  # ValueError: Duplicate error code: MY_ERROR
```

#### ErrorRegistry

错误码集合基类。子类以类属性形式定义 `ErrorEntry`，通过类方法查询。

| 方法 | 说明 |
|---|---|
| `.entries() -> dict[str, ErrorEntry]` (classmethod) | 返回类中所有 `ErrorEntry`，key 为属性名 |
| `.codes() -> list[str]` (classmethod) | 返回类中所有错误码属性名 |

```python
from basic_tool.errors import ErrorRegistry, ErrorEntry

class PaymentErrors(ErrorRegistry):
    PAYMENT_FAILED = ErrorEntry("PAYMENT_FAILED", "支付失败: {reason}", 400)
    REFUND_FAILED = ErrorEntry("REFUND_FAILED", "退款失败: {order_id}", 400)

PaymentErrors.entries()
# {"PAYMENT_FAILED": ErrorEntry(...), "REFUND_FAILED": ErrorEntry(...)}

PaymentErrors.codes()
# ["PAYMENT_FAILED", "REFUND_FAILED"]

# 使用
raise PaymentErrors.PAYMENT_FAILED(reason="余额不足")
```

#### 工具函数

| 函数 | 说明 |
|---|---|
| `check_conflicts() -> None` | 扫描全局注册表检测重复错误码，发现重复抛 `ValueError` |
| `get_all_entries() -> dict[str, ErrorEntry]` | 返回全局注册表的浅拷贝 |
| `clear_registry() -> None` | 清空全局注册表（仅用于测试隔离） |

```python
from basic_tool.errors import check_conflicts, get_all_entries, clear_registry

# 启动时校验无冲突（ErrorEntry 注册时已检测，此函数提供显式入口）
check_conflicts()

# 查看所有已注册错误码
all_codes = get_all_entries()

# 测试中隔离（谨慎使用，会清空 CommonErrors 等所有注册）
clear_registry()
```

---

### `codes.py` — CommonErrors

预定义通用错误码集合，涵盖 15 个常见 Web 服务场景。模块导入时自动注册到全局注册表。

```python
# 直接抛出（kwargs 填充模板）
from basic_tool.errors import CommonErrors

raise CommonErrors.PARAM_MISSING(param="user_id")
raise CommonErrors.RESOURCE_NOT_FOUND(resource="用户")

# 查询所有预定义码
CommonErrors.codes()
```

| 属性名 | 错误码 | 消息模板 | HTTP 状态码 |
|---|---|---|---|
| `PARAM_MISSING` | `PARAM_MISSING` | 缺少必填参数: {param} | 400 |
| `PARAM_INVALID` | `PARAM_INVALID` | 参数无效: {param} | 400 |
| `PARAM_TYPE_ERROR` | `PARAM_TYPE_ERROR` | 参数类型错误: {param} 应为 {expected_type} | 400 |
| `TOKEN_EXPIRED` | `TOKEN_EXPIRED` | 令牌已过期 | 401 |
| `TOKEN_INVALID` | `TOKEN_INVALID` | 令牌无效 | 401 |
| `CREDENTIALS_ERROR` | `CREDENTIALS_ERROR` | 用户名或密码错误 | 401 |
| `PERMISSION_DENIED` | `PERMISSION_DENIED` | 权限不足: 需要 {required_permission} | 403 |
| `ACCESS_FORBIDDEN` | `ACCESS_FORBIDDEN` | 禁止访问: {resource} | 403 |
| `RESOURCE_NOT_FOUND` | `RESOURCE_NOT_FOUND` | {resource}不存在 | 404 |
| `RESOURCE_ALREADY_EXISTS` | `RESOURCE_ALREADY_EXISTS` | {resource}已存在 | 409 |
| `VERSION_CONFLICT` | `VERSION_CONFLICT` | 版本冲突: {resource} 已被修改 | 409 |
| `RATE_LIMITED` | `RATE_LIMITED` | 请求过于频繁，请稍后重试 | 429 |
| `INTERNAL_ERROR` | `INTERNAL_ERROR` | 内部服务器错误 | 500 |
| `SERVICE_UNAVAILABLE` | `SERVICE_UNAVAILABLE` | 服务暂不可用 | 503 |
| `UPSTREAM_TIMEOUT` | `UPSTREAM_TIMEOUT` | 上游服务超时 | 504 |

---

### `handler.py` — setup_error_handlers

```python
def setup_error_handlers(app: FastAPI, config: ErrorConfig | None = None) -> None
```

注册 FastAPI 全局异常处理器。统一响应格式为 `{"code": "...", "message": "..."}`。

注册三种异常处理器：

| 异常类型 | 响应状态码 | 响应体 |
|---|---|---|
| `AppError` | `exc.http_status` | `{"code": ..., "message": ...}`（配置开启时含 `context`） |
| `RequestValidationError` | 422 | `{"code": "PARAM_INVALID", "message": "Validation error", "errors": [...]}` |
| `Exception`（兜底） | 500 | `{"code": "INTERNAL_ERROR", "message": "内部服务器错误"}` |

所有异常都会通过 loguru 记录结构化日志，包含请求方法、路径和 trace_id（从请求上下文 `ctx.get("trace_id")` 读取，由 ContextMiddleware 注入）。

```python
from fastapi import FastAPI
from basic_tool.errors import setup_error_handlers, ErrorConfig

app = FastAPI()
setup_error_handlers(app)

# 或自定义配置
setup_error_handlers(app, ErrorConfig(include_context=True))
```

---

## 使用示例

### 1. 基本 AppError

```python
from basic_tool.errors import AppError

def transfer(amount: int):
    if amount <= 0:
        raise AppError(code="INVALID_AMOUNT", message="转账金额必须大于 0", http_status=400)
    if amount > 1_000_000:
        raise AppError(
            code="AMOUNT_TOO_LARGE",
            message="单笔转账超过限额",
            http_status=400,
            context={"limit": 1_000_000, "actual": amount},
        )
```

### 2. 使用 CommonErrors 预定义码

```python
from basic_tool.errors import CommonErrors

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await db.find_user(user_id)
    if user is None:
        raise CommonErrors.RESOURCE_NOT_FOUND(resource="用户")
    return user

async def login(username: str, password: str):
    user = await db.verify(username, password)
    if user is None:
        raise CommonErrors.CREDENTIALS_ERROR()
    if not user.is_active:
        raise CommonErrors.PERMISSION_DENIED(required_permission="active account")
```

### 3. 自定义 ErrorRegistry 子类

```python
from basic_tool.errors import ErrorRegistry, ErrorEntry

class OrderErrors(ErrorRegistry):
    ORDER_NOT_FOUND = ErrorEntry("ORDER_NOT_FOUND", "订单不存在: {order_id}", 404)
    ORDER_PAID = ErrorEntry("ORDER_PAID", "订单已支付: {order_id}", 409)
    ORDER_CANCELLED = ErrorEntry("ORDER_CANCELLED", "订单已取消: {order_id}", 409)

# 业务代码
async def cancel_order(order_id: str):
    order = await db.get_order(order_id)
    if order is None:
        raise OrderErrors.ORDER_NOT_FOUND(order_id=order_id)
    if order.status == "paid":
        raise OrderErrors.ORDER_PAID(order_id=order_id)
```

### 4. FastAPI 集成

```python
from fastapi import FastAPI
from basic_tool.errors import setup_error_handlers, ErrorConfig, CommonErrors

app = FastAPI()
setup_error_handlers(app, ErrorConfig(include_context=False))

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id < 0:
        raise CommonErrors.PARAM_INVALID(param="item_id")
    return {"item_id": item_id}

# 所有 AppError、请求验证错误、未捕获异常都会被处理器拦截
# 返回统一的 {"code": "...", "message": "..."} 格式
```

### 5. 响应格式

```json
// AppError（默认）
{"code": "RESOURCE_NOT_FOUND", "message": "用户不存在"}

// AppError（include_context=True）
{"code": "AMOUNT_TOO_LARGE", "message": "单笔转账超过限额", "context": {"limit": 1000000, "actual": 2000000}}

// RequestValidationError（422）
{"code": "PARAM_INVALID", "message": "Validation error", "errors": [...]}

// 未捕获异常（500，不暴露内部细节）
{"code": "INTERNAL_ERROR", "message": "内部服务器错误"}
```

---

## 迁移指南（从旧 middleware.py AppError）

旧版 `basic_tool.fastapi.middleware.AppError` 使用位置参数和 HTTP 状态码作为第一个参数，新版改为关键字参数 + 错误码字符串。

```python
# 旧（已废弃）
from basic_tool.fastapi import AppError
raise AppError(404, "Not found")  # 位置参数，第一个是 HTTP 状态码

# 新
from basic_tool.errors import AppError
raise AppError(code="NOT_FOUND", message="Not found", http_status=404)  # 关键字参数

# 或使用预定义码（推荐）
from basic_tool.errors import CommonErrors
raise CommonErrors.RESOURCE_NOT_FOUND(resource="用户")

# 旧代码依赖 .detail / .status_code 属性仍可工作（提供别名）
err = AppError(code="X", message="y", http_status=404)
err.detail       # "y"（.message 别名）
err.status_code  # 404（.http_status 别名）
```
