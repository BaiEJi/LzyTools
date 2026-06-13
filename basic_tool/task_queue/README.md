# task_queue — ARQ 任务队列 SDK

基于 [ARQ](https://github.com/python-arq/arq) 的异步任务队列封装，提供统一配置、`@task` 装饰器注册、结构化日志和 Worker 生命周期管理。

## 核心价值

| ARQ 原生痛点 | SDK 解决方案 |
|---|---|
| 配置分散（WorkerSettings + RedisSettings） | Pydantic `TaskConfig` 统一管理 |
| 任务引用靠字符串，拼写错了运行时才报错 | `@task` 装饰器 + 注册表，编译期检查 |
| 无结构化日志 | 所有操作通过 loguru 输出结构化日志 |
| Worker 生命周期无封装 | `WorkerRunner` 封装信号处理 + 优雅关闭 |

## 快速开始

### 1. 定义任务

```python
from basic_tool.task_queue import task

@task(max_tries=3, job_timeout=60)
async def send_email(ctx, to: str, subject: str):
    """发送邮件。ctx 由 Worker 自动注入。"""
    # ctx["redis"] 可获取 ARQ Redis 连接
    # ctx["job_try"] 可获取当前重试次数
    print(f"Sending email to {to}")
    return f"Email sent to {to}"
```

### 2. 生产者端（FastAPI 应用）

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from basic_tool.task_queue import TaskConfig, TaskQueue

config = TaskConfig(redis_url="redis://localhost:6379/0")
queue = TaskQueue(config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await queue.init()
    yield
    await queue.close()

app = FastAPI(lifespan=lifespan)

@app.post("/send-email")
async def send_email_endpoint(to: str, subject: str):
    job_id = await queue.enqueue("send_email", to, subject)
    return {"job_id": job_id}
```

### 3. 消费者端（Worker 进程）

```python
from basic_tool.task_queue import TaskConfig, WorkerRunner

config = TaskConfig(max_jobs=5)
runner = WorkerRunner(config)
await runner.run()  # 阻塞直到 SIGINT/SIGTERM
```

## API 参考

### TaskConfig

```python
class TaskConfig(BaseModel):
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "arq:queue"
    max_jobs: int = 10
    job_timeout: int = 300
    max_tries: int = 5
    keep_result: int = 3600
    health_check_interval: int = 60
    poll_delay: float = 0.5
```

### @task

```python
@task(name=None, max_tries=None, job_timeout=None)
async def my_task(ctx, ...):
    ...
```

- `name`: 任务名称，默认使用函数名
- `max_tries`: 此任务的最大重试次数，None 使用全局默认值
- `job_timeout`: 此任务的超时秒数，None 使用全局默认值

### TaskQueue

```python
queue = TaskQueue(config)
await queue.init()                          # 初始化连接池
await queue.enqueue("task_name", *args)     # 入队任务
await queue.job_status(job_id)              # 查询状态
await queue.job_result(job_id, timeout=10)  # 获取结果
await queue.abort_job(job_id)               # 中止任务
await queue.close()                         # 关闭连接池
```

### WorkerRunner

```python
runner = WorkerRunner(config, on_startup=None, on_shutdown=None)
await runner.run(burst=False)  # burst=True 时队列空自动退出
```

### build_settings

```python
from basic_tool.task_queue import build_settings

settings = build_settings(config)
# settings 可直接传给 arq.Worker(settings)
```

## 错误处理与重试策略

Worker 包装层（`_wrap_function`）区分**业务异常**和**系统异常**：

- **业务异常 `AppError`**：视为预期失败（如参数非法、业务规则不满足），记录 WARNING 后返回错误标记字典 `{"_error": True, "code": ..., "message": ...}`，**不触发 ARQ 重试**。
- **其他异常**（`ConnectionError`、`TimeoutError` 等）：视为系统故障，照常抛出由 ARQ 按 `max_tries` 重试。

```python
from basic_tool.errors import AppError

@task(max_tries=3)
async def process_order(ctx, order_id: str):
    order = load_order(order_id)
    if order is None:
        raise AppError("ORDER_NOT_FOUND", f"订单不存在: {order_id}")  # 不重试
    await send_to_upstream(order)  # 网络异常会被 ARQ 重试
```

## 请求上下文跨进程传播

`enqueue()` 自动序列化当前请求上下文（`trace_id`、`user_id` 等），随任务传递到 Worker 进程。Worker 执行任务前通过 `_wrap_function` 恢复上下文，实现跨进程追踪。

```python
from basic_tool.context.ctx import request_context

# 生产者端：在请求上下文中入队
with request_context(trace_id="req-abc", user_id=42):
    await queue.enqueue("send_email", "user@example.com")
    # 任务携带 _context_snapshot={"trace_id": "req-abc", "user_id": 42}

# Worker 端：自动恢复，任务函数内可直接访问
@task()
async def send_email(ctx, to: str):
    from basic_tool.context.ctx import ctx as req_ctx
    print(req_ctx.get("trace_id"))  # "req-abc"
    print(req_ctx.get("user_id"))   # 42
```

无活跃上下文时（如脚本直接入队），传递空字典，Worker 跳过恢复，任务正常执行。


## 依赖

- `arq>=0.26.0`
- `redis[hiredis]>=5.0.0`
- `pydantic>=2.0.0`
- `loguru>=0.7.0`
