"""
Log 模块测试。

测试日志格式化函数和 setup/get 功能。
"""

from io import StringIO

from loguru import logger

from basic_tool.logger import LogConfig, get, setup
from basic_tool.logger.logger import _format_logfmt, _format_json, _configured


class TestLogfmtFormatter:
    """logfmt 格式化函数测试。"""

    def test_basic_format(self):
        record = {
            "level": type("L", (), {"name": "INFO"})(),
            "file": type("F", (), {"name": "app.py"})(),
            "line": 42,
            "message": "hello world",
            "extra": {},
            "time": type("T", (), {"strftime": lambda self, fmt: "2024-01-15T10:30:00"})(),
        }
        fmt_str = _format_logfmt(record)
        assert record["extra"]["_fmt_output"] == "2024-01-15T10:30:00||INFO||app.py:42||hello world"
        assert fmt_str == "{extra[_fmt_output]}\n"

    def test_format_with_extra(self):
        record = {
            "level": type("L", (), {"name": "WARNING"})(),
            "file": type("F", (), {"name": "server.py"})(),
            "line": 10,
            "message": "request timeout",
            "extra": {"user_id": 123, "action": "query"},
            "time": type("T", (), {"strftime": lambda self, fmt: "2024-01-15T10:30:00"})(),
        }
        _format_logfmt(record)
        assert (
            record["extra"]["_fmt_output"]
            == "2024-01-15T10:30:00||WARNING||server.py:10||user_id=123||action=query||request timeout"
        )

    def test_format_no_extra(self):
        record = {
            "level": type("L", (), {"name": "ERROR"})(),
            "file": type("F", (), {"name": "db.py"})(),
            "line": 99,
            "message": "connection lost",
            "extra": {},
            "time": type("T", (), {"strftime": lambda self, fmt: "2024-01-15T10:30:00"})(),
        }
        _format_logfmt(record)
        assert record["extra"]["_fmt_output"] == "2024-01-15T10:30:00||ERROR||db.py:99||connection lost"

    def test_fmt_output_excluded_from_kv(self):
        record = {
            "level": type("L", (), {"name": "INFO"})(),
            "file": type("F", (), {"name": "t.py"})(),
            "line": 1,
            "message": "test",
            "extra": {"_fmt_output": "old_value", "key": "val"},
            "time": type("T", (), {"strftime": lambda self, fmt: "2024-01-15T10:30:00"})(),
        }
        _format_logfmt(record)
        assert "old_value" not in record["extra"]["_fmt_output"]
        assert "key=val" in record["extra"]["_fmt_output"]

    def test_format_includes_timestamp(self):
        """时间戳必须出现在输出中。"""
        record = {
            "level": type("L", (), {"name": "INFO"})(),
            "file": type("F", (), {"name": "app.py"})(),
            "line": 1,
            "message": "test",
            "extra": {},
            "time": type("T", (), {"strftime": lambda self, fmt: "2024-01-15T10:30:00"})(),
        }
        _format_logfmt(record)
        assert "2024-01-15T10:30:00" in record["extra"]["_fmt_output"]


class TestJsonFormatter:
    """JSON 格式化函数测试。"""

    def test_json_format(self):
        import orjson
        from datetime import datetime, timezone

        now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        record = {
            "level": type("L", (), {"name": "INFO"})(),
            "file": type("F", (), {"name": "app.py"})(),
            "line": 42,
            "function": "main",
            "message": "hello",
            "extra": {"user_id": 123},
            "time": now,
        }
        _format_json(record)
        output = record["extra"]["_fmt_output"]
        data = orjson.loads(output)
        assert data["level"] == "INFO"
        assert data["file"] == "app.py"
        assert data["line"] == 42
        assert data["message"] == "hello"
        assert data["user_id"] == 123
        assert "time" in data


class TestSetupAndGet:
    """setup/get 集成测试。"""

    def test_setup_default(self):
        buf = StringIO()
        logger.remove()
        logger.add(buf, format=_format_logfmt, level="DEBUG", enqueue=False)
        logger.info("hello", user_id=123)
        output = buf.getvalue()
        assert "||INFO||" in output
        assert "user_id=123" in output
        assert "hello" in output
        logger.remove()

    def test_setup_with_config(self):
        buf = StringIO()
        logger.remove()
        config = LogConfig(level="DEBUG", enqueue=False, sink=["sys.stderr"])
        setup(config)
        # 直接往 buf 里写来测试
        logger.remove()
        logger.add(buf, format=_format_logfmt, level="DEBUG", enqueue=False)
        log = get()
        log.info("test message")
        output = buf.getvalue()
        assert "||INFO||" in output
        assert "test message" in output
        logger.remove()

    def test_get_returns_logger(self):
        log = get()
        assert log is logger

    def test_get_auto_setups(self):
        """get() 在 setup() 之前调用应自动初始化。"""
        import basic_tool.logger.logger as mod
        old = mod._configured
        mod._configured = False
        logger.remove()
        log = get()
        assert log is logger
        assert mod._configured is True
        mod._configured = old
        logger.remove()

    def test_setup_json_output(self):
        """JSON 输出模式。"""
        import orjson
        buf = StringIO()
        logger.remove()
        config = LogConfig(level="DEBUG", enqueue=False, json_output=True, sink=["sys.stderr"])
        setup(config)
        logger.remove()
        logger.add(buf, format=_format_json, level="DEBUG", enqueue=False)
        log = get()
        log.info("json test", key="value")
        output = buf.getvalue().strip()
        data = orjson.loads(output)
        assert data["message"] == "json test"
        assert data["key"] == "value"
        assert "time" in data
        logger.remove()

    def test_logconfig_dataclass(self):
        """LogConfig 是 dataclass，支持默认值。"""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.sink == ["sys.stderr"]
        assert config.json_output is False
        assert config.backtrace is True

    def test_logconfig_custom_sinks(self):
        """支持多个 sink。"""
        config = LogConfig(sink=["sys.stderr", "/tmp/test.log"])
        assert len(config.sink) == 2
