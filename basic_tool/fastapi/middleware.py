"""请求日志中间件和全局异常处理器。

提供结构化请求日志、request_id 注入、AppError 业务异常、
全局异常捕获等横切关注点。
"""

import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class AppError(Exception):
    """业务异常，自动转换为 JSON 响应。

    Attributes:
        status_code: HTTP 状态码。
        detail: 错误详情。
    """

    def __init__(self, status_code: int, detail: str) -> None:
        """初始化 AppError。

        Args:
            status_code: HTTP 状态码。
            detail: 错误详情。
        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。

    记录每个请求的 method、path、status_code、耗时。
    自动注入 X-Request-ID 到 request.state 和响应头。
    使用 loguru 结构化日志，格式与 SDK 其他模块一致。
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """处理请求，记录日志。

        Args:
            request: 请求对象。
            call_next: 下游中间件/路由处理函数。

        Returns:
            响应对象。
        """
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "请求完成 | method={} path={} status={} elapsed={:.1f}ms request_id={}",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response


def setup_error_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。

    处理以下异常类型：
    - AppError: 业务异常，返回对应 status_code 和 detail。
    - RequestValidationError: 请求验证失败，返回 422 和字段错误详情。
    - Exception: 未捕获异常，返回 500（不暴露内部信息）。

    所有错误都通过 loguru 记录。

    Args:
        app: FastAPI 应用实例。
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """处理 AppError 业务异常。"""
        logger.warning(
            "业务异常 | method={} path={} status={} detail={}",
            request.method,
            request.url.path,
            exc.status_code,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求验证异常。"""
        errors = exc.errors()
        logger.warning(
            "请求验证失败 | method={} path={} errors={}",
            request.method,
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获异常。"""
        logger.error(
            "未捕获异常 | method={} path={} type={} message={}",
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
