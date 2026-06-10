# basic_tool

基础设施库，提供与 Web 框架无关的 Redis 缓存、分布式锁和日志能力。

## 安装

```bash
pip install git+https://github.com/xxx/basic_tool.git
```

## 技术栈

### Redis — `basic_tool.redis`

**底层库：** [redis-py](https://github.com/redis/redis-py)（`redis[hiredis]`），使用 `redis.asyncio` 异步接口，`hiredis` C 扩展加速协议解析。

**设计模式：** Mixin 组合模式。`Cache` 类通过继承 9 个 Mixin 按 Redis 数据类型组织方法：

| Mixin | 文件 | 能力 |
|---|---|---|
| `StringMixin` | `_string.py` | get/set/delete/exists/expire/ttl/pttl/persist/pexpire/incr/decr/mget/mset/scan/scan_iter/append/strlen/getdel/getex/type |
| `HashMixin` | `_hash.py` | hget/hset/hgetall/hdel/hmget/hkeys/hvals/hlen/hexists/hincrby |
| `SetMixin` | `_set.py` | sadd/srem/smembers/sismember/smismember/scard/sinter/sunion/sdiff/srandmember |
| `ListMixin` | `_list.py` | lpush/rpush/lpop/rpop/lrange/llen/lindex/lset/lrem/lmove/blpop/brpop/blmove |
| `SortedSetMixin` | `_sorted_set.py` | zadd/zrem/zrange/zrangebyscore/zcard/zscore/zrank/zrevrange/zrevrank/zincrby/zcount/zlexcount/zremrangebyscore |
| `ScriptMixin` | `_script.py` | eval/evalsha/register_script |
| `PubSubMixin` | `_pubsub.py` | publish/pubsub/subscribe/psubscribe |
| `JsonMixin` | `_json.py` | get_json/set_json（基于 orjson） |
| `RawMixin` | `_raw.py` | execute_command/pipeline |

**连接管理：** 基于 `redis.asyncio.ConnectionPool` 连接池，`init()` 时通过 PING 验证连接可用性。

**生命周期：**

```python
from basic_tool.redis import Cache, RedisConfig

config = RedisConfig(url="redis://localhost:6379/0")
cache = Cache(config)
await cache.init()      # 创建连接池 + PING 验证（FastAPI lifespan startup）
# ... 业务使用 ...
await cache.close()     # 释放连接（FastAPI lifespan shutdown）
```

**附加能力：**

- `DistributedLock` / `Lock` — 基于 Lua 脚本的分布式锁，并发安全（每个 Lock 独立状态）
- `@cached` — 异步函数结果缓存装饰器（支持缓存 None 值）
- `@rate_limit` — 滑动窗口限流装饰器（支持动态 key，抛出 `RateLimitError`）
- `@synchronized` — 分布式锁装饰器（复用 Lock，支持格式化占位符）
- `CacheHealth` — 连接池健康检查（PING + pool stats）

详细 API 文档见 [basic_tool/redis/README.md](basic_tool/redis/README.md)。

---

### Logger — `basic_tool.logger`

**底层库：** [loguru](https://github.com/Delgan/loguru)。

**日志格式：** 支持两种格式

**logfmt**（默认）— 带时间戳的结构化文本：
```
2024-01-15T10:30:00||INFO||app.py:42||user_id=123||action=login||user logged in
```

**JSON**（`json_output=True`）— 便于 ELK/Datadog/Loki 采集：
```json
{"time":"2024-01-15T10:30:00+00:00","level":"INFO","file":"app.py","line":42,"message":"user logged in","user_id":123}
```

**配置：**

```python
from basic_tool.logger import setup, get, LogConfig

# 默认 logfmt 格式
setup(LogConfig(level="DEBUG"))

# JSON 格式 + 多 sink
setup(LogConfig(json_output=True, sink=["sys.stderr", "/var/log/app.log"]))

log = get()  # setup() 前调用会自动以默认配置初始化
log.info("server started", host="0.0.0.0", port=8080)
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `level` | `"INFO"` | 最低日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `sink` | `["sys.stderr"]` | 输出目标列表 |
| `rotation` | `None` | 文件轮转策略，如 `"500 MB"`, `"00:00"` |
| `retention` | `None` | 文件保留策略，如 `"10 days"` |
| `enqueue` | `True` | 线程安全写入（后台线程排队） |
| `json_output` | `False` | JSON 格式输出 |
| `backtrace` | `True` | 异常时打印完整调用栈 |
| `diagnose` | `False` | 异常时显示变量值 |

详细 API 文档见 [basic_tool/logger/README.md](basic_tool/logger/README.md)。

---

## 依赖

| 依赖 | 用途 |
|---|---|
| `redis[hiredis]>=5.0.0` | Redis 异步客户端 + C 扩展加速解析 |
| `orjson>=3.9.0` | 高性能 JSON 序列化（`get_json`/`set_json` + Logger JSON 模式） |
| `pydantic>=2.0.0` | 配置类校验（`RedisConfig`） |
| `loguru>=0.7.0` | 日志系统 |

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
