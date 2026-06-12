"""分布式链路追踪（W3C Trace Context）和唯一 ID 生成（Snowflake）模块。

提供分布式链路追踪上下文管理和业务唯一 ID 生成两大能力，
纯 Python 实现，零外部依赖（仅使用标准库和 pydantic）。

使用示例::

    from basic_tool.id_generator import IDConfig, IDGenerator, TraceContext, TraceGenerator

    # 链路追踪
    ctx = TraceContext.root()
    child = ctx.child_span()
    header = ctx.to_traceparent()

    # 唯一 ID 生成
    config = IDConfig(worker_id=1)
    gen = IDGenerator(config)
    order_id = gen.new_prefixed("ORD")
"""

from basic_tool.id_generator.config import IDConfig
from basic_tool.id_generator.generator import IDGenerator, TraceGenerator
from basic_tool.id_generator.trace import TraceContext

__all__ = [
    # 配置
    "IDConfig",
    # 链路追踪
    "TraceContext",
    "TraceGenerator",
    # 唯一 ID
    "IDGenerator",
]
