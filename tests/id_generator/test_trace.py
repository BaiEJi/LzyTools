"""TraceContext 和 TraceGenerator 测试。"""

import re

import pytest

from basic_tool.id_generator.trace import TraceContext
from basic_tool.id_generator.generator import TraceGenerator


class TestTraceContext:
    """TraceContext 核心功能测试。"""

    def test_root(self):
        """新建 trace 的 trace_id/span_id 长度正确，parent_span_id 为空。"""
        ctx = TraceContext.root()
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16
        assert ctx.parent_span_id == ""
        # hex 格式验证
        assert re.match(r"^[0-9a-f]{32}$", ctx.trace_id, re.IGNORECASE)
        assert re.match(r"^[0-9a-f]{16}$", ctx.span_id, re.IGNORECASE)

    def test_child_span(self):
        """子 span 共享 trace_id，span_id 不同，parent_span_id 指向父。"""
        parent = TraceContext.root()
        child = parent.child_span()
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id

    def test_to_traceparent(self):
        """格式验证 "00-{trace_id}-{span_id}-01"。"""
        ctx = TraceContext("a" * 32, "b" * 16)
        tp = ctx.to_traceparent()
        assert tp == f"00-{'a' * 32}-{'b' * 16}-01"

    def test_from_traceparent_valid(self):
        """正确解析合法 header。"""
        header = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        ctx = TraceContext.from_traceparent(header)
        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16

    def test_from_traceparent_invalid_format(self):
        """格式错误抛 ValueError（部分数不对、版本号错、长度错）。"""
        # 部分数不对
        with pytest.raises(ValueError, match="invalid traceparent format"):
            TraceContext.from_traceparent("00-abc-def")

        # 版本号错
        with pytest.raises(ValueError, match="unsupported traceparent version"):
            TraceContext.from_traceparent("01-" + "a" * 32 + "-" + "b" * 16 + "-01")

        # trace_id 长度错
        with pytest.raises(ValueError, match="trace_id must be 32 hex chars"):
            TraceContext.from_traceparent("00-" + "a" * 16 + "-" + "b" * 16 + "-01")

        # span_id 长度错
        with pytest.raises(ValueError, match="span_id must be 16 hex chars"):
            TraceContext.from_traceparent("00-" + "a" * 32 + "-" + "b" * 8 + "-01")

    def test_from_traceparent_invalid_hex(self):
        """非 hex 字符抛 ValueError。"""
        with pytest.raises(ValueError, match="non-hex"):
            TraceContext.from_traceparent("00-" + "z" * 32 + "-" + "a" * 16 + "-01")

    def test_roundtrip(self):
        """from_traceparent(ctx.to_traceparent()) 还原一致。"""
        ctx = TraceContext.root()
        child = ctx.child_span()
        tp = child.to_traceparent()
        parsed = TraceContext.from_traceparent(tp)
        assert parsed.trace_id == child.trace_id
        assert parsed.span_id == child.span_id

    def test_repr(self):
        """__repr__ 输出包含 trace_id 和 span_id。"""
        ctx = TraceContext("abc123", "def456")
        r = repr(ctx)
        assert "abc123" in r
        assert "def456" in r
        assert "TraceContext" in r


class TestTraceGenerator:
    """TraceGenerator 测试。"""

    def test_trace_id_length(self):
        """生成 32 位 hex trace_id。"""
        gen = TraceGenerator()
        tid = gen.trace_id()
        assert len(tid) == 32
        assert re.match(r"^[0-9a-f]{32}$", tid, re.IGNORECASE)

    def test_span_id_length(self):
        """生成 16 位 hex span_id。"""
        gen = TraceGenerator()
        sid = gen.span_id()
        assert len(sid) == 16
        assert re.match(r"^[0-9a-f]{16}$", sid, re.IGNORECASE)

    def test_new_trace(self):
        """返回 TraceContext。"""
        gen = TraceGenerator()
        ctx = gen.new_trace()
        assert isinstance(ctx, TraceContext)
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16

    def test_uniqueness(self):
        """生成 10000 个 trace_id 无重复。"""
        gen = TraceGenerator()
        ids = {gen.trace_id() for _ in range(10000)}
        assert len(ids) == 10000

    def test_from_traceparent(self):
        """从 header 解析 TraceContext。"""
        gen = TraceGenerator()
        header = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        ctx = gen.from_traceparent(header)
        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16
