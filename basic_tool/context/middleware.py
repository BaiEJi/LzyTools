"""FastAPI 请求上下文中间件。

为每个 HTTP 请求创建隔离的请求上下文，基于 W3C Trace Context 规范解析或
创建 trace_id / span_id，提取 client_ip，并在响应头中回传 traceparent，
便于跨服务链路追踪。

核心组件:
- ContextMiddleware: 纯 ASGI 请求上下文中间件
- setup_context_middleware: 便捷注册函数

使用方式:
    from fastapi import FastAPI
    from basic_tool.context.middleware import setup_context_middleware

    app = FastAPI()
    setup_context_middleware(app)
"""

from typing import Awaitable, Callable

from fastapi import FastAPI

from basic_tool.context.ctx import request_context
from basic_tool.id_generator import TraceContext

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class ContextMiddleware:
    """纯 ASGI 请求上下文中间件。

    从 W3C ``traceparent`` 请求头解析链路上下文并创建 child span
    （共享上游 trace_id）；缺失或 malformed 时降级为根 trace。
    同时提取 client_ip（优先 X-Forwarded-For），为每个请求创建隔离的
    ContextVar 上下文，并在响应头中回传 ``traceparent``。

    使用纯 ASGI 实现而非 ``BaseHTTPMiddleware``，以确保 ``traceparent``
    响应头在异常场景下也能正确设置——``BaseHTTPMiddleware`` 的
    ``call_next`` 在异常时会重新抛出而非返回响应，导致由
    ``ServerErrorMiddleware`` 生成的错误响应绕过本中间件。
    """

    def __init__(self, app: ASGIApp) -> None:
        """初始化中间件。

        Args:
            app: 下游 ASGI 应用。
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """处理请求，注入请求上下文并添加 traceparent 响应头。

        Args:
            scope: ASGI scope 字典。
            receive: ASGI receive 可调用对象。
            send: ASGI send 可调用对象。
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: dict[str, str] = {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        traceparent = headers.get("traceparent", "")
        try:
            if traceparent:
                trace_ctx = TraceContext.from_traceparent(traceparent).child_span()
            else:
                raise ValueError("no traceparent")
        except ValueError:
            trace_ctx = TraceContext.root()

        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif scope.get("client"):
            client_ip = scope["client"][0]
        else:
            client_ip = "unknown"

        traceparent_value = trace_ctx.to_traceparent()
        scope["basic_tool.traceparent"] = traceparent_value

        traceparent_bytes = traceparent_value.encode("latin-1")

        async def send_with_traceparent(message: dict) -> None:
            """在 http.response.start 消息中注入 traceparent 响应头。

            Args:
                message: ASGI 消息字典。
            """
            if message["type"] == "http.response.start":
                updated_headers = list(message.get("headers", []))
                updated_headers.append((b"traceparent", traceparent_bytes))
                message = {**message, "headers": updated_headers}
            await send(message)

        with request_context(
            trace_id=trace_ctx.trace_id,
            span_id=trace_ctx.span_id,
            parent_span_id=trace_ctx.parent_span_id,
            client_ip=client_ip,
        ):
            await self.app(scope, receive, send_with_traceparent)


def setup_context_middleware(app: FastAPI) -> None:
    """便捷注册函数：向 FastAPI 应用添加 ContextMiddleware。

    Args:
        app: FastAPI 应用实例。

    Returns:
        None
    """
    app.add_middleware(ContextMiddleware)
