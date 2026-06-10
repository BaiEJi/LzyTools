"""
日志初始化与获取模块。

提供统一的日志配置入口和 logger 获取方式。

支持两种输出格式:
- logfmt: 2024-01-15T10:30:00||INFO||app.py:42||user_id=123||hello world
- json: {"time":"...","level":"INFO","file":"app.py","line":42,"message":"hello world","user_id":123}

核心组件:
- setup(): 根据 LogConfig 初始化 loguru logger
- get(): 获取已配置的 logger 实例

使用方式:
    from basic_tool.logger import setup, get, LogConfig

    setup(LogConfig(level="DEBUG"))
    log = get()
    log.info("user logged in", user_id=123, action="login")
    # logfmt: 2024-01-15T10:30:00||INFO||app.py:42||user_id=123||action=login||user logged in
    # json: {"time":"...","level":"INFO",...,"message":"user logged in","user_id":123,"action":"login"}
"""

import sys
from datetime import datetime, timezone

from loguru import logger

from basic_tool.logger.config import LogConfig

# 标记 setup() 是否已调用
_configured = False


def _format_logfmt(record: dict) -> str:
    """
    logfmt 格式化函数。

    格式: timestamp||level||file:line||k1=v1||k2=v2||message

    - 时间戳使用 ISO 8601 格式（UTC）
    - extra 中的键值对以 k=v 形式插入
    - 用 || 分隔各段

    Args:
        record: loguru 内部的日志记录字典

    Returns:
        str: loguru 格式字符串
    """
    timestamp = record["time"].strftime("%Y-%m-%dT%H:%M:%S")
    parts = [
        timestamp,
        record["level"].name,
        f'{record["file"].name}:{record["line"]}',
    ]
    for k, v in record["extra"].items():
        if k != "_fmt_output":
            parts.append(f"{k}={v}")
    parts.append(record["message"])
    record["extra"]["_fmt_output"] = "||".join(parts)
    return "{extra[_fmt_output]}\n"


def _format_json(record: dict) -> str:
    """
    JSON 格式化函数。

    输出单行 JSON，便于 ELK/Datadog/Loki 等日志系统采集。

    Args:
        record: loguru 内部的日志记录字典

    Returns:
        str: loguru 格式字符串
    """
    import orjson

    data = {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "file": record["file"].name,
        "line": record["line"],
        "function": record["function"],
        "message": record["message"],
    }
    for k, v in record["extra"].items():
        if k != "_fmt_output":
            data[k] = v
    record["extra"]["_fmt_output"] = orjson.dumps(data).decode("utf-8")
    return "{extra[_fmt_output]}\n"


def setup(config: LogConfig | None = None) -> None:
    """
    初始化日志系统。

    移除 loguru 默认 sink，按 LogConfig 重新配置。
    可重复调用，每次调用会清除之前的 sink 配置。

    Args:
        config: 日志配置，为 None 时使用默认配置

    Example:
        setup(LogConfig(level="DEBUG"))
        setup(LogConfig(sink=["sys.stderr", "/var/log/app.log"], rotation="500 MB"))
        setup(LogConfig(json_output=True))  # JSON 格式，便于日志系统采集
    """
    global _configured

    if config is None:
        config = LogConfig()

    logger.remove()

    formatter = _format_json if config.json_output else _format_logfmt

    for sink_path in config.sink:
        if sink_path in ("sys.stderr", "sys.stdout"):
            sink = sys.stderr if sink_path == "sys.stderr" else sys.stdout
        else:
            sink = sink_path

        kwargs: dict = {
            "sink": sink,
            "format": formatter,
            "level": config.level,
            "enqueue": config.enqueue,
            "backtrace": config.backtrace,
            "diagnose": config.diagnose,
        }
        if config.rotation and sink_path not in ("sys.stderr", "sys.stdout"):
            kwargs["rotation"] = config.rotation
        if config.retention and sink_path not in ("sys.stderr", "sys.stdout"):
            kwargs["retention"] = config.retention

        logger.add(**kwargs)

    _configured = True


def get():
    """
    获取已配置的 loguru Logger 实例。

    如果 setup() 尚未调用，会自动以默认配置初始化。

    Returns:
        loguru.Logger: 可直接调用 info/debug/warning/error 等方法

    Example:
        log = get()
        log.info("server started", host="0.0.0.0", port=8080)
        # logfmt: 2024-01-15T10:30:00||INFO||server.py:10||host=0.0.0.0||port=8080||server started
    """
    if not _configured:
        setup()
    return logger
