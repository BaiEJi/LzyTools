"""
Context 模块测试。

测试请求上下文管理、嵌套隔离、异步支持、日志注入、HTTP 传播、
FastAPI 中间件以及并发隔离。覆盖 basic_tool.context 子包的全部公共 API。

采用 TDD RED 阶段：实现尚不存在，测试通过延迟导入（方法内 import）
确保 --collect-only 可收集 25 个用例，运行时因模块缺失而全部失败。
"""

import asyncio
from io import StringIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger


class TestContextBasic:
    """基础上下文操作测试。"""

    def test_request_context_basic(self):
        """进入 request_context 后可读取键值，退出后上下文恢复为空。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="r1", user_id=42):
            assert ctx.get("request_id") == "r1"
            assert ctx.get("user_id") == 42
        assert ctx.getall() == {}

    def test_auto_generate_request_id(self):
        """未提供 request_id 时自动生成 uuid4 hex（32 字符）。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context():
            rid = ctx.get("request_id")
            assert rid is not None
            assert len(rid) == 32

    def test_ctx_set_dynamic(self):
        """ctx.set() 可在当前上下文中动态添加或更新键。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context():
            ctx.set("trace_id", "trace-abc")
            assert ctx.get("trace_id") == "trace-abc"

    def test_ctx_getall_snapshot(self):
        """ctx.getall() 返回包含全部上下文键值副本的字典。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="r1", user_id=42):
            assert ctx.getall() == {"request_id": "r1", "user_id": 42}


class TestContextNesting:
    """上下文嵌套与隔离测试。"""

    def test_cleanup_after_exit(self):
        """进入上下文前后 getall() 应正确反映上下文状态。"""
        from basic_tool.context.ctx import ctx, request_context

        assert ctx.getall() == {}
        with request_context(request_id="r1"):
            assert ctx.getall() != {}
        assert ctx.getall() == {}

    def test_nested_override(self):
        """嵌套上下文内层可覆盖外层键，退出后恢复外层值。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="outer"):
            with request_context(request_id="inner"):
                assert ctx.get("request_id") == "inner"
            assert ctx.get("request_id") == "outer"

    def test_nested_new_key_disappears(self):
        """内层上下文中 ctx.set() 添加的键在退出后消失。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="r1"):
            with request_context(request_id="r2"):
                ctx.set("temp_key", "temp_val")
                assert ctx.get("temp_key") == "temp_val"
            assert ctx.get("temp_key") is None


class TestContextAsync:
    """异步上下文支持测试。"""

    async def test_async_with_usage(self):
        """支持 async with 语法使用请求上下文。"""
        from basic_tool.context.ctx import ctx, request_context

        async with request_context(request_id="async-1"):
            assert ctx.get("request_id") == "async-1"
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

        with request_context(request_id="dump-test", user_id=7):
            dump_str = ctx.dump()
            assert isinstance(dump_str, str)
            assert "dump-test" in dump_str

    def test_ctx_clear(self):
        """ctx.clear() 清空当前上下文字典。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="r1", user_id=42):
            ctx.clear()
            assert ctx.getall() == {}

    def test_ctx_get_default(self):
        """ctx.get() 对不存在的键返回默认值或缺省 None。"""
        from basic_tool.context.ctx import ctx, request_context

        with request_context(request_id="r1"):
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
            buf, format="{extra[request_id]}|{message}", level="DEBUG", enqueue=False
        )

        with request_context(request_id="log-test", user_id=99):
            logger.info("hello world")

        output = buf.getvalue()
        assert "log-test" in output

        buf2 = StringIO()
        logger.remove()
        enable_log_injection()
        logger.add(
            buf2, format="{extra[request_id]}|{message}", level="DEBUG", enqueue=False
        )

        with request_context(request_id="log-test"):
            logger.info("override test", request_id="override")

        output2 = buf2.getvalue()
        assert "override" in output2

        logger.remove()


class TestPropagation:
    """HTTP 头传播与上下文序列化测试。"""

    def test_get_propagation_headers(self):
        """get_propagation_headers() 按默认映射从上下文提取 HTTP 头。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import get_propagation_headers

        with request_context(request_id="h1", tenant_id="t1"):
            headers = get_propagation_headers()
        assert headers == {"X-Request-Id": "h1", "X-Tenant-Id": "t1"}

    def test_get_propagation_headers_custom_map(self):
        """支持自定义 header_map 参数映射上下文键到头名。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import get_propagation_headers

        with request_context(request_id="h1"):
            headers = get_propagation_headers(
                header_map={"request_id": "X-Custom-Id"}
            )
        assert headers == {"X-Custom-Id": "h1"}

    def test_inject_headers_to_httpx(self):
        """inject_headers_to_httpx() 合并上下文头与用户提供的头。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import inject_headers_to_httpx

        with request_context(request_id="h1"):
            result = inject_headers_to_httpx({"Authorization": "Bearer x"})
        assert result["X-Request-Id"] == "h1"
        assert result["Authorization"] == "Bearer x"

    def test_inject_headers_to_httpx_user_priority(self):
        """用户提供的同名头优先于上下文传播头。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import inject_headers_to_httpx

        with request_context(request_id="ctx-id"):
            result = inject_headers_to_httpx({"X-Request-Id": "user-id"})
        assert result["X-Request-Id"] == "user-id"

    def test_serialize_context(self):
        """serialize_context() 返回当前上下文的快照副本。"""
        from basic_tool.context.ctx import request_context
        from basic_tool.context.propagation import serialize_context

        with request_context(request_id="s1", user_id=42):
            data = serialize_context()
        assert data["request_id"] == "s1"
        assert data["user_id"] == 42

    def test_deserialize_context(self):
        """deserialize_context() 从序列化数据恢复上下文。"""
        from basic_tool.context.ctx import ctx, request_context
        from basic_tool.context.propagation import deserialize_context, serialize_context

        with request_context(request_id="s1", user_id=42):
            data = serialize_context()
        with deserialize_context(data):
            assert ctx.get("request_id") == "s1"
            assert ctx.get("user_id") == 42

    def test_deserialize_context_cleanup(self):
        """deserialize_context() 退出后恢复之前状态，反序列化的键被清除。"""
        from basic_tool.context.ctx import ctx, request_context
        from basic_tool.context.propagation import deserialize_context, serialize_context

        with request_context(request_id="s1"):
            data = serialize_context()
        assert ctx.getall() == {}
        with deserialize_context(data):
            assert ctx.get("request_id") == "s1"
        assert ctx.get("request_id") is None


class TestMiddleware:
    """FastAPI ContextMiddleware 测试。"""

    def test_middleware_request_id_from_header(self):
        """中间件从 X-Request-Id 请求头提取 request_id。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"request_id": ctx.get("request_id")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test", headers={"X-Request-Id": "my-req-123"})
        assert resp.json()["request_id"] == "my-req-123"

    def test_middleware_auto_generate_request_id(self):
        """无 X-Request-Id 头时中间件自动生成 uuid4 hex。"""
        from basic_tool.context.ctx import ctx
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"request_id": ctx.get("request_id")}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        rid = resp.json()["request_id"]
        assert rid is not None
        assert len(rid) == 32

    def test_middleware_response_header(self):
        """响应头包含 X-Request-Id，无请求头时使用自动生成值。"""
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()

        @app.get("/test")
        def get_ctx():
            return {"ok": True}

        app.add_middleware(ContextMiddleware)
        client = TestClient(app)

        resp = client.get("/test", headers={"X-Request-Id": "abc"})
        assert resp.headers["X-Request-Id"] == "abc"

        resp2 = client.get("/test")
        assert "X-Request-Id" in resp2.headers
        assert len(resp2.headers["X-Request-Id"]) == 32

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


class TestConcurrency:
    """并发场景下的上下文隔离测试。"""

    async def test_concurrent_isolation(self):
        """并发任务间上下文隔离，各任务读取各自的 request_id。"""
        from basic_tool.context.ctx import ctx, request_context

        async def task_with_context(req_id):
            with request_context(request_id=req_id):
                await asyncio.sleep(0.01)
                return ctx.get("request_id")

        results = await asyncio.gather(
            task_with_context("req-a"),
            task_with_context("req-b"),
        )
        assert results[0] == "req-a"
        assert results[1] == "req-b"
