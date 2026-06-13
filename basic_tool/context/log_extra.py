"""
日志上下文注入模块。

通过 loguru 的 patcher 机制将当前请求上下文字段自动注入到每条日志记录的
``extra`` 中，使日志格式串可以使用 ``{extra[trace_id]}`` 等占位符，
无需在每次打日志时手动传入上下文。

核心组件:
- _inject_context: loguru patcher 函数，按记录注入上下文字段
- enable_log_injection: 启用全局注入（修复 patch() 返回新实例的陷阱）

使用方式:
    from basic_tool.context.log_extra import enable_log_injection
    from basic_tool.context.ctx import request_context
    from loguru import logger

    enable_log_injection()
    logger.add(sys.stderr, format="{extra[trace_id]}|{message}")

    with request_context(trace_id="abc"):
        logger.info("hello")  # 输出: abc|hello

注意:
    用户在打日志时显式传入的 extra 优先级高于上下文注入的值，
    即已存在的键不会被覆盖。
"""

from basic_tool.context.ctx import _context_data


def _inject_context(record: dict) -> None:
    """
    将当前上下文字段注入日志记录的 ``extra`` 中。

    作为 loguru 的 patcher 函数，在每条日志记录格式化前调用。
    仅填充 ``record["extra"]`` 中尚不存在的键，保证用户显式传入的
    extra 优先级更高。

    Args:
        record: loguru 日志记录字典，原地修改其 ``extra`` 字段。

    Returns:
        None
    """
    context = _context_data.get()
    for key, value in context.items():
        if key not in record["extra"]:
            record["extra"][key] = value


def enable_log_injection() -> None:
    """
    启用全局日志上下文注入。

    调用后，所有 loguru 日志记录（包括 ``basic_tool.logger.get()``
    返回的 logger）都会自动包含当前请求上下文中的字段。

    实现说明:
        ``loguru.logger.patch()`` 返回一个新的 Core 实例，不会修改
        原始的全局 ``loguru.logger``。本函数通过将 patched 实例的
        ``_options`` 复制回全局 logger，使 patcher 生效于所有
        loguru 引用。

    Returns:
        None
    """
    import loguru

    patched = loguru.logger.patch(_inject_context)
    loguru.logger._options = patched._options
