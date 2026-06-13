"""存储模块配置。

定义 StorageConfig，承载存储后端的配置参数。
v1 仅支持 local 后端，MinIO 相关字段以注释形式预留。
"""

from pydantic import BaseModel


class StorageConfig(BaseModel):
    """存储模块配置。

    业务方创建 StorageConfig 实例后传给 Storage，不自行读取 .env。

    Attributes:
        backend: 后端类型，v1 只有 "local"。
        base_dir: 本地存储根目录。
        url_prefix: URL 前缀，用于 url() 拼接公开访问地址。
        auto_create_dir: init() 时是否自动创建目录。

    MinIO 预留字段（v1 未实现）::

        endpoint: str = "localhost:9000"
        access_key: str = ""
        secret_key: str = ""
        bucket: str = ""
        secure: bool = False
    """

    backend: str = "local"
    base_dir: str = "./uploads"
    url_prefix: str = ""
    auto_create_dir: bool = True
