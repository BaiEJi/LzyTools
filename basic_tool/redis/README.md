# basic_tool.redis — Redis 异步缓存

基于 `redis[hiredis]` 的异步 Redis 客户端封装，提供连接池管理、常用数据操作、分布式锁、缓存装饰器等能力。

## 依赖

- `redis[hiredis]>=5.0.0` — 异步 Redis 客户端
- `orjson>=3.9.0` — 高性能 JSON 序列化
- `pydantic>=2.0.0` — 配置校验

## 模块结构

```
basic_tool/redis/
├── __init__.py        # 统一导出
├── config.py          # RedisConfig 配置类
├── client.py          # Cache 客户端
├── health.py          # CacheHealth 健康检查
├── locks.py           # DistributedLock 分布式锁
└── decorators.py      # cached / rate_limit / synchronized 装饰器
```

## API 文档

---

### `config.py` — RedisConfig

```python
class RedisConfig(BaseModel):
    url: str                            # redis://:password@host:port/db
    max_connections: int = 50           # 连接池上限
    socket_connect_timeout: int = 5     # TCP 建连超时秒数
    socket_timeout: int = 5             # 读写超时秒数
    socket_keepalive: bool = True       # TCP keepalive
    retry_on_timeout: bool = True       # 超时自动重试
    health_check_interval: int = 30     # 空闲连接探活间隔秒数
    decode_responses: bool = True       # bytes → str
```

---

### `client.py` — Cache

```python
class Cache:
    def __init__(self, config: RedisConfig)
```

#### 生命周期

| 方法 | 说明 |
|---|---|
| `async init() -> None` | 创建连接池 + 客户端实例。lifespan startup 调用 |
| `async close() -> None` | 优雅关闭连接池。lifespan shutdown 调用 |
| `client -> Redis` | 底层 `redis.asyncio.Redis` 实例，用于调用任意未封装的命令 |

#### String 操作

| 方法 | 说明 |
|---|---|
| `async get(key: str) -> str \| None` | 获取值 |
| `async set(key, value, *, ex=None, px=None, nx=False, xx=False) -> bool \| None` | 设置值 |
| `async delete(*keys: str) -> int` | 删除 key，返回删除数量 |
| `async exists(*keys: str) -> int` | 检查 key 是否存在 |
| `async expire(key: str, seconds: int) -> bool` | 设置过期时间 |
| `async ttl(key: str) -> int` | 获取剩余过期时间（-1=永不过期，-2=不存在） |
| `async pttl(key: str) -> int` | 获取剩余过期时间（毫秒） |
| `async persist(key: str) -> bool` | 移除过期时间 |
| `async pexpire(key: str, ms: int) -> bool` | 设置过期时间（毫秒） |
| `async incr(key: str, amount: int = 1) -> int` | 递增 |
| `async decr(key: str, amount: int = 1) -> int` | 递减 |
| `async mget(*keys: str) -> list[str \| None]` | 批量获取 |
| `async mset(mapping: dict[str, str]) -> bool` | 批量设置 |
| `async append(key: str, value: str) -> int` | 追加值，返回总长度 |
| `async strlen(key: str) -> int` | 获取字符串长度 |
| `async getdel(key: str) -> str \| None` | 获取并删除 |
| `async getex(key, *, ex=None, px=None) -> str \| None` | 获取并设置过期时间 |
| `async type(key: str) -> str` | 获取 key 的数据类型 |

#### Hash 操作

| 方法 | 说明 |
|---|---|
| `async hget(name: str, key: str) -> str \| None` | 获取 hash 字段值 |
| `async hset(name, key=None, value=None, *, mapping=None) -> int` | 设置 hash 字段（支持单字段和 mapping 批量） |
| `async hgetall(name: str) -> dict[str, str]` | 获取 hash 所有字段 |
| `async hdel(name: str, *keys: str) -> int` | 删除 hash 字段 |
| `async hmget(name: str, *keys: str) -> list[str \| None]` | 批量获取 hash 字段 |
| `async hkeys(name: str) -> list[str]` | 获取所有字段名 |
| `async hvals(name: str) -> list[str]` | 获取所有值 |
| `async hlen(name: str) -> int` | 获取字段数量 |
| `async hexists(name: str, key: str) -> bool` | 检查字段是否存在 |
| `async hincrby(name: str, key: str, amount: int = 1) -> int` | 递增字段值 |

#### Set 操作

| 方法 | 说明 |
|---|---|
| `async sadd(name: str, *values: str) -> int` | 添加成员 |
| `async srem(name: str, *values: str) -> int` | 移除成员 |
| `async smembers(name: str) -> set[str]` | 获取所有成员 |
| `async sismember(name: str, value: str) -> bool` | 检查成员是否存在 |
| `async smismember(name: str, *values: str) -> list[bool]` | 批量检查成员是否存在 |
| `async scard(name: str) -> int` | 获取成员数量 |
| `async sinter(*names: str) -> set[str]` | 获取交集 |
| `async sunion(*names: str) -> set[str]` | 获取并集 |
| `async sdiff(*names: str) -> set[str]` | 获取差集 |
| `async srandmember(name: str, count=None) -> str \| list[str] \| None` | 随机获取成员 |

#### List 操作

| 方法 | 说明 |
|---|---|
| `async lpush(name, *values) -> int` | 从左侧插入 |
| `async rpush(name, *values) -> int` | 从右侧插入 |
| `async lpop(name, count=None) -> str \| list \| None` | 从左侧弹出 |
| `async rpop(name, count=None) -> str \| list \| None` | 从右侧弹出 |
| `async lrange(name, start, end) -> list[str]` | 获取范围元素 |
| `async llen(name) -> int` | 获取列表长度 |
| `async lindex(name, index) -> str \| None` | 获取指定索引元素 |
| `async lset(name, index, value) -> bool` | 设置指定索引元素 |
| `async lrem(name, count, value) -> int` | 移除匹配元素 |
| `async lmove(src, dst, src_side="LEFT", dst_side="RIGHT") -> str \| None` | 原子移动元素 |
| `async blpop(*keys, timeout=0) -> tuple \| None` | 阻塞式左弹出 |
| `async brpop(*keys, timeout=0) -> tuple \| None` | 阻塞式右弹出 |
| `async blmove(src, dst, src_side, dst_side, timeout=0) -> str \| None` | 阻塞式原子移动 |

#### Scan 操作

| 方法 | 说明 |
|---|---|
| `async scan(cursor=0, *, match=None, count=100) -> tuple[int, list[str]]` | 增量迭代 key |
| `async scan_iter(match=None, count=100) -> AsyncIterator[str]` | 异步迭代器，自动处理 cursor |

#### JSON 快捷方式

| 方法 | 说明 |
|---|---|
| `async get_json(key: str) -> Any` | get + orjson 反序列化 |
| `async set_json(key: str, value: Any, *, ex=None) -> bool \| None` | orjson 序列化 + set |

#### Pipeline

| 方法 | 说明 |
|---|---|
| `pipeline(transaction=True) -> Pipeline` | 获取 Pipeline 对象，transaction=True 时用 MULTI/EXEC 包裹 |

#### Sorted Set 操作

| 方法 | 说明 |
|---|---|
| `async zadd(name, mapping, *, nx=False, xx=False, ch=False) -> int` | 添加成员及分数 |
| `async zrem(name, *values) -> int` | 移除成员 |
| `async zrange(name, start, end, *, withscores=False, desc=False) -> list` | 按索引范围获取 |
| `async zrangebyscore(name, min, max, *, withscores=False, offset=0, count=None) -> list` | 按分数范围获取 |
| `async zcard(name) -> int` | 获取成员数量 |
| `async zscore(name, value) -> float \| None` | 获取指定成员的分数 |
| `async zrank(name, value) -> int \| None` | 获取指定成员的排名（升序） |
| `async zrevrange(name, start, end, *, withscores=False) -> list` | 按索引范围获取（降序） |
| `async zrevrank(name, value) -> int \| None` | 获取指定成员的排名（降序） |
| `async zincrby(name, amount, value) -> float` | 递增成员分数 |
| `async zcount(name, min, max) -> int` | 统计分数范围内的成员数 |
| `async zlexcount(name, min, max) -> int` | 统计字典序范围内的成员数 |
| `async zremrangebyscore(name, min, max) -> int` | 按分数范围移除 |

#### Lua 脚本

| 方法 | 说明 |
|---|---|
| `async eval(script, numkeys, *keys_and_args) -> Any` | 执行 Lua 脚本（每次发送全文） |
| `async evalsha(sha, numkeys, *keys_and_args) -> Any` | 通过 SHA1 执行已缓存脚本（更高效） |
| `register_script(script) -> Script` | 注册可复用脚本（自动处理 EVALSHA + EVAL 回退） |

#### 原始命令

| 方法 | 说明 |
|---|---|
| `async execute_command(*args, **kwargs) -> Any` | 直接执行 Redis 原始命令 |

#### Pub/Sub

| 方法 | 说明 |
|---|---|
| `async publish(channel, message) -> int` | 发布消息，返回接收者数量 |
| `pubsub(**kwargs) -> PubSub` | 获取原生 PubSub 对象（手动管理生命周期） |
| `async subscribe(*channels) -> PubSub` | 订阅频道，返回已订阅的 PubSub |
| `async psubscribe(*patterns) -> PubSub` | 按模式订阅，支持 `*` `?` `[...]` 通配符 |

---

### `health.py` — CacheHealth

```python
class CacheHealth:
    def __init__(self, cache: Cache)
```

| 方法 | 说明 |
|---|---|
| `pool_stats() -> dict` | 连接池状态 `{created, in_use, idle, max, status}` |
| `async check() -> dict` | 综合健康检查 `{ok, pool, ping_ms, error}` |

---

### `locks.py` — DistributedLock / Lock

```python
class DistributedLock:
    def __init__(self, cache: Cache)

class Lock:
    def __init__(self, cache: Cache, key: str)
```

**DistributedLock** 是锁工厂，通过 `lock(key)` 或 `get_lock(key)` 返回独立的 **Lock** 对象。
每个 Lock 持有独立的 token 和 key，可在并发场景下安全使用。

| 方法 | 说明 |
|---|---|
| `DistributedLock.get_lock(key) -> Lock` | 获取独立锁对象（不自动获取） |
| `DistributedLock.lock(key, *, timeout=30, ...) -> _LockContext` | 返回 async with 上下文管理器 |
| `Lock.acquire(*, timeout=30, retry_interval=0.1, retry_count=50) -> bool` | 获取锁 |
| `Lock.release() -> bool` | 释放锁（Lua 脚本保证原子性） |
| `Lock.extend(timeout: int) -> bool` | 续期锁（重置 TTL） |

---

### `decorators.py`

#### `@cached`

```python
@cached(*, prefix: str, ttl: int = 300, ttl_jitter: int = 0, key_builder=None)
```

缓存异步函数返回值。被装饰函数的参数中需包含 `Cache` 实例。
None 返回值也会被缓存（通过 exists 检查区分缓存未命中）。

- `prefix`: key 前缀
- `ttl`: 过期秒数
- `ttl_jitter`: TTL 随机抖动（防缓存雪崩）
- `key_builder`: 自定义 key 生成函数 `(func_name, filtered_args, filtered_kwargs) -> str`
  （args/kwargs 已过滤 Cache 实例）

#### `@rate_limit`

```python
@rate_limit(*, key: str, max_requests: int = 10, window: int = 60, cache: Cache)
```

滑动窗口限流。使用 Sorted Set 实现。

- `key`: 限流维度标识，支持 `{param}` 格式化占位符（如 `"user:{user_id}"`）
- `max_requests`: 窗口内最大请求数
- `window`: 时间窗口秒数
- 抛出 `RateLimitError`（而非 `RuntimeError`），包含 `key`/`count`/`max_requests`/`window` 属性

#### `@synchronized`

```python
@synchronized(*, lock_key: str, timeout=30, retry_interval=0.1, retry_count=50, cache: Cache)
```

分布式锁装饰器。`lock_key` 支持格式化占位符，如 `"import:{user_id}"`。
内部使用 `Lock` 对象，每次调用创建独立锁实例，确保并发安全。

- `lock_key`: 锁标识（支持从函数参数格式化）
- `timeout`: 锁自动过期秒数

---

## 使用示例

```python
from basic_tool.redis import Cache, RedisConfig, CacheHealth

# 初始化
config = RedisConfig(url="redis://localhost:6379/0")
cache = Cache(config)

async def lifespan(app):
    await cache.init()
    yield
    await cache.close()

# 基本操作
await cache.set("user:1", "Alice", ex=3600)
name = await cache.get("user:1")

# JSON 操作
await cache.set_json("user:1:detail", {"name": "Alice", "age": 30}, ex=600)
detail = await cache.get_json("user:1:detail")

# 健康检查
health = CacheHealth(cache)
result = await health.check()
# {"ok": True, "pool": {...}, "ping_ms": 0.5, "error": None}

# 分布式锁
from basic_tool.redis import DistributedLock
dist_lock = DistributedLock(cache)

# 方式 1：async with（推荐）
async with dist_lock.lock("order:123", timeout=60):
    await process_order(123)

# 方式 2：手动控制
lk = dist_lock.get_lock("order:123")
if await lk.acquire(timeout=60):
    try:
        await process_order(123)
    finally:
        await lk.release()

# Lua 脚本
result = await cache.eval(
    'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end',
    1, "lock:1", "token_abc"
)

# 注册可复用脚本
incr_script = cache.register_script(
    'local v = tonumber(redis.call("get", KEYS[1])) + tonumber(ARGV[1]); '
    'redis.call("set", KEYS[1], tostring(v)); return v'
)
result = await incr_script(keys=["counter"], args=["10"])

# 原始命令
result = await cache.execute_command("XADD", "mystream", "*", "name", "Alice")

# Pub/Sub
ps = await cache.subscribe("events")
async for msg in ps.listen():
    if msg["type"] == "message":
        print(msg["data"])

# Sorted Set（限流、排行榜等）
await cache.zadd("leaderboard", {"alice": 100, "bob": 85})
top = await cache.zrange("leaderboard", 0, -1, desc=True, withscores=True)

# 缓存装饰器
from basic_tool.redis import cached

@cached(prefix="user", ttl=600)
async def get_user(cache: Cache, user_id: int):
    return await db.query("SELECT * FROM users WHERE id = ?", user_id)
```
