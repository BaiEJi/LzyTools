"""
Metrics 写入器。

提供将指标批量写入 Redis Streams（缓冲）和 VictoriaMetrics（持久化）的能力。
Redis Streams 作为缓冲层，VictoriaMetrics 作为最终存储。
"""

import httpx
from loguru import logger

from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.models import MetricBatch, MetricPoint
from basic_tool.redis import Cache


class MetricsWriter:
    """
    指标写入器，负责将指标批量写入 Redis Stream 和 VictoriaMetrics。

    Redis Stream 作为缓冲层暂存指标点，VictoriaMetrics 作为最终持久化存储。
    通过 ``init()`` 初始化 httpx 客户端，``close()`` 释放资源。

    使用示例::

        config = MetricsConfig(vm_url="http://vm:8428")
        writer = MetricsWriter(config, cache=cache)
        await writer.init()

        batch = MetricBatch(points=[MetricPoint(name="cpu", value=80.5)], source="svc")
        await writer.write_batch(batch)    # 写入 Redis Stream
        await writer.flush_to_vm(batch)    # 刷新到 VictoriaMetrics

        await writer.close()

    Attributes:
        _config: Metrics 配置实例。
        _cache: Redis Cache 实例（用于 Stream 写入）。
        _http: httpx 异步客户端（init 后创建，复用连接）。
        _initialized: 是否已初始化。
    """

    def __init__(self, config: MetricsConfig, cache: Cache | None = None) -> None:
        """初始化写入器。

        Args:
            config: Metrics 配置实例。
            cache: Redis Cache 实例，用于 Stream 写入。
        """
        self._config = config
        self._cache: Cache | None = cache
        self._http: httpx.AsyncClient | None = None
        self._initialized = False

    async def init(self) -> None:
        """初始化 httpx 异步客户端。

        创建指向 VictoriaMetrics 的 ``httpx.AsyncClient``，复用连接。
        标记 ``_initialized`` 为 True，使 ``cache`` 属性可用。
        """
        self._http = httpx.AsyncClient(base_url=self._config.vm_url)
        self._initialized = True

    async def close(self) -> None:
        """关闭 httpx 客户端，标记未初始化。

        幂等操作：多次调用安全，不会重复关闭已关闭的客户端。
        """
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._initialized = False

    @property
    def cache(self) -> Cache:
        """获取 Cache 实例。

        Returns:
            Redis Cache 实例。

        Raises:
            RuntimeError: 未调用 init() 就访问此属性时抛出。
        """
        if not self._initialized or self._cache is None:
            raise RuntimeError("MetricsWriter 未初始化，请先调用 init()")
        return self._cache

    async def write_batch(self, batch: MetricBatch) -> int:
        """将一批指标点写入 Redis Stream。

        每个 ``MetricPoint`` 序列化为一个 Stream entry，字段包含 name/value/type
        以及带 ``label_`` 前缀的标签。Stream key 格式为
        ``{stream_prefix}:{source}``。

        Args:
            batch: 指标批次。

        Returns:
            写入的指标点数量；空批次返回 0。
        """
        if not batch.points:
            return 0
        stream_key = f"{self._config.stream_prefix}:{batch.source}"
        count = 0
        for point in batch.points:
            fields = {
                "name": point.name,
                "value": str(point.value),
                "type": point.type.value,
            }
            for k, v in point.labels.items():
                fields[f"label_{k}"] = v
            await self.cache.xadd(
                stream_key, fields, maxlen=self._config.stream_max_len
            )
            count += 1
        logger.info("写入 Redis Stream | stream={} count={}", stream_key, count)
        return count

    async def flush_to_vm(self, batch: MetricBatch) -> int:
        """将一批指标点刷新到 VictoriaMetrics。

        以 Prometheus exposition 文本格式 POST 到
        ``/api/v1/import/prometheus`` 端点。每个指标点输出一行，
        带标签时格式为 ``name{label="val"} value``，无标签时为 ``name value``。

        Args:
            batch: 指标批次。

        Returns:
            发送的指标点数量；空批次返回 0（不发送请求）。

        Raises:
            httpx.HTTPStatusError: 远端返回非 2xx 状态码时抛出。
        """
        if not batch.points:
            return 0
        if self._http is None:
            return 0
        lines = []
        for point in batch.points:
            name = point.name
            labels = point.labels
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {point.value}")
            else:
                lines.append(f"{name} {point.value}")
        body = "\n".join(lines) + "\n"
        resp = await self._http.post("/api/v1/import/prometheus", content=body)
        resp.raise_for_status()
        logger.info("写入 VictoriaMetrics | count={}", len(batch.points))
        return len(batch.points)
