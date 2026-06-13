"""
Redis 异步客户端模块。

负责创建和管理 Redis 连接池与客户端实例。
所有业务模块通过 Cache 类获取统一的 Redis 能力。

Cache 通过 Mixin 模式组织，Mixin 文件位于同目录下：
- _string: String / Key 通用操作
- _hash: Hash 操作
- _set: Set 操作
- _list: List 操作（含阻塞命令）
- _sorted_set: Sorted Set 操作
- _script: Lua 脚本
- _pubsub: Pub/Sub 消息
- _json: JSON 序列化快捷方式
- _raw: 原始命令 / Pipeline
- _stream: Stream 操作

使用方式:
    cache = Cache(RedisConfig(url="redis://localhost:6379/0"))
    await cache.init()
    await cache.set("key", "value", ex=60)
    val = await cache.get("key")
    await cache.close()
"""

from loguru import logger

from redis.asyncio import ConnectionPool, Redis

from basic_tool.redis.client._hash import HashMixin
from basic_tool.redis.client._json import JsonMixin
from basic_tool.redis.client._list import ListMixin
from basic_tool.redis.client._pubsub import PubSubMixin
from basic_tool.redis.client._raw import RawMixin
from basic_tool.redis.client._script import ScriptMixin
from basic_tool.redis.client._set import SetMixin
from basic_tool.redis.client._sorted_set import SortedSetMixin
from basic_tool.redis.client._stream import StreamMixin
from basic_tool.redis.client._string import StringMixin
from basic_tool.redis.config import RedisConfig


class Cache(
    StringMixin,
    HashMixin,
    SetMixin,
    ListMixin,
    SortedSetMixin,
    ScriptMixin,
    PubSubMixin,
    JsonMixin,
    RawMixin,
    StreamMixin,
):
    """
    Redis 异步客户端，生命周期由业务方管理。

    通过 Mixin 组合提供:
    - 连接池生命周期管理（init / close）
    - String / Hash / Set / List / Sorted Set 操作
    - JSON 序列化快捷方式
    - Lua 脚本执行
    - Pub/Sub 消息
    - 原始命令 / Pipeline
    - 底层 Redis 实例透出（client 属性）

    用法:
        cache = Cache(RedisConfig(url="redis://localhost:6379/0"))
        await cache.init()      # FastAPI lifespan startup
        # ... 业务代码中使用 ...
        await cache.close()     # FastAPI lifespan shutdown
    """

    def __init__(self, config: RedisConfig) -> None:
        """
        初始化 Cache 实例。

        注意: 此方法仅保存配置，不创建连接。
        需要调用 init() 才会真正建立连接池。

        Args:
            config: Redis 连接配置
        """
        self._config = config
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        """
        获取底层 redis.asyncio.Redis 实例。

        当需要 Cache 未封装的 Redis 命令时，可通过此属性直接调用。
        例如: await cache.client.xadd("stream", {"f": "v"})

        Returns:
            Redis: 底层异步客户端实例

        Raises:
            RuntimeError: 未调用 init() 就访问此属性时抛出
        """
        if self._client is None:
            raise RuntimeError(
                "Redis 客户端未初始化，请先调用 init() "
                "（通常在 FastAPI lifespan startup 中）"
            )
        return self._client

    async def init(self) -> None:
        """
        创建连接池并初始化客户端实例。

        连接池参数说明:
        - max_connections: 连接池上限，防止耗尽 Redis 服务端连接
        - socket_connect_timeout: TCP 建连超时
        - socket_timeout: 读写超时，防止慢查询卡住连接
        - socket_keepalive: 启用 TCP keepalive，检测对端断开
        - retry_on_timeout: 超时时自动重试
        - health_check_interval: 每 N 秒对空闲连接发 PING 探活

        如果已经初始化过，跳过重复调用。

        注意: 此方法会通过 PING 验证连接可用性。
        连接失败时会清理资源并抛出异常。

        Raises:
            redis.exceptions.RedisError: 连接 Redis 失败时抛出
        """
        if self._client is not None:
            logger.warning("Redis 连接池已初始化，跳过重复调用")
            return

        self._pool = ConnectionPool.from_url(
            self._config.url,
            max_connections=self._config.max_connections,
            socket_connect_timeout=self._config.socket_connect_timeout,
            socket_timeout=self._config.socket_timeout,
            socket_keepalive=self._config.socket_keepalive,
            retry_on_timeout=self._config.retry_on_timeout,
            health_check_interval=self._config.health_check_interval,
            decode_responses=self._config.decode_responses,
        )

        self._client = Redis(connection_pool=self._pool)

        # 验证连接可用性
        try:
            await self._client.ping()
        except Exception as e:
            logger.error("Redis 连接失败 | url={} error={}", self._config.url, e)
            await self._client.aclose()
            self._client = None
            self._pool = None
            raise

        logger.info(
            "Redis 连接池初始化完成 | max_connections={} health_check={}s",
            self._config.max_connections,
            self._config.health_check_interval,
        )

    async def close(self) -> None:
        """
        优雅关闭连接池，释放所有 TCP 连接。

        在 FastAPI lifespan shutdown 时调用，确保无连接泄漏。
        关闭后 _client 和 _pool 置为 None，可安全重新 init()。
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._pool = None
            logger.info("Redis 连接池已关闭")
