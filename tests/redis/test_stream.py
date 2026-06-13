"""
Stream 操作测试。
"""

import re

import pytest


class TestStreamAdd:
    """xadd 测试。"""

    async def test_xadd_basic(self, cache):
        entry_id = await cache.xadd(
            "test_stream", {"field1": "value1", "field2": "value2"}
        )
        assert re.match(r"\d+-\d+", entry_id) is not None

    async def test_xadd_returns_valid_id(self, cache):
        entry_id = await cache.xadd("test_stream", {"f": "v"})
        assert isinstance(entry_id, str)
        assert len(entry_id) > 0
        assert "-" in entry_id

    async def test_xadd_data_stored(self, cache):
        entry_id = await cache.xadd(
            "test_stream", {"field1": "value1", "field2": "value2"}
        )
        entries = await cache.client.xrange("test_stream")
        assert len(entries) == 1
        stored_id, stored_fields = entries[0]
        assert stored_id == entry_id
        assert stored_fields == {"field1": "value1", "field2": "value2"}

    async def test_xadd_custom_id(self, cache):
        entry_id = await cache.xadd("test_stream", {"f": "v"}, id="1-0")
        assert entry_id == "1-0"

    async def test_xadd_maxlen(self, cache):
        for i in range(5):
            await cache.xadd("test_stream", {"i": str(i)}, maxlen=3)
        length = await cache.xlen("test_stream")
        assert length <= 3


class TestStreamRead:
    """xrange / xrevrange / xread 测试。"""

    async def test_xrange_all(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xadd("s", {"k": "v2"})
        await cache.xadd("s", {"k": "v3"})
        entries = await cache.xrange("s")
        assert len(entries) == 3
        assert entries[0][1]["k"] == "v1"
        assert entries[2][1]["k"] == "v3"

    async def test_xrange_with_count(self, cache):
        for i in range(5):
            await cache.xadd("s", {"i": str(i)})
        entries = await cache.xrange("s", count=2)
        assert len(entries) == 2

    async def test_xrange_with_range(self, cache):
        id1 = await cache.xadd("s", {"i": "1"})
        id2 = await cache.xadd("s", {"i": "2"})
        id3 = await cache.xadd("s", {"i": "3"})
        entries = await cache.xrange("s", min=id1, max=id2)
        assert len(entries) == 2

    async def test_xrevrange(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xadd("s", {"k": "v2"})
        await cache.xadd("s", {"k": "v3"})
        entries = await cache.xrevrange("s")
        assert len(entries) == 3
        assert entries[0][1]["k"] == "v3"
        assert entries[2][1]["k"] == "v1"

    async def test_xread_basic(self, cache):
        id1 = await cache.xadd("s", {"k": "v1"})
        result = await cache.xread(streams={"s": "0-0"})
        assert result is not None
        assert len(result) == 1
        stream_name, entries = result[0]
        assert stream_name == "s"
        assert len(entries) == 1

    async def test_xread_no_new(self, cache):
        await cache.xadd("s", {"k": "v1"})
        result = await cache.xread(streams={"s": "$"}, count=1)
        assert result is None or len(result) == 0


class TestStreamManage:
    """xlen / xtrim / xdel / xinfo_stream 测试。"""

    async def test_xlen(self, cache):
        assert await cache.xlen("s") == 0
        await cache.xadd("s", {"k": "v"})
        assert await cache.xlen("s") == 1
        await cache.xadd("s", {"k": "v"})
        assert await cache.xlen("s") == 2

    async def test_xtrim(self, cache):
        for i in range(10):
            await cache.xadd("s", {"i": str(i)})
        trimmed = await cache.xtrim("s", maxlen=3)
        assert trimmed >= 7
        assert await cache.xlen("s") <= 3

    async def test_xdel(self, cache):
        id1 = await cache.xadd("s", {"k": "v1"})
        id2 = await cache.xadd("s", {"k": "v2"})
        deleted = await cache.xdel("s", id1)
        assert deleted == 1
        assert await cache.xlen("s") == 1

    async def test_xinfo_stream(self, cache):
        await cache.xadd("s", {"k": "v"})
        info = await cache.xinfo_stream("s")
        assert "length" in info
        assert info["length"] == 1


class TestStreamConsumerGroup:
    """消费者组操作测试。"""

    async def test_xgroup_create_and_destroy(self, cache):
        await cache.xadd("s", {"k": "v"})
        result = await cache.xgroup_create("s", "mygroup", id="0")
        assert result is True

        groups = await cache.xinfo_groups("s")
        assert len(groups) == 1
        assert groups[0]["name"] == "mygroup"

        destroyed = await cache.xgroup_destroy("s", "mygroup")
        assert destroyed is True

    async def test_xgroup_create_mkstream(self, cache):
        result = await cache.xgroup_create("new_stream", "g", mkstream=True)
        assert result is True
        assert await cache.xlen("new_stream") == 0
        await cache.xgroup_destroy("new_stream", "g")

    async def test_xreadgroup_basic(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xadd("s", {"k": "v2"})
        await cache.xgroup_create("s", "g", id="0")

        # 读取 1 条消息
        result = await cache.xreadgroup("g", "c1", streams={"s": ">"}, count=1)
        assert result is not None
        stream_name, entries = result[0]
        assert len(entries) == 1

        # 确认
        entry_id = entries[0][0]
        acked = await cache.xack("s", "g", entry_id)
        assert acked == 1

        await cache.xgroup_destroy("s", "g")

    async def test_xreadgroup_pending(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xgroup_create("s", "g", id="0")

        # 读取但不确认
        await cache.xreadgroup("g", "c1", streams={"s": ">"})

        # 检查 pending
        pending = await cache.xpending("s", "g")
        assert pending["pending"] == 1

        await cache.xgroup_destroy("s", "g")

    async def test_xack(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xgroup_create("s", "g", id="0")

        result = await cache.xreadgroup("g", "c1", streams={"s": ">"})
        entry_id = result[0][1][0][0]

        acked = await cache.xack("s", "g", entry_id)
        assert acked == 1

        pending = await cache.xpending("s", "g")
        assert pending["pending"] == 0

        await cache.xgroup_destroy("s", "g")

    async def test_xpending_range(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xadd("s", {"k": "v2"})
        await cache.xgroup_create("s", "g", id="0")

        await cache.xreadgroup("g", "c1", streams={"s": ">"})

        pending_list = await cache.xpending_range("s", "g", "-", "+", 10)
        assert len(pending_list) == 2

        await cache.xgroup_destroy("s", "g")

    async def test_xclaim(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xgroup_create("s", "g", id="0")

        result = await cache.xreadgroup("g", "c1", streams={"s": ">"})
        entry_id = result[0][1][0][0]

        # 认领（min_idle_time=0 用于测试）
        claimed = await cache.xclaim("s", "g", "c2", 0, entry_id)
        assert len(claimed) == 1

        await cache.xgroup_destroy("s", "g")

    async def test_xgroup_delconsumer(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xgroup_create("s", "g", id="0")
        await cache.xreadgroup("g", "c1", streams={"s": ">"})

        pending = await cache.xgroup_delconsumer("s", "g", "c1")
        assert pending == 1

        await cache.xgroup_destroy("s", "g")

    async def test_xgroup_setid(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xadd("s", {"k": "v2"})
        await cache.xgroup_create("s", "g", id="0")

        result = await cache.xgroup_setid("s", "g", id="0")
        assert result is True

        await cache.xgroup_destroy("s", "g")

    async def test_xinfo_consumers(self, cache):
        await cache.xadd("s", {"k": "v1"})
        await cache.xgroup_create("s", "g", id="0")
        await cache.xreadgroup("g", "c1", streams={"s": ">"})

        consumers = await cache.xinfo_consumers("s", "g")
        assert len(consumers) == 1
        assert consumers[0]["name"] == "c1"

        await cache.xgroup_destroy("s", "g")
