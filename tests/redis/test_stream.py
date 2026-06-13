"""
Stream 操作测试。
"""

import re


class TestStream:
    """Stream 操作测试。"""

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
