# basic_tool.concurrency — 异步并发工具集

基于 `asyncio` 的异步并发工具，提供批量并发执行、并发限流、超时保护、重试和错误聚合能力。

## 依赖

- `asyncio`（标准库） — 异步运行时
- `pydantic>=2.0.0` — 配置校验（`ConcurrencyConfig`）

## 模块结构

```
basic_tool/concurrency/
├── __init__.py       # 统一导出
├── config.py         # ConcurrencyConfig 配置类
├── exceptions.py     # CompositeError 聚合异常
├── strategy.py       # ErrorStrategy 枚举
├── pool.py           # ConcurrencyPool + PoolStats
├── batch.py          # gather_with_limit / run_in_batches / gather_with_retry
├── timeout.py        # with_timeout
└── task_group.py     # TaskGroup
```

## API 文档

---

### `config.py` — ConcurrencyConfig

```python
class ConcurrencyConfig(BaseModel):
    """并发操作配置。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `max_concurrency` | `int` | `10` | 最大并发任务数 |
| `default_timeout` | `float` | `30.0` | 默认超时时间（秒） |
| `max_retries` | `int` | `3` | 最大重试次数 |
| `backoff_base` | `float` | `1.0` | 指数退避基准延迟（秒） |
| `backoff_cap` | `float` | `60.0` | 最大退避延迟（秒） |

---

### `strategy.py` — ErrorStrategy

```python
class ErrorStrategy(str, Enum):
    """并发任务执行的错误处理策略。"""
```

| 取值 | 说明 |
|---|---|
| `FAIL_FAST` | 首个错误立即取消剩余任务 |
| `COLLECT_ALL` | 等待所有任务完成，随后抛出包含全部失败的 `CompositeError` |
| `SKIP_FAILED` | 跳过失败任务，仅返回成功结果 |

---

### `exceptions.py` — CompositeError

```python
class CompositeError(Exception):
    """将多个任务错误聚合为单个异常。"""
```

| 属性 | 类型 | 说明 |
|---|---|---|
| `errors` | `list[BaseException]` | 失败任务的异常列表 |
| `failed_indices` | `list[int]` | 失败任务在原始输入中的索引列表。未传入时默认为 `range(len(errors))` |

`__str__` 输出示例：

```
2 task(s) failed:
  [0] ValueError: invalid input
  [3] TimeoutError: Operation timed out after 5s
```

---

### `pool.py` — PoolStats / ConcurrencyPool

#### PoolStats

```python
@dataclass(frozen=True)
class PoolStats:
    """并发池状态快照。"""
```

| 属性 | 类型 | 说明 |
|---|---|---|
| `total` | `int` | 允许的最大并发数 |
| `used` | `int` | 当前运行中的任务数 |
| `waiting` | `int` | 等待获取信号量槽位的任务数 |
| `available` | `int` | 可用槽位数（`total - used`） |

#### ConcurrencyPool

```python
class ConcurrencyPool:
    """基于信号量的并发池，限制协程同时执行数量。"""
```

| 方法 / 属性 | 签名 | 说明 |
|---|---|---|
| `__init__()` | `(max_concurrency: int)` | 初始化。`max_concurrency` 必须 >= 1，否则抛出 `ValueError` |
| `stats` | `-> PoolStats` (property) | 返回当前池状态快照 |
| `run()` | `async (coro: Coroutine) -> T` | 在并发限制内执行单个协程，返回其结果 |
| `gather()` | `async (*coros: Coroutine) -> list[T]` | 并发执行多个协程，结果按输入顺序返回 |

---

### `batch.py` — gather_with_limit / run_in_batches / gather_with_retry

#### `gather_with_limit()`

```python
async def gather_with_limit(
    *coros: Coroutine,
    max_concurrency: int,
    strategy: ErrorStrategy = ErrorStrategy.FAIL_FAST,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[T]
```

并发执行协程，限制最大并发数。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `*coros` | `Coroutine` | — (必填) | 待执行的协程 |
| `max_concurrency` | `int` | — (必填) | 最大并发数，必须 >= 1 |
| `strategy` | `ErrorStrategy` | `FAIL_FAST` | 错误处理策略 |
| `on_progress` | `Callable[[int, int], None] \| None` | `None` | 进度回调 `(completed, total)`，每个任务完成后调用 |

**返回：** 结果列表，顺序与输入一致。`SKIP_FAILED` 策略下仅包含成功结果。

**抛出：**
- `ValueError` — `max_concurrency < 1`
- `CompositeError` — `COLLECT_ALL` 策略下有任务失败时
- 原始异常 — `FAIL_FAST` 策略下首个错误立即抛出

#### `run_in_batches()`

```python
async def run_in_batches(
    fn: Callable[[Any], Coroutine],
    items: list[Any],
    batch_size: int,
    inter_batch_delay: float = 0.0,
) -> list[T]
```

分批执行函数，每批内并发，批次间顺序执行。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `fn` | `Callable[[Any], Coroutine]` | — (必填) | 异步函数，对每个 item 调用 |
| `items` | `list[Any]` | — (必填) | 待处理的 item 列表 |
| `batch_size` | `int` | — (必填) | 每批数量，必须 >= 1 |
| `inter_batch_delay` | `float` | `0.0` | 批次间延迟（秒） |

**返回：** 结果列表，顺序与 `items` 一致。

**抛出：** `ValueError` — `batch_size < 1`。批次内任一任务抛出的异常会通过 `asyncio.gather` 正常传播。

#### `gather_with_retry()`

```python
async def gather_with_retry(
    *coro_factories: Callable[[], Coroutine],
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_cap: float = 60.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    strategy: ErrorStrategy = ErrorStrategy.COLLECT_ALL,
) -> list[T]
```

使用工厂函数执行带重试的并发任务。每个工厂函数在每次尝试时调用以创建全新协程，避免 "coroutine already awaited" 错误。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `*coro_factories` | `Callable[[], Coroutine]` | — (必填) | 返回新协程的可调用对象 |
| `max_retries` | `int` | `3` | 每个任务的最大重试次数 |
| `backoff_base` | `float` | `1.0` | 指数退避基准延迟（秒） |
| `backoff_cap` | `float` | `60.0` | 最大退避延迟（秒） |
| `retryable_exceptions` | `tuple[type[BaseException], ...]` | `(Exception,)` | 触发重试的异常类型 |
| `strategy` | `ErrorStrategy` | `COLLECT_ALL` | 最终失败的错误处理策略 |

退避公式：`delay = min(backoff_base * 2^attempt, backoff_cap) * random(0.5, 1.0)`，含随机抖动。

**返回：** 结果列表。

**抛出：** `CompositeError` — 有任务在重试耗尽后仍然失败（`COLLECT_ALL` / `FAIL_FAST` 策略）。

---

### `timeout.py` — with_timeout

```python
async def with_timeout(
    coro: object,
    timeout: float,
    *,
    message: str = "",
) -> T
```

为协程添加超时保护。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `coro` | `object` | — (必填) | 待执行的协程 |
| `timeout` | `float` | — (必填) | 最大等待时间（秒），必须 > 0 |
| `message` | `str` | `""` | 自定义超时错误信息。为空时使用默认信息 |

**返回：** 协程的返回值。

**抛出：**
- `ValueError` — `timeout <= 0`
- `TimeoutError` — 协程超时。信息为 `message` 或 `"Operation timed out after {timeout}s"`

---

### `task_group.py` — TaskGroup

```python
class TaskGroup:
    """包装 asyncio.TaskGroup，将 BaseExceptionGroup 转为 CompositeError。"""
```

提供受管理的并发任务上下文。退出时若有任务失败，抛出 `CompositeError` 而非 `BaseExceptionGroup`。

| 方法 | 签名 | 说明 |
|---|---|---|
| `__init__()` | `() -> None` | 初始化。需配合 `async with` 使用 |
| `__aenter__()` | `async () -> TaskGroup` | 进入任务组上下文 |
| `__aexit__()` | `async (...) -> bool` | 退出上下文。有任务失败时抛出 `CompositeError` |
| `create()` | `(coro: Coroutine) -> asyncio.Task[T]` | 在组内创建任务，返回 `asyncio.Task` |

---

## 使用示例

### 基本并发执行

```python
import asyncio
from basic_tool.concurrency import gather_with_limit

async def fetch(url: str) -> str:
    await asyncio.sleep(0.1)
    return f"result from {url}"

async def main():
    urls = ["https://a.com", "https://b.com", "https://c.com"]
    results = await gather_with_limit(
        *[fetch(u) for u in urls],
        max_concurrency=2,
    )
    print(results)
    # ['result from https://a.com', 'result from https://b.com', 'result from https://c.com']

asyncio.run(main())
```

### 超时保护

```python
import asyncio
from basic_tool.concurrency import with_timeout

async def slow_api() -> str:
    await asyncio.sleep(10)
    return "done"

async def main():
    try:
        result = await with_timeout(slow_api(), timeout=2.0, message="API too slow")
    except TimeoutError as e:
        print(f"timed out: {e}")  # timed out: API too slow

asyncio.run(main())
```

### 并发池

```python
import asyncio
from basic_tool.concurrency import ConcurrencyPool

async def process(item: int) -> int:
    await asyncio.sleep(0.05)
    return item * 2

async def main():
    pool = ConcurrencyPool(max_concurrency=3)

    results = await pool.gather(
        *[process(i) for i in range(10)]
    )
    print(results)  # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    # 查看池状态
    print(pool.stats)
    # PoolStats(total=3, used=0, waiting=0, available=3)

asyncio.run(main())
```

### 带重试的并发（工厂函数模式）

```python
import asyncio
from basic_tool.concurrency import gather_with_retry

async def fetch_with_retry(url: str) -> str:
    # 模拟可能失败的网络请求
    await asyncio.sleep(0.1)
    return f"data from {url}"

async def main():
    urls = ["https://a.com", "https://b.com", "https://c.com"]

    # 每个工厂函数被调用时返回一个全新协程
    results = await gather_with_retry(
        *[lambda u=u: fetch_with_retry(u) for u in urls],
        max_retries=3,
        backoff_base=1.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
    )
    print(results)

asyncio.run(main())
```

### TaskGroup 错误聚合

```python
import asyncio
from basic_tool.concurrency import TaskGroup, CompositeError

async def task_ok() -> int:
    await asyncio.sleep(0.01)
    return 42

async def task_fail() -> None:
    await asyncio.sleep(0.02)
    raise ValueError("something went wrong")

async def main():
    async with TaskGroup() as tg:
        tg.create(task_ok())
        tg.create(task_fail())
        tg.create(task_ok())

# 如果有任务失败，退出上下文时抛出 CompositeError
async def safe_main():
    try:
        async with TaskGroup() as tg:
            tg.create(task_ok())
            tg.create(task_fail())
    except CompositeError as e:
        for err in e.errors:
            print(f"{type(err).__name__}: {err}")
        # ValueError: something went wrong

asyncio.run(safe_main())
```

### COLLECT_ALL 错误收集与 SKIP_FAILED 跳过失败

```python
import asyncio
from basic_tool.concurrency import gather_with_limit, ErrorStrategy, CompositeError

async def maybe_fail(x: int) -> int:
    await asyncio.sleep(0.01)
    if x % 3 == 0:
        raise ValueError(f"{x} is divisible by 3")
    return x

async def main():
    inputs = list(range(1, 10))

    # COLLECT_ALL：收集所有错误后一次性抛出
    try:
        await gather_with_limit(
            *[maybe_fail(x) for x in inputs],
            max_concurrency=5,
            strategy=ErrorStrategy.COLLECT_ALL,
        )
    except CompositeError as e:
        print(e.failed_indices)  # [2, 5, 8]（即 3, 6, 9）

    # SKIP_FAILED：跳过失败，仅返回成功结果
    results = await gather_with_limit(
        *[maybe_fail(x) for x in inputs],
        max_concurrency=5,
        strategy=ErrorStrategy.SKIP_FAILED,
    )
    print(results)  # [1, 2, 4, 5, 7, 8]

asyncio.run(main())
```

### 进度回调与分批执行

```python
import asyncio
from basic_tool.concurrency import gather_with_limit, run_in_batches

async def download(url: str) -> bytes:
    await asyncio.sleep(0.05)
    return b"..."

async def main():
    urls = [f"https://example.com/{i}" for i in range(20)]

    # 进度回调
    def on_progress(completed: int, total: int) -> None:
        pct = completed * 100 // total
        print(f"progress: {completed}/{total} ({pct}%)")

    await gather_with_limit(
        *[download(u) for u in urls],
        max_concurrency=5,
        on_progress=on_progress,
    )

    # 分批执行：每批 8 个，批次间停顿 0.5 秒
    results = await run_in_batches(
        download,
        urls,
        batch_size=8,
        inter_batch_delay=0.5,
    )

asyncio.run(main())
```

### 基于 ConcurrencyConfig 配置

```python
from basic_tool.concurrency import ConcurrencyConfig

config = ConcurrencyConfig(
    max_concurrency=20,
    default_timeout=15.0,
    max_retries=5,
    backoff_base=2.0,
    backoff_cap=120.0,
)

# 用配置值驱动并发操作
max_conc = config.max_concurrency
timeout = config.default_timeout
```

---

## 请求上下文自动传播

所有并发工具（`ConcurrencyPool` / `gather_with_limit` / `gather_with_retry` / `TaskGroup`）均基于 `asyncio.Task` 调度协程。Python 3.11+ 的 `asyncio.Task` 在创建时会自动 **复制当前 ContextVar 快照**，因此 `basic_tool.context.ctx` 中保存的 `trace_id`、`user_id` 等键值会自动传播到子任务中，无需手动传递。

**关键特性：**

- **自动继承** — 在调用并发工具前通过 `request_context(...)` 或 `ctx.set(...)` 写入的值，子任务内可直接读取。
- **快照隔离** — 上下文是 **快照拷贝**（snapshot），而非跨任务共享的可变状态。子任务内的修改不会影响其他任务或父任务。

**示例：trace_id 自动传播到并发任务**

```python
import asyncio
from basic_tool.concurrency import gather_with_limit
from basic_tool.context import ctx, request_context

async def fetch(url: str) -> str:
    # 子任务内可直接读取父任务设置的 trace_id
    trace_id = ctx.get("trace_id")
    return f"[{trace_id}] {url}"

async def main():
    # 在并发调用前设置请求上下文
    async with request_context(user_id=42):  # trace_id 自动生成
        results = await gather_with_limit(
            fetch("https://a.com"),
            fetch("https://b.com"),
            max_concurrency=2,
        )
        # results: ["[<trace_id>] https://a.com", "[<trace_id>] https://b.com"]
        # 两个子任务看到的 trace_id 相同（来自同一快照）

asyncio.run(main())
```

**快照隔离示例：子任务修改不影响父任务**

```python
import asyncio
from basic_tool.concurrency import ConcurrencyPool
from basic_tool.context import ctx, request_context

async def worker():
    ctx.set("custom_key", "child_value")  # 仅影响当前子任务的快照
    return ctx.get("custom_key")

async def main():
    async with request_context():
        pool = ConcurrencyPool(max_concurrency=1)
        await pool.run(worker())
        # 父任务中 custom_key 仍为 None —— 子任务的修改不会传播回来
        assert ctx.get("custom_key") is None

asyncio.run(main())
```
