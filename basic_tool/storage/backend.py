"""存储后端抽象接口。

定义 FileInfo（文件元信息）与 StorageBackend（存储后端抽象基类）。
所有具体后端（如 LocalBackend）继承 StorageBackend 并实现其抽象方法。
"""

from abc import ABC, abstractmethod


class FileInfo:
    """文件元信息。

    使用 __slots__ 减少内存占用，适用于大量文件元信息的场景。

    Attributes:
        key: 文件键名（相对路径，如 "photos/cat.jpg"）。
        size: 文件大小（字节）。
        content_type: MIME 类型（如 "image/png"），可为 None。
        last_modified: 最后修改时间（Unix 时间戳，秒）。
        metadata: 自定义元数据（v1 不支持持久化，预留接口）。
    """

    __slots__ = ("key", "size", "content_type", "last_modified", "metadata")

    def __init__(
        self,
        key: str,
        size: int,
        content_type: str | None,
        last_modified: float,
        metadata: dict | None = None,
    ):
        """初始化文件信息。

        Args:
            key: 文件键名（相对路径）。
            size: 文件大小（字节）。
            content_type: MIME 类型（如 "image/png"），可为 None。
            last_modified: 最后修改时间（Unix 时间戳）。
            metadata: 自定义元数据（v1 不支持，预留）。
        """
        self.key = key
        self.size = size
        self.content_type = content_type
        self.last_modified = last_modified
        self.metadata = metadata


class StorageBackend(ABC):
    """存储后端抽象基类。

    所有具体存储后端（LocalBackend、MinioBackend 等）必须继承此类
    并实现全部抽象异步方法。调用方通过 Storage facade 间接使用后端，
    不直接持有 StorageBackend 实例。
    """

    @abstractmethod
    async def init(self) -> None:
        """初始化后端资源（创建目录、建立连接等）。

        在 Storage.init() 中调用，对应应用 lifespan startup。
        """

    @abstractmethod
    async def close(self) -> None:
        """释放后端资源。

        在 Storage.close() 中调用，对应应用 lifespan shutdown。
        """

    @abstractmethod
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """写入文件，静默覆盖已存在的同名文件。

        Args:
            key: 文件键名（相对路径，如 "photos/cat.jpg"）。
            data: 文件内容（完整 bytes）。
            content_type: MIME 类型，调用方必须提供。
            metadata: 自定义元数据（v1 不支持持久化）。

        Raises:
            ValueError: key 为空或包含路径遍历。
        """

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """读取文件内容。

        Args:
            key: 文件键名。

        Returns:
            完整文件内容 bytes。

        Raises:
            FileNotFoundError: 文件不存在。
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除文件，同时清理 .ct sidecar 文件。

        Args:
            key: 文件键名。

        Raises:
            FileNotFoundError: 文件不存在。
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在。

        Args:
            key: 文件键名。

        Returns:
            文件存在返回 True，否则 False。
        """

    @abstractmethod
    async def info(self, key: str) -> FileInfo:
        """获取文件元信息。

        content_type 从 .ct sidecar 文件读取。

        Args:
            key: 文件键名。

        Returns:
            文件元信息。

        Raises:
            FileNotFoundError: 文件不存在。
        """

    @abstractmethod
    async def list(self, prefix: str = "") -> list[FileInfo]:
        """列出指定前缀下的文件。

        Args:
            prefix: 键名前缀，空字符串列出所有文件。

        Returns:
            FileInfo 列表（content_type 从 .ct sidecar 读取）。
        """
