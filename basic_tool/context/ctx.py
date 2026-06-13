"""
请求上下文管理模块。

基于 ContextVar 实现请求级隔离的上下文管理，支持同步/异步 with 语法、
安全嵌套（内层继承外层键、退出后恢复）以及 asyncio.Task 自动继承。

核心组件:
- _context_data: ContextVar[dict]，所有上下文数据的唯一存储
- ContextManager: 上下文读写单例（get/set/getall/dump/clear）
- ctx: 模块级 ContextManager 单例
- request_context(): 请求上下文工厂函数，自动生成 trace_id（W3C 128-bit）
- _RequestContext: 支持 sync/async with 的上下文管理器

使用方式:
    from basic_tool.context.ctx import ctx, request_context

    with request_context(user_id=42):
        ctx.set("action", "login")
        assert ctx.get("user_id") == 42

    # 嵌套：内层继承并覆盖外层
    with request_context(user_id=1):
        with request_context(user_id=2):
            assert ctx.get("user_id") == 2  # 内层覆盖
        assert ctx.get("user_id") == 1  # 退出后恢复

    # 异步
    async with request_context(trace_id="abc"):
        assert ctx.get("trace_id") == "abc"
"""

from contextvars import ContextVar
from typing import Any

from basic_tool.id_generator import TraceGenerator

_context_data: ContextVar[dict[str, Any]] = ContextVar("_context_data", default={})

_trace_gen = TraceGenerator()


class ContextManager:
    """请求上下文管理器。通过 ContextVar 实现请求级隔离。"""

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取上下文中的单个值。

        Args:
            key: 上下文键名
            default: 键不存在时的默认返回值，默认为 None

        Returns:
            Any: 键对应的值，不存在时返回 default
        """
        return _context_data.get().get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        动态设置上下文键值。原地修改当前上下文字典。

        Args:
            key: 上下文键名
            value: 要设置的值

        Returns:
            None
        """
        current = _context_data.get()
        current[key] = value

    def getall(self) -> dict[str, Any]:
        """
        返回完整上下文的副本。

        无活跃上下文时返回空字典。

        Returns:
            dict[str, Any]: 当前上下文字典的浅拷贝
        """
        return _context_data.get().copy()

    def dump(self) -> str:
        """
        返回上下文的人类可读字符串表示。

        格式为 "key=value, key=value"，无活跃上下文时返回空字符串。

        Returns:
            str: 上下文键值对的字符串拼接
        """
        return ", ".join(f"{k}={v}" for k, v in _context_data.get().items())

    def clear(self) -> None:
        """
        清空当前上下文字典（原地修改）。

        Returns:
            None
        """
        _context_data.get().clear()


ctx = ContextManager()


class _RequestContext:
    """请求上下文管理器，支持 sync/async with。基于 ContextVar.set/reset 实现安全嵌套。"""

    def __init__(self, data: dict[str, Any]):
        """
        初始化请求上下文。

        Args:
            data: 初始上下文数据字典
        """
        self._data = data
        self._token: Any = None

    def __enter__(self) -> "_RequestContext":
        current = _context_data.get()
        new_data = {**current, **self._data}
        self._token = _context_data.set(new_data)
        return self

    def __exit__(self, *args: Any) -> None:
        _context_data.reset(self._token)

    async def __aenter__(self) -> "_RequestContext":
        return self.__enter__()

    async def __aexit__(self, *args: Any) -> None:
        self.__exit__(*args)


def request_context(**kwargs: Any) -> _RequestContext:
    """
    创建请求上下文。未提供 trace_id 时自动生成 128-bit hex（W3C trace_id）。

    Args:
        **kwargs: 初始上下文键值对

    Returns:
        _RequestContext: 支持 sync/async with 的上下文管理器
    """
    if "trace_id" not in kwargs:
        kwargs["trace_id"] = _trace_gen.trace_id()
    return _RequestContext(kwargs)
