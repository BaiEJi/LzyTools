"""
日志配置模块。

定义日志系统所需的所有参数。
业务方创建 LogConfig 实例后传给 setup()，不自行读取 .env。
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class LogConfig:
    """
    日志配置。

    Attributes:
        level: 最低日志级别
        sink: 输出目标列表。每项可以是 "sys.stderr"、"sys.stdout" 或文件路径
        rotation: 日志文件轮转策略，如 "500 MB", "00:00"，仅文件 sink 有效
        retention: 日志文件保留策略，如 "10 days"，仅文件 sink 有效
        enqueue: 是否启用线程安全写入（通过后台线程排队）
        json_output: 是否输出 JSON 格式（便于日志系统采集）
        backtrace: 异常时是否打印完整调用栈
        diagnose: 异常时是否显示变量值
    """

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    sink: list[str] = field(default_factory=lambda: ["sys.stderr"])
    rotation: str | None = None
    retention: str | None = None
    enqueue: bool = True
    json_output: bool = False
    backtrace: bool = True
    diagnose: bool = False
