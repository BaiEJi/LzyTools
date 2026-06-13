"""错误日志集成。

提供 log_error() 函数，根据异常类型和 HTTP 状态码选择合适的日志级别。
"""

from typing import Any

from loguru import logger

from basic_tool.errors.config import ErrorConfig
# Delayed to allow the module to be imported early
# AppError imported inside function to avoid circular deps if needed


def log_error(
    exc: Exception,
    *,
    config: ErrorConfig | None = None,
    request_method: str = "",
    request_path: str = "",
    trace_id: str = "",
) -> None:
    """记录错误日志。

    根据异常类型选择日志级别：
    - AppError 5xx → ERROR（含堆栈）
    - AppError 4xx → WARNING
    - 非 AppError → ERROR（含堆栈）

    Args:
        exc: 异常对象。
        config: 错误配置，默认使用 ErrorConfig()。
        request_method: 请求方法（GET/POST 等），可选。
        request_path: 请求路径，可选。
        trace_id: 链路追踪 ID，可选。
    """
    from basic_tool.errors.app_error import AppError

    if config is None:
        config = ErrorConfig()

    extra: dict[str, Any] = {}
    if request_method:
        extra["request_method"] = request_method
    if request_path:
        extra["request_path"] = request_path
    if trace_id:
        extra["trace_id"] = trace_id

    bound_logger = logger.bind(**extra) if extra else logger

    if isinstance(exc, AppError):
        extra["error_code"] = exc.code
        extra["http_status"] = exc.http_status
        bound_logger = logger.bind(**extra) if extra else logger

        if exc.http_status >= 500:
            # 5xx: ERROR with stack trace
            bound_logger.error(
                "服务端异常 | error_code={} http_status={} message={}",
                exc.code,
                exc.http_status,
                exc.message,
            )
            if config.log_5xx_stack:
                bound_logger.exception("异常堆栈")
        else:
            # 4xx: WARNING
            if config.log_4xx_summary:
                bound_logger.warning(
                    "业务异常 | error_code={} http_status={} message={}",
                    exc.code,
                    exc.http_status,
                    exc.message,
                )
    else:
        # Non-AppError: ERROR with stack trace
        bound_logger.error(
            "未捕获异常 | type={} message={}",
            type(exc).__name__,
            str(exc),
        )
        bound_logger.exception("异常堆栈")
