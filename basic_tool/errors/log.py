"""错误日志集成。

提供 log_error() 函数，根据异常类型和 HTTP 状态码选择合适的日志级别。

回调协议：
    log_error() 接受可选的 on_error 回调，用于将错误码和 HTTP 状态码上报给外部
    指标系统（如 metrics）。errors 模块故意不直接依赖 metrics 模块，因为这会形成
    循环依赖：errors → metrics → redis → errors（redis 中的 RateLimitError 是
    AppError 子类）。通过回调协议，errors 保持为 DAG 叶子节点，由调用方（如
    应用入口）注入 metrics 集成。
"""

from typing import Any, Callable

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
    on_error: Callable[[str, int], None] | None = None,
) -> None:
    """记录错误日志，并可选地通过回调上报错误指标。

    根据异常类型选择日志级别：
    - AppError 5xx → ERROR（含堆栈）
    - AppError 4xx → WARNING
    - 非 AppError → ERROR（含堆栈）

    日志记录完成后，若提供 on_error 回调，则以 (error_code, http_status) 调用之。
    回调失败不会中断错误处理流程（内部 try/except 静默吞掉异常）。

    Args:
        exc: 异常对象。
        config: 错误配置，默认使用 ErrorConfig()。
        request_method: 请求方法（GET/POST 等），可选。
        request_path: 请求路径，可选。
        trace_id: 链路追踪 ID，可选。
        on_error: 错误指标回调，签名为 ``on_error(error_code: str, http_status: int) -> None``。
            AppError 传入其 ``.code`` 和 ``.http_status``；非 AppError 传入
            ``("UNKNOWN", 500)``。用于在不引入循环依赖的前提下对接 metrics 系统。
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

    # 上报错误指标（回调协议，避免 errors → metrics 循环依赖）
    if on_error is not None:
        try:
            if isinstance(exc, AppError):
                on_error(exc.code, exc.http_status)
            else:
                on_error("UNKNOWN", 500)
        except Exception:
            # 回调失败不得中断错误处理流程
            pass
