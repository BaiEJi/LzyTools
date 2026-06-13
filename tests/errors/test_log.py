"""错误日志集成测试。"""

import io

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
