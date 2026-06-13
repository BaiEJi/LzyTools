"""请求日志中间件和全局异常处理器（已迁移到 basic_tool.errors）。

AppError 和 setup_error_handlers 已迁移至 basic_tool.errors 模块。
此文件保留向后兼容的导入入口和 RequestLoggingMiddleware。
"""

import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from basic_tool.context.ctx import ctx
from basic_tool.errors import AppError, setup_error_handlers as _setup_error_handlers


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。

    记录每个请求的 method、path、status_code、耗时。
    从请求上下文中读取 trace_id（由 ContextMiddleware 注入），
    使用 loguru 结构化日志。当未注册 ContextMiddleware 时 trace_id 为空字符串。
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """处理请求，记录日志。

        Args:
            request: 请求对象。
            call_next: 下游中间件/路由处理函数。

        Returns:
            响应对象。
        """
        trace_id = ctx.get("trace_id", "")
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "请求完成 | method={} path={} status={} elapsed={:.1f}ms trace_id={}",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            trace_id,
        )

        return response


def setup_error_handlers(app: FastAPI) -> None:
    """注册全局异常处理器（已弃用，委托至 basic_tool.errors）。

    .. deprecated::
        请直接使用 ``from basic_tool.errors import setup_error_handlers``。

    Args:
        app: FastAPI 应用实例。
    """
    _setup_error_handlers(app)
