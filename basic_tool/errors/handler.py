"""FastAPI 全局异常处理器。

注册 AppError、RequestValidationError、Exception 三种异常处理器，
返回标准化 JSON 响应并记录结构化日志。
"""

from typing import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from basic_tool.context.ctx import ctx
from basic_tool.errors.app_error import AppError
from basic_tool.errors.config import ErrorConfig
from basic_tool.errors.log import log_error


def _trace_id_from_scope(scope: Mapping[str, object]) -> str:
    """从 ASGI scope 中提取 trace_id。

    当异常处理器运行在 ContextMiddleware 之外（如 ServerErrorMiddleware）时，
    ContextVar 不可用，此时从 scope 中存储的 traceparent 字符串解析 trace_id。

    Args:
        scope: ASGI scope 字典。

    Returns:
        trace_id 字符串，解析失败时返回空字符串。
    """
    traceparent = scope.get("basic_tool.traceparent", "")
    if not traceparent or not isinstance(traceparent, str):
        return ""
    parts = traceparent.split("-")
    if len(parts) == 4:
        return parts[1]
    return ""


def setup_error_handlers(app: FastAPI, config: ErrorConfig | None = None) -> None:
    """注册全局异常处理器。

    处理以下异常类型：
    - AppError: 返回对应 http_status 和标准化 JSON（code + message）。
    - RequestValidationError: 返回 422 和字段错误详情。
    - Exception: 返回 500 和通用错误信息（不暴露内部细节）。

    Args:
        app: FastAPI 应用实例。
        config: 错误配置，默认 ErrorConfig()。
    """
    if config is None:
        config = ErrorConfig()

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """处理 AppError 业务异常。"""
        log_error(
            exc,
            config=config,
            request_method=request.method,
            request_path=request.url.path,
            trace_id=ctx.get("trace_id", ""),
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(include_context=config.include_context),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求验证异常，转换为 PARAM_INVALID 格式。"""
        from basic_tool.errors.codes import CommonErrors

        errors = exc.errors()
        app_err = CommonErrors.PARAM_INVALID(param="request body")
        app_err.context["validation_errors"] = errors
        log_error(
            app_err,
            config=config,
            request_method=request.method,
            request_path=request.url.path,
            trace_id=ctx.get("trace_id", ""),
        )
        return JSONResponse(
            status_code=422,
            content={
                "code": "PARAM_INVALID",
                "message": "Validation error",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获异常，返回 500。"""
        from basic_tool.errors.codes import CommonErrors

        app_err = CommonErrors.INTERNAL_ERROR()
        log_error(
            exc,
            config=config,
            request_method=request.method,
            request_path=request.url.path,
            trace_id=_trace_id_from_scope(request.scope),
        )
        response = JSONResponse(
            status_code=500,
            content=app_err.to_dict(include_context=config.include_context),
        )
        traceparent = request.scope.get("basic_tool.traceparent")
        if traceparent:
            response.headers["traceparent"] = traceparent
        return response
