"""W3C Trace Context 链路追踪上下文。"""

from __future__ import annotations

import re
import secrets


class TraceContext:
    """W3C Trace Context 兼容的链路追踪上下文。

    trace_id: 128-bit（32 位 hex），全局唯一，贯穿整条调用链
    span_id: 64-bit（16 位 hex），当前操作 ID
    parent_span_id: 上一级 span ID，根 span 为空

    用法:
        # 入口服务：创建新的 trace
        ctx = TraceContext.root()

        # 下游服务：从 traceparent header 解析
        ctx = TraceContext.from_traceparent("00-4bf92f...-a3ce929d-01")

        # 跨服务传播：写入 HTTP header
        headers = {"traceparent": ctx.to_traceparent()}

        # 进入子操作：创建 child span
        child = ctx.child_span()
    """

    __slots__ = ("trace_id", "span_id", "parent_span_id")

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: str = "",
    ) -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id

    @classmethod
    def root(cls) -> TraceContext:
        """创建新的根 trace（入口服务调用）。

        Returns:
            全新的 TraceContext，parent_span_id 为空。
        """
        return cls(
            trace_id=secrets.token_hex(16),  # 128-bit = 32 hex chars
            span_id=secrets.token_hex(8),  # 64-bit = 16 hex chars
        )

    def child_span(self) -> TraceContext:
        """创建子 span（进入下游操作时调用）。

        Returns:
            新的 TraceContext，共享同一 trace_id，
            当前 span_id 成为 parent_span_id。
        """
        return TraceContext(
            trace_id=self.trace_id,
            span_id=secrets.token_hex(8),
            parent_span_id=self.span_id,
        )

    def to_traceparent(self) -> str:
        """序列化为 W3C traceparent header 格式。

        格式: {version}-{trace_id}-{span_id}-{flags}
        version 固定 "00"，flags 固定 "01"（sampled）

        Returns:
            如 "00-4bf92f3577b34da6a3ce929d0e0e4736-a3ce929d0e0e4736-01"
        """
        return f"00-{self.trace_id}-{self.span_id}-01"

    @classmethod
    def from_traceparent(cls, header: str) -> TraceContext:
        """从 W3C traceparent header 解析上下文。

        Args:
            header: traceparent 字符串，格式 "00-{trace_id}-{span_id}-{flags}"

        Returns:
            解析后的 TraceContext。

        Raises:
            ValueError: header 格式不合法（格式错误、版本号不支持、
                trace_id/span_id 长度不对、包含非 hex 字符）。
        """
        parts = header.split("-")
        if len(parts) != 4:
            raise ValueError(f"invalid traceparent format: {header}")
        version, trace_id, span_id, _flags = parts
        if version != "00":
            raise ValueError(f"unsupported traceparent version: {version}")
        if len(trace_id) != 32:
            raise ValueError(f"trace_id must be 32 hex chars, got {len(trace_id)}")
        if len(span_id) != 16:
            raise ValueError(f"span_id must be 16 hex chars, got {len(span_id)}")
        # Hex format validation (fix from Metis review)
        _HEX_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
        if not _HEX_RE.match(trace_id):
            raise ValueError(f"trace_id contains non-hex characters: {trace_id}")
        _HEX16_RE = re.compile(r"^[0-9a-f]{16}$", re.IGNORECASE)
        if not _HEX16_RE.match(span_id):
            raise ValueError(f"span_id contains non-hex characters: {span_id}")
        return cls(trace_id=trace_id, span_id=span_id)

    def __repr__(self) -> str:
        return f"TraceContext(trace_id={self.trace_id}, span_id={self.span_id})"
