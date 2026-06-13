"""
basic_tool.context 包的初始化模块。

统一导出上下文管理相关组件，方便外部使用:
    from basic_tool.context import ctx, request_context
    from basic_tool.context import enable_log_injection
    from basic_tool.context import get_propagation_headers, inject_headers_to_httpx
    from basic_tool.context import serialize_context, deserialize_context
    from basic_tool.context import ContextMiddleware, setup_context_middleware
"""

from basic_tool.context.ctx import ContextManager, ctx, request_context
from basic_tool.context.log_extra import enable_log_injection
from basic_tool.context.middleware import ContextMiddleware, setup_context_middleware
from basic_tool.context.propagation import (
    deserialize_context,
    get_propagation_headers,
    inject_headers_to_httpx,
    serialize_context,
)

__all__ = [
    # 核心
    "ctx",
    "ContextManager",
    "request_context",
    # 日志注入
    "enable_log_injection",
    # 透传
    "get_propagation_headers",
    "inject_headers_to_httpx",
    "serialize_context",
    "deserialize_context",
    # FastAPI
    "ContextMiddleware",
    "setup_context_middleware",
]
