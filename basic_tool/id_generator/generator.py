"""Snowflake 分布式唯一 ID 生成器与链路追踪 ID 生成器。"""

from __future__ import annotations

import secrets
import threading
import time

from basic_tool.id_generator.config import IDConfig
from basic_tool.id_generator.trace import TraceContext


# Snowflake bit layout constants
_WORKER_BITS = 10       # worker_id occupies 10 bits
_SEQUENCE_BITS = 12     # sequence occupies 12 bits
_MAX_WORKER_ID = (1 << _WORKER_BITS) - 1       # 1023
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1       # 4095
_WORKER_SHIFT = _SEQUENCE_BITS                  # 12
_TIMESTAMP_SHIFT = _SEQUENCE_BITS + _WORKER_BITS  # 22


class IDGenerator:
    """Snowflake 分布式唯一 ID 生成器。

    生成 64-bit 整数 ID，趋势递增，全局唯一。
    纯 Python 实现，零外部依赖，线程安全。

    64-bit 布局:
        [1 bit unused][41 bits timestamp][10 bits worker_id][12 bits sequence]

    用法:
        config = IDConfig(worker_id=1)
        gen = IDGenerator(config)

        # 单个生成
        id1 = gen.new()              # int: 7350283750400000001

        # 批量生成
        ids = gen.batch(100)         # list[int]: 100 个唯一 ID

        # 带前缀的字符串 ID（业务展示用）
        order_id = gen.new_prefixed("ORD")  # "ORD_7350283750400000001"
    """

    def __init__(self, config: IDConfig) -> None:
        self._worker_id = config.worker_id
        self._epoch = config.epoch
        self._lock = threading.Lock()
        self._sequence = 0
        self._last_ts = -1

    def _current_ms(self) -> int:
        """当前毫秒时间戳。"""
        return int(time.time() * 1000)

    def _wait_next_ms(self, ts: int) -> int:
        """自旋等待到下一毫秒。"""
        while True:
            now = self._current_ms()
            if now > ts:
                return now

    def _next_id_unlocked(self) -> int:
        """在锁内生成一个 ID（核心算法）。"""
        ts = self._current_ms()

        if ts < self._last_ts:
            # 时钟回拨保护：等待到上次生成的时间戳
            ts = self._wait_next_ms(self._last_ts)

        if ts == self._last_ts:
            # 同毫秒内，sequence 自增
            self._sequence = (self._sequence + 1) & _MAX_SEQUENCE
            if self._sequence == 0:
                # sequence 溢出，等待下一毫秒
                ts = self._wait_next_ms(ts)
        else:
            # 新毫秒，sequence 重置
            self._sequence = 0

        self._last_ts = ts

        return (
            ((ts - self._epoch) << _TIMESTAMP_SHIFT)
            | (self._worker_id << _WORKER_SHIFT)
            | self._sequence
        )

    def new(self) -> int:
        """生成一个唯一的 Snowflake ID。

        Returns:
            64-bit 整数，趋势递增，全局唯一。
        """
        with self._lock:
            return self._next_id_unlocked()

    def batch(self, count: int) -> list[int]:
        """批量生成唯一 ID。

        同一调用内的 ID 保证唯一且连续递增。
        比循环调用 new() 更高效（减少锁竞争）。

        Args:
            count: 需要生成的 ID 数量，必须 > 0。

        Returns:
            长度为 count 的 list[int]，每个元素唯一。

        Raises:
            ValueError: count <= 0。
        """
        if count <= 0:
            raise ValueError(f"count must be > 0, got {count}")

        result: list[int] = []
        with self._lock:
            for _ in range(count):
                result.append(self._next_id_unlocked())
        return result

    def new_prefixed(self, prefix: str) -> str:
        """生成带业务前缀的字符串 ID。

        适用于订单号、流水号等需要业务标识的场景。

        Args:
            prefix: 业务前缀，如 "ORD", "TXN", "MSG"。

        Returns:
            如 "ORD_7350283750400000001"。
        """
        return f"{prefix}_{self.new()}"


class TraceGenerator:
    """链路追踪 ID 生成器。

    提供 trace_id / span_id 的快速生成能力，
    以及从 HTTP header 解析链路上下文的便捷方法。

    用法:
        gen = TraceGenerator()

        # 生成新的 trace（入口服务）
        ctx = gen.new_trace()

        # 只生成 trace_id（轻量场景，如日志标记）
        trace_id = gen.trace_id()   # "4bf92f3577b34da6a3ce929d0e0e4736"

        # 只生成 span_id
        span_id = gen.span_id()     # "a3ce929d0e0e4736"

        # 从 header 解析
        ctx = gen.from_traceparent(request.headers["traceparent"])
    """

    def new_trace(self) -> TraceContext:
        """创建全新的根 trace 上下文。

        Returns:
            TraceContext，trace_id 和 span_id 均为新生成。
        """
        return TraceContext.root()

    def trace_id(self) -> str:
        """生成一个 128-bit trace_id（32 位 hex）。

        Returns:
            32 字符的 hex 字符串。
        """
        return secrets.token_hex(16)

    def span_id(self) -> str:
        """生成一个 64-bit span_id（16 位 hex）。

        Returns:
            16 字符的 hex 字符串。
        """
        return secrets.token_hex(8)

    @staticmethod
    def from_traceparent(header: str) -> TraceContext:
        """从 W3C traceparent header 解析链路上下文。

        Args:
            header: traceparent 字符串。

        Returns:
            解析后的 TraceContext。

        Raises:
            ValueError: header 格式不合法。
        """
        return TraceContext.from_traceparent(header)
