"""错误模块配置。

提供 ErrorConfig 用于控制错误日志行为和响应内容。
"""

from pydantic import BaseModel


class ErrorConfig(BaseModel):
    """错误处理配置。

    控制错误响应是否包含上下文、日志详细程度。

    Attributes:
        include_context: 响应体是否包含 context 字段。
        log_5xx_stack: 5xx 错误是否记录完整堆栈。
        log_4xx_summary: 4xx 错误是否记录摘要（而非完整堆栈）。
    """

    include_context: bool = False
    log_5xx_stack: bool = True
    log_4xx_summary: bool = True
