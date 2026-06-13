"""
basic_tool.storage 包的初始化模块。

统一导出存储相关组件，方便外部使用:
    from basic_tool.storage import Storage, StorageConfig
    from basic_tool.storage import StorageBackend, FileInfo
"""

from basic_tool.storage.backend import FileInfo, StorageBackend
from basic_tool.storage.config import StorageConfig
from basic_tool.storage.storage import Storage

__all__ = [
    "Storage",
    "StorageConfig",
    "StorageBackend",
    "FileInfo",
]
