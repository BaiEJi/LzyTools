"""存储模块测试 fixtures。

提供三种 fixture：
- ``storage_config`` — 指向临时目录的 StorageConfig。
- ``storage`` — 未初始化的 Storage 实例（用于 init 相关测试）。
- ``initialized_storage`` — 已初始化的 Storage 实例，测试结束自动关闭。
"""

import pytest

from basic_tool.storage.config import StorageConfig


@pytest.fixture
def storage_config(tmp_path):
    """创建临时 StorageConfig，指向 tmp_path 目录。"""
    return StorageConfig(base_dir=str(tmp_path), url_prefix="http://cdn.example.com")


@pytest.fixture
def storage(storage_config):
    """创建 Storage 实例（尚未 init）。"""
    from basic_tool.storage.storage import Storage
    return Storage(storage_config)


@pytest.fixture
async def initialized_storage(storage):
    """创建并初始化的 Storage 实例，测试结束后自动关闭。"""
    await storage.init()
    yield storage
    await storage.close()
