"""FastAPI 全局异常处理器。

注册 AppError、RequestValidationError、Exception 三种异常处理器，
返回标准化 JSON 响应并记录结构化日志。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from basic_tool.errors.app_error import AppError
from basic_tool.errors.config import ErrorConfig
from basic_tool.errors.log import log_error


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
            request_id=getattr(request.state, "request_id", ""),
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
            request_id=getattr(request.state, "request_id", ""),
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
            request_id=getattr(request.state, "request_id", ""),
        )
        return JSONResponse(
            status_code=500,
            content=app_err.to_dict(include_context=config.include_context),
        )
