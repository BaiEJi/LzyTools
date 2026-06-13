"""Storage facade 测试。

覆盖 init 生命周期、put/get、delete、exists、info、list、url、安全检查。
TDD RED 阶段：实现尚未编写，全部测试应失败。
"""

import pytest


class TestInit:
    """Storage 初始化生命周期测试。"""

    async def test_init_creates_dir(self, storage_config):
        """auto_create_dir=True 时，init() 自动创建不存在的目录。"""
        import os

        nonexistent = os.path.join(storage_config.base_dir, "subdir")
        storage_config.base_dir = nonexistent

        from basic_tool.storage.storage import Storage
        storage = Storage(storage_config)

        await storage.init()
        assert os.path.isdir(nonexistent)
        await storage.close()

    async def test_init_missing_dir_raises(self, storage_config):
        """auto_create_dir=False 且目录不存在时，init() 抛出 FileNotFoundError。"""
        import os

        nonexistent = os.path.join(storage_config.base_dir, "missing")
        storage_config.base_dir = nonexistent
        storage_config.auto_create_dir = False

        from basic_tool.storage.storage import Storage
        storage = Storage(storage_config)

        with pytest.raises(FileNotFoundError):
            await storage.init()


class TestPutGet:
    """put / get 读写操作测试。"""

    async def test_put_and_get(self, initialized_storage):
        """写入后读取，内容应一致。"""
        await initialized_storage.put("hello.txt", b"hello world")
        data = await initialized_storage.get("hello.txt")
        assert data == b"hello world"

    async def test_put_with_content_type(self, initialized_storage):
        """put 时指定 content_type，info() 应能正确读回。"""
        await initialized_storage.put("img.png", b"\x89PNG", content_type="image/png")
        info = await initialized_storage.info("img.png")
        assert info.content_type == "image/png"

    async def test_put_overwrite(self, initialized_storage):
        """覆盖写入同名文件，内容应更新为新值。"""
        await initialized_storage.put("overwrite.txt", b"old")
        await initialized_storage.put("overwrite.txt", b"new content")
        data = await initialized_storage.get("overwrite.txt")
        assert data == b"new content"

    async def test_put_empty_data(self, initialized_storage):
        """写入空 bytes，应创建 0 字节文件。"""
        await initialized_storage.put("empty.dat", b"")
        data = await initialized_storage.get("empty.dat")
        assert data == b""
        info = await initialized_storage.info("empty.dat")
        assert info.size == 0

    async def test_get_after_delete_raises(self, initialized_storage):
        """删除后再次 get，应抛出 FileNotFoundError。"""
        await initialized_storage.put("temp.txt", b"data")
        await initialized_storage.delete("temp.txt")
        with pytest.raises(FileNotFoundError):
            await initialized_storage.get("temp.txt")


class TestDelete:
    """delete 删除操作测试。"""

    async def test_delete(self, initialized_storage):
        """删除文件后，exists() 返回 False。"""
        await initialized_storage.put("del.txt", b"delete me")
        await initialized_storage.delete("del.txt")
        assert await initialized_storage.exists("del.txt") is False

    async def test_delete_not_found(self, initialized_storage):
        """删除不存在的文件应抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            await initialized_storage.delete("nope.txt")

    async def test_delete_removes_ct_file(self, initialized_storage):
        """删除文件时同时清理 .ct sidecar，重新写入不保留旧 content_type。"""
        await initialized_storage.put("sidecar.txt", b"data", content_type="text/plain")
        await initialized_storage.delete("sidecar.txt")
        # 重新写入不带 content_type，应为 None（证明 .ct 已被清理）
        await initialized_storage.put("sidecar.txt", b"new data")
        info = await initialized_storage.info("sidecar.txt")
        assert info.content_type is None


class TestExists:
    """exists 存在性检查测试。"""

    async def test_exists(self, initialized_storage):
        """exists() 对存在的文件返回 True，不存在的返回 False。"""
        await initialized_storage.put("exists.txt", b"hi")
        assert await initialized_storage.exists("exists.txt") is True
        assert await initialized_storage.exists("missing.txt") is False


class TestInfo:
    """info 元信息查询测试。"""

    async def test_info(self, initialized_storage):
        """info() 返回正确的 key、size、content_type、last_modified。"""
        await initialized_storage.put("info.txt", b"12345", content_type="text/plain")
        info = await initialized_storage.info("info.txt")
        assert info.key == "info.txt"
        assert info.size == 5
        assert info.content_type == "text/plain"
        assert info.last_modified > 0


class TestList:
    """list 列举操作测试。"""

    async def test_list(self, initialized_storage):
        """list() 按前缀列出匹配的文件。"""
        await initialized_storage.put("photos/a.jpg", b"a")
        await initialized_storage.put("photos/b.jpg", b"b")
        await initialized_storage.put("docs/readme.md", b"r")
        result = await initialized_storage.list("photos/")
        keys = [fi.key for fi in result]
        assert set(keys) == {"photos/a.jpg", "photos/b.jpg"}

    async def test_list_empty_prefix(self, initialized_storage):
        """空前缀列出所有文件。"""
        await initialized_storage.put("a.txt", b"a")
        await initialized_storage.put("b/c.txt", b"c")
        result = await initialized_storage.list("")
        keys = [fi.key for fi in result]
        assert set(keys) == {"a.txt", "b/c.txt"}

    async def test_list_nonexistent_prefix(self, initialized_storage):
        """不存在的前缀返回空列表。"""
        await initialized_storage.put("a.txt", b"a")
        result = await initialized_storage.list("nonexistent/")
        assert result == []

    async def test_list_with_ct_sidecar(self, initialized_storage):
        """list() 返回的 FileInfo 包含正确的 content_type（来自 .ct sidecar）。"""
        await initialized_storage.put("img/photo.png", b"pngdata", content_type="image/png")
        await initialized_storage.put("img/no_ct.txt", b"text")
        result = await initialized_storage.list("img/")
        ct_map = {fi.key: fi.content_type for fi in result}
        assert ct_map["img/photo.png"] == "image/png"
        assert ct_map["img/no_ct.txt"] is None


class TestUrl:
    """url 公开地址拼接测试。"""

    async def test_url(self, initialized_storage):
        """url() 正确拼接 url_prefix 和 key。"""
        result = initialized_storage.url("photos/cat.jpg")
        assert result == "http://cdn.example.com/photos/cat.jpg"

    async def test_url_no_prefix(self, storage_config):
        """url_prefix 为空时，url() 返回 key 本身。"""
        storage_config.url_prefix = ""
        from basic_tool.storage.storage import Storage
        storage = Storage(storage_config)
        assert storage.url("plain/key.txt") == "plain/key.txt"


class TestSecurity:
    """路径遍历安全检查测试。"""

    async def test_path_traversal(self, initialized_storage):
        """key 含 ../ 路径遍历应抛出 ValueError。"""
        with pytest.raises(ValueError):
            await initialized_storage.put("../../etc/passwd", b"hacked")

    async def test_key_with_leading_slash(self, initialized_storage):
        """以 / 开头的绝对路径 key 应被路径遍历检查拦截。"""
        with pytest.raises(ValueError):
            await initialized_storage.put("/etc/passwd", b"hacked")
