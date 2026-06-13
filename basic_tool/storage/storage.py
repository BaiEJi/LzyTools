"""Storage 门面类。

提供统一存储接口，内部委托给具体的 StorageBackend 实现。
业务方通过 Storage 使用存储功能，不直接接触后端。
"""

from loguru import logger

from basic_tool.storage.backend import FileInfo, StorageBackend
from basic_tool.storage.config import StorageConfig


class Storage:
    """存储门面类，委托给具体后端。

    使用方式::

        config = StorageConfig(base_dir="/data/uploads")
        storage = Storage(config)
        await storage.init()
        await storage.put("photos/cat.jpg", data, content_type="image/jpeg")
        data = await storage.get("photos/cat.jpg")
        await storage.close()
    """

    def __init__(self, config: StorageConfig):
        """初始化 Storage 门面。

        Args:
            config: 存储配置。
        """
        self._config = config
        self._backend: StorageBackend | None = None
        self._initialized = False
        self._backend = self._create_backend()

    def _create_backend(self) -> StorageBackend:
        """根据 config.backend 创建后端实例。

        Returns:
            StorageBackend 实例。

        Raises:
            ValueError: 不支持的 backend 类型。
        """
        if self._config.backend == "local":
            from basic_tool.storage.local import LocalBackend

            return LocalBackend(self._config)
        raise ValueError(f"unsupported backend: {self._config.backend}")

    async def init(self) -> None:
        """初始化后端资源。"""
        await self._backend.init()
        self._initialized = True

    async def close(self) -> None:
        """释放后端资源。"""
        await self._backend.close()
        self._initialized = False

    @property
    def backend(self) -> StorageBackend:
        """返回底层后端实例。"""
        return self._backend

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """写入文件，委托给后端。

        写入完成后通过 loguru 记录操作日志（key、大小、content_type）。

        Args:
            key: 文件键名（相对路径）。
            data: 文件内容。
            content_type: MIME 类型。
            metadata: 自定义元数据。
        """
        logger.info(
            "storage put | key={} size={} content_type={}",
            key,
            len(data),
            content_type,
        )
        await self._backend.put(key, data, content_type, metadata)

    async def get(self, key: str) -> bytes:
        """读取文件，委托给后端。

        读取前通过 loguru 记录 DEBUG 日志（key）。

        Args:
            key: 文件键名。

        Returns:
            完整文件内容 bytes。
        """
        logger.debug("storage get | key={}", key)
        return await self._backend.get(key)

    async def delete(self, key: str) -> None:
        """删除文件，委托给后端。

        删除前通过 loguru 记录操作日志（key）。

        Args:
            key: 文件键名。
        """
        logger.info("storage delete | key={}", key)
        await self._backend.delete(key)

    async def exists(self, key: str) -> bool:
        """检查文件存在，委托给后端。

        检查后通过 loguru 记录 DEBUG 日志（key、是否存在）。

        Args:
            key: 文件键名。

        Returns:
            文件存在返回 True，否则 False。
        """
        result = await self._backend.exists(key)
        logger.debug("storage exists | key={} exists={}", key, result)
        return result

    async def info(self, key: str) -> FileInfo:
        """获取文件信息，委托给后端。

        Args:
            key: 文件键名。

        Returns:
            文件元信息。
        """
        return await self._backend.info(key)

    async def list(self, prefix: str = "") -> list[FileInfo]:
        """列出文件，委托给后端。

        列举完成后通过 loguru 记录操作日志（prefix、匹配数量）。

        Args:
            prefix: 键名前缀，空字符串列出所有文件。

        Returns:
            FileInfo 列表。
        """
        result = await self._backend.list(prefix)
        logger.info("storage list | prefix={} count={}", prefix, len(result))
        return result

    def url(self, key: str) -> str:
        """拼接访问 URL。

        如果 config.url_prefix 为空，返回 key 本身；
        否则拼接 url_prefix 和 key。

        Args:
            key: 文件键名。

        Returns:
            完整访问 URL。
        """
        prefix = self._config.url_prefix
        if not prefix:
            return key
        return f"{prefix}/{key}"
