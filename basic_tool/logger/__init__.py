"""
basic_tool.logger 包的初始化模块。

统一导出日志相关组件:
    from basic_tool.logger import setup, get, LogConfig
"""

from basic_tool.logger.config import LogConfig
from basic_tool.logger.logger import get, setup

__all__ = [
    "LogConfig",
    "setup",
    "get",
]
