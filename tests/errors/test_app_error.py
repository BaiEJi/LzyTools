"""AppError 异常类测试。"""

from basic_tool.errors.app_error import AppError


class TestAppError:
    """AppError 异常类测试。"""

    def test_app_error_creation(self):
        """AppError 正确存储所有字段。"""
        err = AppError(code="TEST_CODE", message="test message", http_status=404)
        assert err.code == "TEST_CODE"
        assert err.message == "test message"
        assert err.http_status == 404
        assert err.context == {}

    def test_app_error_detail_alias(self):
        """.detail 属性别名返回 message。"""
        err = AppError(code="TEST", message="hello", http_status=400)
        assert err.detail == "hello"

    def test_app_error_status_code_alias(self):
        """.status_code 属性别名返回 http_status。"""
        err = AppError(code="TEST", message="hello", http_status=503)
        assert err.status_code == 503

    def test_to_dict_without_context(self):
        """to_dict() 默认不包含 context。"""
        err = AppError(code="TEST", message="msg", http_status=400, context={"key": "val"})
        d = err.to_dict()
        assert d == {"code": "TEST", "message": "msg"}

    def test_to_dict_with_context(self):
        """to_dict(include_context=True) 包含 context。"""
        err = AppError(code="TEST", message="msg", http_status=400, context={"key": "val"})
        d = err.to_dict(include_context=True)
        assert d == {"code": "TEST", "message": "msg", "context": {"key": "val"}}

    def test_app_error_is_exception(self):
        """AppError 是 Exception 子类。"""
        assert issubclass(AppError, Exception)

    def test_app_error_chain(self):
        """AppError 支持 raise from 链。"""
        try:
            try:
                raise ValueError("original")
            except ValueError as e:
                raise AppError(code="CHAIN", message="wrapped", http_status=500) from e
        except AppError as ae:
            assert ae.code == "CHAIN"
            assert ae.__cause__ is not None
            assert isinstance(ae.__cause__, ValueError)

    def test_app_error_context_default_empty(self):
        """context 默认为空字典。"""
        err = AppError(code="TEST", message="msg")
        assert err.context == {}

    def test_app_error_with_context(self):
        """context 正确存储传入的字典。"""
        ctx = {"user_id": 123, "action": "login"}
        err = AppError(code="TEST", message="msg", http_status=400, context=ctx)
        assert err.context == ctx
