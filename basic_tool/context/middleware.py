"""FastAPI 请求上下文中间件。

为每个 HTTP 请求创建隔离的请求上下文，自动提取或生成 request_id，
提取 client_ip，并在响应头中回传 request_id，便于链路追踪。

核心组件:
- ContextMiddleware: 基于 starlette BaseHTTPMiddleware 的请求上下文中间件
- setup_context_middleware: 便捷注册函数

使用方式:
    from fastapi import FastAPI
    from basic_tool.context.middleware import setup_context_middleware

    app = FastAPI()
    setup_context_middleware(app)
"""

import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from basic_tool.context.ctx import request_context


class ContextMiddleware(BaseHTTPMiddleware):
    """FastAPI 请求上下文中间件。

    从请求头 X-Request-Id 提取请求 ID（缺失时自动生成 uuid4 hex），
    提取 client_ip（优先 X-Forwarded-For），为每个请求创建隔离的
    ContextVar 上下文，并在响应头中回传 X-Request-Id。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """处理请求，注入请求上下文。

        Args:
            request: 进入的请求对象。
            call_next: 下游中间件/路由处理函数。

        Returns:
            Response: 下游返回的响应对象，已添加 X-Request-Id 响应头。
        """
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        with request_context(request_id=request_id, client_ip=client_ip):
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response


def setup_context_middleware(app: FastAPI) -> None:
    """便捷注册函数：向 FastAPI 应用添加 ContextMiddleware。

    Args:
        app: FastAPI 应用实例。

    Returns:
        None
    """
    app.add_middleware(ContextMiddleware)
