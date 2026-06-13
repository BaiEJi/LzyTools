"""CommonErrors 预定义错误码测试。"""

from basic_tool.errors.codes import CommonErrors


class TestCommonErrors:
    """CommonErrors 测试。"""

    def test_all_15_entries_exist(self):
        """所有 15 个错误码条目都存在。"""
        entries = CommonErrors.entries()
        expected = [
            "PARAM_MISSING", "PARAM_INVALID", "PARAM_TYPE_ERROR",
            "TOKEN_EXPIRED", "TOKEN_INVALID", "CREDENTIALS_ERROR",
            "PERMISSION_DENIED", "ACCESS_FORBIDDEN",
            "RESOURCE_NOT_FOUND", "RESOURCE_ALREADY_EXISTS", "VERSION_CONFLICT",
            "RATE_LIMITED",
            "INTERNAL_ERROR", "SERVICE_UNAVAILABLE", "UPSTREAM_TIMEOUT",
        ]
        assert len(entries) == 15, f"Expected 15 entries, got {len(entries)}"
        for name in expected:
            assert name in entries, f"Missing: {name}"
            assert entries[name].code == name

    def test_param_missing_with_param(self):
        """PARAM_MISSING 带 param 参数正确渲染。"""
        err = CommonErrors.PARAM_MISSING(param="username")
        assert err.code == "PARAM_MISSING"
        assert "username" in err.message
        assert err.http_status == 400
        assert err.context == {"param": "username"}

    def test_token_expired_no_params(self):
        """TOKEN_EXPIRED 不带参数正确渲染。"""
        err = CommonErrors.TOKEN_EXPIRED()
        assert err.code == "TOKEN_EXPIRED"
        assert err.http_status == 401
        assert err.context == {}

    def test_resource_not_found_with_resource(self):
        """RESOURCE_NOT_FOUND 带 resource 参数正确渲染。"""
        err = CommonErrors.RESOURCE_NOT_FOUND(resource="用户")
        assert err.code == "RESOURCE_NOT_FOUND"
        assert "用户" in err.message
        assert err.http_status == 404
