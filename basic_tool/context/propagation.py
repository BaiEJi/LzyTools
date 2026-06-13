"""
上下文传播模块。

提供 HTTP 头传播与任务队列序列化能力，将请求上下文跨进程/跨服务传递。

核心组件:
- _DEFAULT_HEADER_MAP: 上下文键到 HTTP 头名的默认映射
- get_propagation_headers(): 从当前上下文提取传播头
- inject_headers_to_httpx(): 合并上下文头与用户头（用户优先）
- serialize_context(): 序列化当前上下文为可传递字典
- deserialize_context(): 从序列化数据恢复上下文

使用方式:
    from basic_tool.context.propagation import (
        get_propagation_headers,
        inject_headers_to_httpx,
        serialize_context,
        deserialize_context,
    )

    # HTTP 头传播
    with request_context(request_id="req-1", user_id=42):
        headers = inject_headers_to_httpx({"Authorization": "Bearer x"})

    # 任务队列序列化
    with request_context(request_id="job-1", user_id=99):
        payload = serialize_context()
    with deserialize_context(payload):
        assert ctx.get("user_id") == 99
"""

from typing import Any

from basic_tool.context.ctx import _RequestContext, _context_data, request_context

_DEFAULT_HEADER_MAP: dict[str, str] = {
    "request_id": "X-Request-Id",
    "trace_id": "X-Trace-Id",
    "tenant_id": "X-Tenant-Id",
    "user_id": "X-User-Id",
}


def get_propagation_headers(
    header_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    从当前上下文提取传播头。

    按映射表将上下文键转换为 HTTP 头名，仅包含当前上下文中存在的键，
    值统一转为字符串。无活跃上下文时返回空字典。

    Args:
        header_map: 上下文键到 HTTP 头名的映射，为 None 时使用 _DEFAULT_HEADER_MAP

    Returns:
        dict[str, str]: 当前上下文对应的传播头字典
    """
    if header_map is None:
        header_map = _DEFAULT_HEADER_MAP
    context = _context_data.get()
    headers = {}
    for ctx_key, header_name in header_map.items():
        if ctx_key in context:
            headers[header_name] = str(context[ctx_key])
    return headers


def inject_headers_to_httpx(
    headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    合并上下文传播头与用户头。用户头优先（不被覆盖）。

    先提取当前上下文的传播头，再用用户提供的同名头覆盖，
    确保用户头优先级高于上下文传播头。

    Args:
        headers: 用户提供的请求头，为 None 时仅返回上下文传播头

    Returns:
        dict[str, str]: 合并后的请求头字典（新字典，不修改输入）
    """
    ctx_headers = get_propagation_headers()
    if headers is None:
        return ctx_headers
    return {**ctx_headers, **headers}


def serialize_context() -> dict[str, Any]:
    """
    序列化当前上下文（返回副本）。

    用于任务队列等场景，将上下文快照传递到另一进程或协程。
    无活跃上下文时返回空字典。

    Returns:
        dict[str, Any]: 当前上下文字典的浅拷贝
    """
    return _context_data.get().copy()


def deserialize_context(data: dict[str, Any]) -> _RequestContext:
    """
    从序列化数据恢复上下文。

    将 serialize_context() 产生的字典恢复为请求上下文管理器，
    支持 sync/async with 语法。退出后恢复之前的上下文状态。

    Args:
        data: serialize_context() 产生的上下文字典

    Returns:
        _RequestContext: 支持 with/async with 的上下文管理器
    """
    return request_context(**data)
