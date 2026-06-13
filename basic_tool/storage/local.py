"""本地文件系统存储后端。

使用 aiofiles 实现异步文件 I/O，content_type 通过 .ct sidecar 文件持久化。
路径遍历防护使用 Path.is_relative_to()。
"""

import os
from pathlib import Path

import aiofiles
from loguru import logger

from basic_tool.storage.backend import FileInfo, StorageBackend
from basic_tool.storage.config import StorageConfig


class LocalBackend(StorageBackend):
    """本地文件系统存储后端。

    所有文件存储在 base_dir 下，key 作为相对路径。
    content_type 持久化在同名 .ct sidecar 文件中（如 ``a.png`` 的 sidecar 为
    ``a.png.ct``）。list() 列举时会自动跳过 .ct 文件。

    Attributes:
        _config: 存储配置实例。
        _base_dir: 解析后的绝对基准目录。
    """

    def __init__(self, config: StorageConfig):
        """初始化本地后端。

        Args:
            config: 存储配置实例，读取 base_dir 与 auto_create_dir。
        """
        self._config = config
        self._base_dir = Path(config.base_dir).resolve()

    def _resolve(self, key: str) -> Path:
        """安全解析 key 为绝对路径。

        执行两项安全检查：
        1. key 不能为空。
        2. 解析后的路径必须在 base_dir 内（防止路径遍历，含绝对路径与 ``..`` 上跳）。

        Args:
            key: 文件键名（相对路径，如 ``photos/cat.jpg``）。

        Returns:
            解析后的绝对文件路径。

        Raises:
            ValueError: key 为空或路径遍历被拦截。
        """
        if not key:
            raise ValueError("key must not be empty")

        target = (self._base_dir / key).resolve()
        if not target.is_relative_to(self._base_dir):
            raise ValueError(f"path traversal detected: {key}")
        return target

    @staticmethod
    def _ct_path(target: Path) -> Path:
        """计算主文件对应的 .ct sidecar 路径。

        在完整文件名后追加 ``.ct``（不替换原扩展名），例如 ``a.png`` -> ``a.png.ct``。

        Args:
            target: 主文件绝对路径。

        Returns:
            对应的 .ct sidecar 路径。
        """
        return target.with_suffix(target.suffix + ".ct")

    async def _read_ct(self, target: Path) -> str | None:
        """读取 .ct sidecar 文件的 content_type。

        Args:
            target: 主文件绝对路径。

        Returns:
            content_type 字符串，或 None（无 sidecar 文件）。
        """
        ct_path = self._ct_path(target)
        if not ct_path.exists():
            return None
        async with aiofiles.open(ct_path, "r") as f:
            return await f.read()

    async def init(self) -> None:
        """初始化后端：按配置创建或校验 base_dir。

        初始化时通过 loguru 记录 INFO 日志（base_dir）。

        auto_create_dir=True 时创建目录（含父目录，exist_ok）；
        auto_create_dir=False 且目录不存在时抛出 FileNotFoundError。

        Raises:
            FileNotFoundError: auto_create_dir=False 且 base_dir 不存在。
        """
        logger.info("LocalBackend 初始化 | base_dir={}", self._config.base_dir)
        if self._config.auto_create_dir:
            self._base_dir.mkdir(parents=True, exist_ok=True)
        elif not self._base_dir.exists():
            raise FileNotFoundError(f"base_dir does not exist: {self._base_dir}")

    async def close(self) -> None:
        """释放后端资源（本地后端无资源需释放，no-op）。"""
        pass

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """写入文件，content_type 存储到 .ct sidecar。

        静默覆盖已存在的同名文件。覆盖时不带 content_type 会移除旧的 .ct sidecar，
        避免残留错误类型。metadata 参数在 v1 中被忽略（no-op）。

        Args:
            key: 文件键名（相对路径）。
            data: 文件内容（完整 bytes）。
            content_type: MIME 类型，可为 None。
            metadata: 自定义元数据（v1 不支持持久化）。

        Raises:
            ValueError: key 为空或包含路径遍历。
        """
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(target, "wb") as f:
            await f.write(data)

        ct_path = self._ct_path(target)
        if content_type is not None:
            async with aiofiles.open(ct_path, "w") as f:
                await f.write(content_type)
        else:
            # 覆盖写入且未提供 content_type：移除可能残留的旧 .ct sidecar
            ct_path.unlink(missing_ok=True)

    async def get(self, key: str) -> bytes:
        """读取文件内容。

        Args:
            key: 文件键名。

        Returns:
            完整文件内容 bytes。

        Raises:
            ValueError: key 为空或包含路径遍历。
            FileNotFoundError: 文件不存在。
        """
        target = self._resolve(key)
        if not target.exists():
            raise FileNotFoundError(f"file not found: {key}")
        async with aiofiles.open(target, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> None:
        """删除文件和对应的 .ct sidecar。

        Args:
            key: 文件键名。

        Raises:
            ValueError: key 为空或包含路径遍历。
            FileNotFoundError: 文件不存在。
        """
        target = self._resolve(key)
        if not target.exists():
            raise FileNotFoundError(f"file not found: {key}")
        target.unlink()
        self._ct_path(target).unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        """检查文件是否存在。

        Args:
            key: 文件键名。

        Returns:
            文件存在返回 True，否则 False。
        """
        target = self._resolve(key)
        return target.exists()

    async def info(self, key: str) -> FileInfo:
        """获取文件元信息。

        content_type 从 .ct sidecar 读取。metadata 在 v1 中恒为 None。

        Args:
            key: 文件键名。

        Returns:
            文件元信息。

        Raises:
            ValueError: key 为空或包含路径遍历。
            FileNotFoundError: 文件不存在。
        """
        target = self._resolve(key)
        if not target.exists():
            raise FileNotFoundError(f"file not found: {key}")

        stat = target.stat()
        content_type = await self._read_ct(target)
        return FileInfo(
            key=key,
            size=stat.st_size,
            content_type=content_type,
            last_modified=stat.st_mtime,
            metadata=None,
        )

    async def list(self, prefix: str = "") -> list[FileInfo]:
        """列出指定前缀下的文件。

        递归列举 base_dir/prefix 下的所有文件，自动跳过 .ct sidecar 文件。
        content_type 从各自的 .ct sidecar 读取。键名中的路径分隔符统一为 ``/``。

        Args:
            prefix: 键名前缀，空字符串列出 base_dir 下所有文件。前缀对应的目录
                不存在时返回空列表。

        Returns:
            FileInfo 列表（按路径排序）。
        """
        prefix_path = self._base_dir / prefix if prefix else self._base_dir
        if not prefix_path.exists():
            return []

        results = []
        for path in sorted(prefix_path.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".ct":
                continue  # 跳过内部 sidecar 文件

            rel_key = str(path.relative_to(self._base_dir)).replace(os.sep, "/")
            stat = path.stat()
            content_type = await self._read_ct(path)
            results.append(
                FileInfo(
                    key=rel_key,
                    size=stat.st_size,
                    content_type=content_type,
                    last_modified=stat.st_mtime,
                    metadata=None,
                )
            )

        return results
