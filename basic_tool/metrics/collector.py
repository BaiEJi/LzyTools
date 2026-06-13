"""
Metrics 采集器。

提供 counter/gauge/histogram 指标记录、内存缓冲、Prometheus exposition 格式输出、
定时刷新到 VictoriaMetrics 的能力。
"""

import asyncio
from collections import defaultdict

import httpx
from loguru import logger

from basic_tool.metrics.config import MetricsConfig
from basic_tool.metrics.models import MetricPoint, MetricType


class MetricsCollector:
    """指标采集器，提供内存缓冲和 Prometheus 格式输出。

    通过 counter/gauge/histogram 方法记录指标点到内存缓冲区，
    可生成 Prometheus exposition 格式文本，或通过后台任务定时刷新到远端。

    使用示例::

        config = MetricsConfig(service_name="my_app", flush_interval=10.0)
        collector = MetricsCollector(config, endpoint="http://vm:8428/api/v1/import/prometheus")
        await collector.init()

        collector.counter("http_requests_total", labels={"method": "GET"})
        collector.gauge("queue_depth", 42)
        collector.histogram("request_duration_seconds", 0.15)

        text = collector.prometheus_exposition()  # Prometheus 格式输出

        await collector.close()

    Attributes:
        _config: Metrics 配置实例。
        _endpoint: VictoriaMetrics 写入地址。
        _buffers: 按指标名分组的内存缓冲区。
        _http: httpx 异步客户端（init 后创建）。
        _flush_task: 后台定时刷新任务。
    """

    def __init__(self, config: MetricsConfig, endpoint: str) -> None:
        """初始化采集器。

        Args:
            config: Metrics 配置实例。
            endpoint: VictoriaMetrics 写入端点 URL。
        """
        self._config = config
        self._endpoint = endpoint
        self._buffers: defaultdict[str, list[MetricPoint]] = defaultdict(list)
        self._http: httpx.AsyncClient | None = None
        self._flush_task: asyncio.Task | None = None

    async def init(self) -> None:
        """初始化 httpx 客户端并启动后台刷新任务。

        创建 ``self._http`` 异步客户端用于后续 POST 刷新，
        同时启动 ``self._flush_task`` 后台协程定时刷新缓冲区到远端。
        """
        self._http = httpx.AsyncClient()
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def close(self) -> None:
        """关闭采集器，取消后台任务并释放 httpx 客户端。

        幂等操作：多次调用安全，不会重复取消已取消的任务或关闭已关闭的客户端。
        """
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """记录 counter 类型指标点。

        Args:
            name: 指标名称。
            value: 指标值，默认 1.0。
            labels: 标签键值对，默认空字典。
        """
        self._buffers[name].append(
            MetricPoint(name=name, value=value, type=MetricType.COUNTER, labels=labels or {})
        )

    def gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """记录 gauge 类型指标点。

        Args:
            name: 指标名称。
            value: 指标值。
            labels: 标签键值对，默认空字典。
        """
        self._buffers[name].append(
            MetricPoint(name=name, value=value, type=MetricType.GAUGE, labels=labels or {})
        )

    def histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """记录 histogram 类型指标点。

        Args:
            name: 指标名称。
            value: 指标值。
            labels: 标签键值对，默认空字典。
        """
        self._buffers[name].append(
            MetricPoint(name=name, value=value, type=MetricType.HISTOGRAM, labels=labels or {})
        )

    def prometheus_exposition(self) -> str:
        """生成 Prometheus text exposition 格式字符串。

        按指标名分组，每个指标输出 HELP/TYPE 头，然后按标签集合聚合输出数据行。
        相同标签集合的多个点会聚合成一行（值求和）。

        Returns:
            Prometheus exposition 格式文本；缓冲区为空时返回 ``"\\n"``。
        """
        if not any(self._buffers.values()):
            return "\n"

        sections: list[str] = []
        for name, points in self._buffers.items():
            if not points:
                continue
            metric_type = points[0].type.value
            lines = [f"# HELP {name} {name}", f"# TYPE {name} {metric_type}"]
            # aggregate by label set using hashable tuple key (no eval)
            aggregated: dict[tuple, float] = {}
            label_sets: dict[tuple, dict[str, str]] = {}
            for p in points:
                key = tuple(sorted(p.labels.items()))
                if key not in aggregated:
                    aggregated[key] = 0.0
                    label_sets[key] = p.labels
                aggregated[key] += p.value
            for key, total in aggregated.items():
                labels = label_sets[key]
                if labels:
                    label_str = ",".join(
                        f'{k}="{v}"' for k, v in sorted(labels.items())
                    )
                    lines.append(f"{name}{{{label_str}}} {total}")
                else:
                    lines.append(f"{name} {total}")
            sections.append("\n".join(lines))
        return "\n".join(sections) + "\n"

    async def _flush_loop(self) -> None:
        """后台定时刷新循环。

        按 ``flush_interval`` 间隔周期性地将缓冲区数据刷新到远端。
        单次刷新失败不会中断循环，仅记录警告日志。
        """
        while True:
            await asyncio.sleep(self._config.flush_interval)
            try:
                await self._do_flush()
            except Exception:
                logger.warning("flush 失败", exc_info=True)

    async def _do_flush(self) -> None:
        """将当前缓冲区数据刷新到 VictoriaMetrics。

        采用 copy-then-clear 模式：先快照当前缓冲区数据，生成 exposition 文本后
        POST 到远端。仅在 POST 成功（``raise_for_status`` 未抛异常）时清空缓冲区，
        失败时保留数据等待下次重试。

        Raises:
            httpx.HTTPStatusError: 远端返回非 2xx 状态码时抛出（缓冲区不清空）。
        """
        if self._http is None:
            return
        # snapshot current buffers
        snapshot: dict[str, list[MetricPoint]] = {}
        for name, points in self._buffers.items():
            if points:
                snapshot[name] = list(points)
        if not snapshot:
            return
        body = self.prometheus_exposition()
        resp = await self._http.post(self._endpoint, content=body)
        resp.raise_for_status()
        # only clear on success
        for name in snapshot:
            self._buffers[name].clear()
