"""注册表测试。"""

import pytest
from basic_tool.errors.registry import (
    ErrorEntry,
    ErrorRegistry,
    check_conflicts,
    clear_registry,
    get_all_entries,
)


class TestErrorEntry:
    """ErrorEntry 测试。"""

    def test_entry_creation_and_registration(self):
        """ErrorEntry 创建并注册到全局注册表。"""
        entry = ErrorEntry("TEST_CODE", "test message", 400)
        assert entry.code == "TEST_CODE"
        assert entry.message_template == "test message"
        assert entry.http_status == 400
        assert "TEST_CODE" in get_all_entries()

    def test_entry_call_without_kwargs(self):
        """__call__ 不带 kwargs 时 message 等于 template。"""
        entry = ErrorEntry("NO_PARAM", "static message", 400)
        err = entry()
        assert err.message == "static message"
        assert err.code == "NO_PARAM"
        assert err.context == {}

    def test_entry_call_with_kwargs(self):
        """__call__ 带 kwargs 时渲染消息模板。"""
        entry = ErrorEntry("WITH_PARAM", "Hello {name}, age {age}", 200)
        err = entry(name="Alice", age=30)
        assert err.message == "Hello Alice, age 30"
        assert err.code == "WITH_PARAM"
        assert err.http_status == 200
        assert err.context == {"name": "Alice", "age": 30}

    def test_duplicate_code_raises(self):
        """重复注册同一错误码抛出 ValueError。"""
        ErrorEntry("DUP", "first", 400)
        with pytest.raises(ValueError, match="Duplicate error code"):
            ErrorEntry("DUP", "second", 400)

    def test_entry_is_frozen(self):
        """ErrorEntry 是 frozen dataclass，不可修改。"""
        entry = ErrorEntry("FROZEN", "msg", 400)
        with pytest.raises(Exception):
            entry.code = "CHANGED"


class TestErrorRegistry:
    """ErrorRegistry 测试。"""

    def test_registry_entries(self):
        """ErrorRegistry.entries() 返回类属性中的 ErrorEntry。"""
        class TestErrors(ErrorRegistry):
            ALPHA = ErrorEntry("ALPHA", "alpha error", 400)
            BETA = ErrorEntry("BETA", "beta error", 404)

        entries = TestErrors.entries()
        assert "ALPHA" in entries
        assert "BETA" in entries
        assert entries["ALPHA"].code == "ALPHA"
        assert entries["BETA"].code == "BETA"

    def test_registry_codes(self):
        """ErrorRegistry.codes() 返回错误码属性名列表。"""
        class TestErrors(ErrorRegistry):
            GAMMA = ErrorEntry("GAMMA", "gamma", 400)
            DELTA = ErrorEntry("DELTA", "delta", 400)

        codes = TestErrors.codes()
        assert "GAMMA" in codes
        assert "DELTA" in codes


class TestRegistryFunctions:
    """注册表模块函数测试。"""

    def test_check_conflicts_no_conflict(self):
        """check_conflicts() 无冲突时不抛异常。"""
        ErrorEntry("UNIQUE_1", "msg", 400)
        check_conflicts()  # 不应抛出异常

    def test_clear_registry(self):
        """clear_registry() 清空全局注册表。"""
        ErrorEntry("TO_CLEAR", "msg", 400)
        assert "TO_CLEAR" in get_all_entries()
        clear_registry()
        assert get_all_entries() == {}

    def test_get_all_entries_returns_copy(self):
        """get_all_entries() 返回注册表副本。"""
        ErrorEntry("COPY_TEST", "msg", 400)
        entries = get_all_entries()
        entries["FAKE"] = None  # 修改副本不应影响原注册表
        assert "FAKE" not in get_all_entries()
