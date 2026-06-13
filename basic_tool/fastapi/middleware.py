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
from basic_tool.metrics.collector import MetricsCollector


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。

    记录每个请求的 method、path、status_code、耗时。
    从请求上下文中读取 trace_id（由 ContextMiddleware 注入），
    使用 loguru 结构化日志。当未注册 ContextMiddleware 时 trace_id 为空字符串。

    可选注入 ``MetricsCollector`` 以在每个请求结束时记录
    ``http_requests_total`` (counter) 和 ``http_request_duration_seconds`` (histogram)。
    当 metrics 为 None 时不执行任何采集逻辑（零开销）。
    采集过程中的任何异常都会被静默吞掉，确保不影响正常请求处理。
    """

    def __init__(
        self,
        app: Any,
        metrics: MetricsCollector | None = None,
    ) -> None:
        """初始化请求日志中间件。

        Args:
            app: ASGI 应用实例（由 ``add_middleware`` 自动注入）。
            metrics: 可选的指标采集器，传入则记录请求 counter 和耗时 histogram；
                     None 表示不采集（零开销）。采集器的生命周期由调用方负责。
        """
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """处理请求，记录日志和指标。

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

        if self._metrics is not None:
            try:
                method = request.method
                path = request.url.path
                status = response.status_code
                self._metrics.counter(
                    "http_requests_total",
                    labels={"method": method, "path": path, "status": str(status)},
                )
                self._metrics.histogram(
                    "http_request_duration_seconds",
                    elapsed_ms / 1000,
                    labels={"method": method, "path": path},
                )
            except Exception:
                pass

        return response


def setup_error_handlers(app: FastAPI) -> None:
    """注册全局异常处理器（已弃用，委托至 basic_tool.errors）。

    .. deprecated::
        请直接使用 ``from basic_tool.errors import setup_error_handlers``。

    Args:
        app: FastAPI 应用实例。
    """
    _setup_error_handlers(app)
