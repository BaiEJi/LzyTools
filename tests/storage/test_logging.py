"""Storage 门面操作日志测试。

验证 put/get/delete/exists/list 以及 LocalBackend.init() 通过 loguru 记录日志。
"""

from io import StringIO

from loguru import logger


def _attach_sink(buf: StringIO, level: str = "DEBUG") -> int:
    """移除所有 loguru sink，挂载一个写入 buf 的 DEBUG 级别 sink。

    Args:
        buf: 用于收集日志的 StringIO。
        level: sink 级别，默认 DEBUG（覆盖 storage 模块的所有日志级别）。

    Returns:
        新 sink 的 handler id（用于后续移除）。
    """
    logger.remove()
    return logger.add(buf, level=level, enqueue=False, format="{message}")


class TestStorageFacadeLogging:
    """Storage 门面方法的日志测试。"""

    async def test_put_logs_info(self, initialized_storage):
        """put() 记录 INFO 日志，含 key、size、content_type。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("hello.txt", b"hello world")

        out = buf.getvalue()
        assert "storage put" in out
        assert "key=hello.txt" in out
        assert "size=11" in out
        assert "content_type=None" in out

    async def test_put_logs_content_type_value(self, initialized_storage):
        """put() 携带 content_type 时日志中应体现该值。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("img.png", b"\x89PNG", content_type="image/png")

        out = buf.getvalue()
        assert "content_type=image/png" in out

    async def test_get_logs_debug(self, initialized_storage):
        """get() 记录 DEBUG 日志，含 key。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("read.txt", b"data")
        await initialized_storage.get("read.txt")

        out = buf.getvalue()
        assert "storage get" in out
        assert "key=read.txt" in out

    async def test_delete_logs_info(self, initialized_storage):
        """delete() 记录 INFO 日志，含 key。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("bye.txt", b"data")
        await initialized_storage.delete("bye.txt")

        out = buf.getvalue()
        assert "storage delete" in out
        assert "key=bye.txt" in out

    async def test_exists_logs_debug_with_result(self, initialized_storage):
        """exists() 记录 DEBUG 日志，含 key 和 exists 布尔值。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("present.txt", b"x")
        await initialized_storage.exists("present.txt")
        await initialized_storage.exists("absent.txt")

        out = buf.getvalue()
        assert "storage exists" in out
        assert "key=present.txt" in out
        assert "exists=True" in out
        assert "key=absent.txt" in out
        assert "exists=False" in out

    async def test_list_logs_info_with_count(self, initialized_storage):
        """list() 记录 INFO 日志，含 prefix 和 count。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("photos/a.jpg", b"a")
        await initialized_storage.put("photos/b.jpg", b"b")
        await initialized_storage.list("photos/")

        out = buf.getvalue()
        assert "storage list" in out
        assert "prefix=photos/" in out
        assert "count=2" in out

    async def test_list_empty_prefix(self, initialized_storage):
        """list() 空前缀日志中 prefix 为空字符串。"""
        buf = StringIO()
        _attach_sink(buf)

        await initialized_storage.put("a.txt", b"a")
        await initialized_storage.list("")

        out = buf.getvalue()
        assert "prefix=" in out
        assert "count=1" in out


class TestLocalBackendInitLogging:
    """LocalBackend.init() 日志测试。"""

    async def test_init_logs_base_dir(self, storage):
        """init() 记录 INFO 日志，含 base_dir。"""
        buf = StringIO()
        _attach_sink(buf)

        await storage.init()
        try:
            out = buf.getvalue()
            assert "LocalBackend 初始化" in out
            assert f"base_dir={storage._config.base_dir}" in out
        finally:
            await storage.close()
