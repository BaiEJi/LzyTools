"""
Context 模块测试。

测试请求上下文管理、嵌套隔离、异步支持、日志注入、HTTP 传播、
FastAPI 中间件以及并发隔离。覆盖 basic_tool.context 子包的全部公共 API。

采用方法内 import 风格，确保每个测试独立可读。
"""

import asyncio
from io import StringIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class TestContextBasic:
    """基础上下文操作测试。"""

    def test_request_context_basic(self):
        """进入 request_context 后可读取键值，退出后上下文恢复为空。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="t1", user_id=42):
            assert ctx.get("trace_id") == "t1"
            assert ctx.get("user_id") == 42
        assert ctx.getall() == {}

    def test_auto_generate_trace_id(self):
        """未提供 trace_id 时自动生成 128-bit hex（32 字符）。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context():
            tid = ctx.get("trace_id")
            assert tid is not None
            assert len(tid) == 32

    def test_ctx_set_dynamic(self):
        """ctx.set() 可在当前上下文中动态添加或更新键。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context():
            ctx.set("trace_id", "trace-abc")
            assert ctx.get("trace_id") == "trace-abc"

    def test_ctx_getall_snapshot(self):
        """ctx.getall() 返回包含全部上下文键值副本的字典。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="t1", user_id=42):
            assert ctx.getall() == {"trace_id": "t1", "user_id": 42}


class TestContextNesting:
    """上下文嵌套与隔离测试。"""

    def test_cleanup_after_exit(self):
        """进入上下文前后 getall() 应正确反映上下文状态。"""
        from basic_tool.context.ctx import ctx, request_context

        assert ctx.getall() == {}
        with request_context(trace_id="t1"):
            assert ctx.getall() != {}
        assert ctx.getall() == {}

    def test_nested_override(self):
        """嵌套上下文内层可覆盖外层键，退出后恢复外层值。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="outer"):
            with request_context(trace_id="inner"):
                assert ctx.get("trace_id") == "inner"
            assert ctx.get("trace_id") == "outer"

    def test_nested_new_key_disappears(self):
        """内层上下文中 ctx.set() 添加的键在退出后消失。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="t1"):
            with request_context(trace_id="t2"):
                ctx.set("temp_key", "temp_val")
                assert ctx.get("temp_key") == "temp_val"
            assert ctx.get("temp_key") is None


class TestContextAsync:
    """异步上下文支持测试。"""

    async def test_async_with_usage(self):
        """支持 async with 语法使用请求上下文。"""
        from basic_tool.context.ctx import ctx, request_context

        async with request_context(trace_id="async-1"):
            assert ctx.get("trace_id") == "async-1"
        assert ctx.getall() == {}

    async def test_async_task_inheritance(self):
        """子 asyncio.Task 继承父上下文中的键值。"""
        from basic_tool.context.ctx import ctx, request_context

        async def child():
            return ctx.get("parent_key")

        with request_context(parent_key="parent_value"):
            result = await asyncio.create_task(child())
        assert result == "parent_value"


class TestContextUtilities:
    """上下文工具方法测试。"""

    def test_ctx_dump(self):
        """ctx.dump() 返回包含上下文键的可读字符串。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="dump-test", user_id=7):
            dump_str = ctx.dump()
            assert isinstance(dump_str, str)
            assert "dump-test" in dump_str

    def test_ctx_clear(self):
        """ctx.clear() 清空当前上下文字典。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="t1", user_id=42):
            ctx.clear()
            assert ctx.getall() == {}

    def test_ctx_get_default(self):
        """ctx.get() 对不存在的键返回默认值或缺省 None。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(trace_id="t1"):
            assert ctx.get("nonexistent", default="fallback") == "fallback"
            assert ctx.get("nonexistent") is None


class TestLogInjection:
    """日志上下文注入测试。"""

    def test_enable_log_injection(self):
        """enable_log_injection() 将上下文字段注入日志记录，用户 extra 优先。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.log_extra import enable_log_injection

        buf = StringIO()
        logger.remove()
        enable_log_injection()
        logger.add(
            buf, format="{extra[trace_id]}|{message}", level="DEBUG", enqueue=False
        )

        with request_context(trace_id="log-test", user_id=99):
            logger.info("hello world")

        output = buf.getvalue()
        assert "log-test" in output

        buf2 = StringIO()
        logger.remove()
        enable_log_injection()
        logger.add(
            buf2, format="{extra[trace_id]}|{message}", level="DEBUG", enqueue=False
        )

        with request_context(trace_id="log-test"):
            logger.info("override test", trace_id="override")

        output2 = buf2.getvalue()
        assert "override" in output2

        logger.remove()

    def test_enable_log_injection_idempotent(self):
        """enable_log_injection() 幂等：多次调用不会叠加 patcher。"""
        import loguru

        import basic_tool.context.log_extra as log_extra
        from basic_tool.context.log_extra import enable_log_injection

        log_extra._log_injection_enabled = False

        enable_log_injection()
        assert log_extra._log_injection_enabled is True

        options_after_first = loguru.logger._options

        enable_log_injection()
        assert loguru.logger._options is options_after_first


class TestPropagation:
    """HTTP 头传播与上下文序列化测试。"""

    def test_get_propagation_headers(self):
        """get_propagation_headers() 按默认映射从上下文提取 HTTP 头并重建 traceparent。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import get_propagation_headers

        with request_context(trace_id="t1", span_id="s1", tenant_id="ten1"):
            headers = get_propagation_headers()
        assert headers == {
            "X-Trace-Id": "t1",
            "X-Span-Id": "s1",
            "X-Tenant-Id": "ten1",
            "traceparent": "00-t1-s1-01",
        }

    def test_get_propagation_headers_custom_map(self):
        """支持自定义 header_map 参数映射上下文键到头名。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import get_propagation_headers

        with request_context(trace_id="t1"):
            headers = get_propagation_headers(
                header_map={"trace_id": "X-Custom-Id"}
            )
        assert headers == {"X-Custom-Id": "t1"}

    def test_inject_headers_to_httpx(self):
        """inject_headers_to_httpx() 合并上下文头与用户提供的头。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import inject_headers_to_httpx

        with request_context(trace_id="t1"):
            result = inject_headers_to_httpx({"Authorization": "Bearer x"})
        assert result["X-Trace-Id"] == "t1"
        assert result["Authorization"] == "Bearer x"

    def test_inject_headers_to_httpx_user_priority(self):
        """用户提供的同名头优先于上下文传播头。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import inject_headers_to_httpx

        with request_context(trace_id="ctx-id"):
            result = inject_headers_to_httpx({"X-Trace-Id": "user-id"})
        assert result["X-Trace-Id"] == "user-id"

    def test_serialize_context(self):
        """serialize_context() 返回当前上下文的快照副本。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import serialize_context

        with request_context(trace_id="s1", user_id=42):
            data = serialize_context()
        assert data["trace_id"] == "s1"
        assert data["user_id"] == 42

    def test_deserialize_context(self):
        """deserialize_context() 从序列化数据恢复上下文。"""
        from basic_tool.context.ctx import ctx, request_context
        from basic_tool.context.propagation import deserialize_context, serialize_context

        with request_context(trace_id="s1", user_id=42):
            data = serialize_context()
        with deserialize_context(data):
            assert ctx.get("trace_id") == "s1"
            assert ctx.get("user_id") == 42

    def test_deserialize_context_cleanup(self):
        """deserialize_context() 退出后恢复之前状态，反序列化的键被清除。"""
        from basic_tool.context.ctx import ctx, request_context
        from basic_tool.context.propagation import deserialize_context, serialize_context

        with request_context(trace_id="s1"):
            data = serialize_context()
        assert ctx.getall() == {}
        with deserialize_context(data):
            assert ctx.get("trace_id") == "s1"
        assert ctx.get("trace_id") is None


class TestMiddleware:
    """FastAPI ContextMiddleware 测试。"""

    def test_middleware_traceparent_from_header(self):
        """中间件从 traceparent 请求头解析 trace_id（保留上游 trace_id）。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"trace_id": ctx.get("trace_id")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        upstream_tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        resp = client.get("/test", headers={"traceparent": upstream_tp})
        assert resp.json()["trace_id"] == "0af7651916cd43dd8448eb211c80319c"

    def test_middleware_child_span(self):
        """有 traceparent 头时创建 child span：trace_id 保留，span_id 变化，parent_span_id 正确。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {
                "trace_id": ctx.get("trace_id"),
                "span_id": ctx.get("span_id"),
                "parent_span_id": ctx.get("parent_span_id"),
            }

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        upstream_tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        resp = client.get("/test", headers={"traceparent": upstream_tp})
        data = resp.json()
        assert data["trace_id"] == "0af7651916cd43dd8448eb211c80319c"
        assert data["span_id"] != "b7ad6b7169203331"
        assert len(data["span_id"]) == 16
        assert data["parent_span_id"] == "b7ad6b7169203331"

    def test_middleware_auto_generate_root_trace(self):
        """无 traceparent 头时中间件自动生成根 trace（32 hex trace_id）。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"trace_id": ctx.get("trace_id")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        tid = resp.json()["trace_id"]
        assert tid is not None
        assert len(tid) == 32

    def test_middleware_malformed_traceparent(self):
        """malformed traceparent 头时降级为根 trace，返回 HTTP 200。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"trace_id": ctx.get("trace_id")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test", headers={"traceparent": "garbage"})
        assert resp.status_code == 200
        tid = resp.json()["trace_id"]
        assert tid is not None
        assert len(tid) == 32

    def test_middleware_response_header(self):
        """响应头包含 traceparent（child span 或 root trace）。"""
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"ok": True}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)

        upstream_tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        resp = client.get("/test", headers={"traceparent": upstream_tp})
        resp_tp = resp.headers["traceparent"]
        parts = resp_tp.split("-")
        assert parts[0] == "00"
        assert parts[1] == "0af7651916cd43dd8448eb211c80319c"
        assert parts[2] != "b7ad6b7169203331"
        assert parts[3] == "01"

        resp2 = client.get("/test")
        tp2 = resp2.headers["traceparent"]
        parts2 = tp2.split("-")
        assert parts2[0] == "00"
        assert len(parts2[1]) == 32
        assert len(parts2[2]) == 16
        assert parts2[3] == "01"

    def test_middleware_client_ip(self):
        """中间件提取 client_ip 存入上下文。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"client_ip": ctx.get("client_ip")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        assert resp.json()["client_ip"] is not None

    def test_contextvar_propagation_through_middleware(self):
        """ContextMiddleware 设置的 ContextVar 可被内层中间件读取。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()
        captured = {}

        class InnerMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                captured["trace_id"] = ctx.get("trace_id")
                captured["span_id"] = ctx.get("span_id")
                return await call_next(request)

        @app.get("/test")
        def get_ctx():
            return {"ok": True}

        app.add_middleware(InnerMiddleware)
        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert captured["trace_id"] is not None
        assert len(captured["trace_id"]) == 32
        assert captured["span_id"] is not None
        assert len(captured["span_id"]) == 16


class TestConcurrency:
    """并发场景下的上下文隔离测试。"""

    async def test_concurrent_isolation(self):
        """并发任务间上下文隔离，各任务读取各自的 trace_id。"""
        from basic_tool.context.ctx import ctx, request_context

        async def task_with_context(tid):
            with request_context(trace_id=tid):
                await asyncio.sleep(0.01)
                return ctx.get("trace_id")

        results = await asyncio.gather(
            task_with_context("trace-a"),
            task_with_context("trace-b"),
        )
        assert results[0] == "trace-a"
        assert results[1] == "trace-b"
