"""basic_tool.errors — 标准化错误码与异常处理模块。

提供统一的业务异常 AppError、错误码注册表、预定义错误码 CommonErrors、
FastAPI 全局异常处理器和 loguru 日志集成。

使用示例::

    from basic_tool.errors import AppError, CommonErrors, setup_error_handlers
    from fastapi import FastAPI

    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        if item_id < 0:
            raise CommonErrors.PARAM_INVALID(param="item_id")
        # 或直接构造
        raise AppError(code="CUSTOM", message="custom error", http_status=400)
"""

from basic_tool.errors.app_error import AppError
from basic_tool.errors.codes import CommonErrors
from basic_tool.errors.config import ErrorConfig
from basic_tool.errors.handler import setup_error_handlers
from basic_tool.errors.registry import (
    ErrorEntry,
    ErrorRegistry,
    check_conflicts,
    clear_registry,
    get_all_entries,
)

__all__ = [
    "AppError",
    "ErrorConfig",
    "ErrorRegistry",
    "ErrorEntry",
    "check_conflicts",
    "get_all_entries",
    "clear_registry",
    "CommonErrors",
    "setup_error_handlers",
]
