"""错误日志集成测试。"""

import io
from unittest.mock import MagicMock

from loguru import logger

from basic_tool.errors.app_error import AppError
from basic_tool.errors.log import log_error


class TestLogError:
    """log_error 函数测试。"""

    def test_5xx_app_error_logs_error(self):
        """5xx AppError 在 ERROR 级别记录。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="ERROR", format="{level}||{message}")
        try:
            err = AppError(code="SERVER_ERR", message="server error", http_status=500)
            log_error(err)
            output = sink.getvalue()
            assert "ERROR" in output
            assert "SERVER_ERR" in output
        finally:
            logger.remove(handler_id)

    def test_4xx_app_error_logs_warning(self):
        """4xx AppError 在 WARNING 级别记录（不出现在 ERROR sink）。"""
        error_sink = io.StringIO()
        warning_sink = io.StringIO()
        error_id = logger.add(error_sink, level="ERROR", format="{level}||{message}")
        warning_id = logger.add(warning_sink, level="WARNING", format="{level}||{message}")
        try:
            err = AppError(code="CLIENT_ERR", message="client error", http_status=400)
            log_error(err)
            # 4xx should NOT appear in ERROR sink
            assert "CLIENT_ERR" not in error_sink.getvalue()
            # 4xx SHOULD appear in WARNING sink
            assert "CLIENT_ERR" in warning_sink.getvalue()
        finally:
            logger.remove(error_id)
            logger.remove(warning_id)

    def test_non_app_error_logs_error(self):
        """非 AppError 异常在 ERROR 级别记录。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="ERROR", format="{level}||{message}")
        try:
            log_error(ValueError("oops"))
            output = sink.getvalue()
            assert "ERROR" in output
            assert "ValueError" in output or "oops" in output
        finally:
            logger.remove(handler_id)


class TestLogErrorCallback:
    """log_error 的 on_error 回调测试。"""

    def test_callback_invoked_with_app_error_code_and_status(self):
        """AppError 触发回调时传入 (.code, .http_status)。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="DEBUG", format="{message}")
        try:
            cb = MagicMock()
            err = AppError(code="TEST", message="msg", http_status=400)
            log_error(err, on_error=cb)
            cb.assert_called_once_with("TEST", 400)
        finally:
            logger.remove(handler_id)

    def test_callback_invoked_for_5xx_app_error(self):
        """5xx AppError 同样触发回调。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="DEBUG", format="{message}")
        try:
            cb = MagicMock()
            err = AppError(code="SERVER_ERR", message="msg", http_status=500)
            log_error(err, on_error=cb)
            cb.assert_called_once_with("SERVER_ERR", 500)
        finally:
            logger.remove(handler_id)

    def test_callback_not_required_default_none(self):
        """不传 on_error 时不报错，正常记录日志。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="WARNING", format="{message}")
        try:
            err = AppError(code="NO_CB", message="msg", http_status=400)
            log_error(err)
            assert "NO_CB" in sink.getvalue()
        finally:
            logger.remove(handler_id)

    def test_callback_exception_does_not_break_flow(self):
        """回调内部抛异常不得中断 log_error。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="WARNING", format="{message}")
        try:
            err = AppError(code="BOOM", message="msg", http_status=400)

            def bad_callback(code: str, status: int) -> None:
                raise RuntimeError("callback exploded")

            log_error(err, on_error=bad_callback)
            assert "BOOM" in sink.getvalue()
        finally:
            logger.remove(handler_id)

    def test_callback_for_non_app_error_passes_unknown_and_500(self):
        """非 AppError 异常触发回调时传入 ("UNKNOWN", 500)。"""
        sink = io.StringIO()
        handler_id = logger.add(sink, level="ERROR", format="{message}")
        try:
            cb = MagicMock()
            log_error(ValueError("x"), on_error=cb)
            cb.assert_called_once_with("UNKNOWN", 500)
        finally:
            logger.remove(handler_id)
