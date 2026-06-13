"""
Crypto 异常层次结构测试。

验证 CryptoError 及其子类正确继承 AppError，
并携带预期的 code 与 http_status 属性。
"""

import pytest

from basic_tool.crypto.exceptions import (
    CryptoError,
    DecryptionError,
    InvalidKeyError,
    SignatureVerificationError,
)
from basic_tool.errors import AppError


class TestCryptoErrorInheritance:
    """验证密码学异常继承自 AppError。"""

    def test_crypto_error_is_app_error(self):
        """CryptoError 实例应为 AppError 实例。"""
        err = CryptoError("boom")
        assert isinstance(err, AppError)

    def test_crypto_error_is_exception(self):
        """CryptoError 仍应是 Exception（向后兼容）。"""
        err = CryptoError("boom")
        assert isinstance(err, Exception)

    @pytest.mark.parametrize(
        "exc_cls",
        [DecryptionError, InvalidKeyError, SignatureVerificationError],
    )
    def test_subclasses_inherit_app_error(self, exc_cls):
        """所有子类应为 AppError 与 CryptoError 实例。"""
        err = exc_cls("msg")
        assert isinstance(err, AppError)
        assert isinstance(err, CryptoError)


class TestCryptoErrorCodesAndStatus:
    """验证每个异常的 code 与 http_status。"""

    def test_crypto_error_code_and_status(self):
        """CryptoError code=CRYPTO_ERROR, http_status=500。"""
        err = CryptoError("boom")
        assert err.code == "CRYPTO_ERROR"
        assert err.http_status == 500

    def test_decryption_error_code_and_status(self):
        """DecryptionError code=DECRYPTION_ERROR, http_status=400。"""
        err = DecryptionError("failed")
        assert err.code == "DECRYPTION_ERROR"
        assert err.http_status == 400

    def test_invalid_key_error_code_and_status(self):
        """InvalidKeyError code=INVALID_KEY, http_status=400。"""
        err = InvalidKeyError("bad key")
        assert err.code == "INVALID_KEY"
        assert err.http_status == 400

    def test_signature_verification_error_code_and_status(self):
        """SignatureVerificationError code=SIGNATURE_VERIFICATION_FAILED, http_status=403。"""
        err = SignatureVerificationError("mismatch")
        assert err.code == "SIGNATURE_VERIFICATION_FAILED"
        assert err.http_status == 403


class TestCryptoErrorMessageAndRaising:
    """验证 message 传递与 raise 行为（向后兼容）。"""

    def test_message_preserved(self):
        """构造函数传入的 message 应保留在 .message 与 str()。"""
        err = DecryptionError("decryption failed: bad token")
        assert err.message == "decryption failed: bad token"
        assert "decryption failed: bad token" in str(err)

    def test_raise_decryption_error_caught_as_app_error(self):
        """raise DecryptionError 可被 except AppError 捕获。"""
        with pytest.raises(AppError):
            raise DecryptionError("fail")

    def test_raise_invalid_key_caught_as_crypto_error(self):
        """raise InvalidKeyError 可被 except CryptoError 捕获。"""
        with pytest.raises(CryptoError):
            raise InvalidKeyError("empty")

    def test_raise_signature_caught_as_exception(self):
        """raise SignatureVerificationError 可被 except Exception 捕获。"""
        with pytest.raises(Exception):
            raise SignatureVerificationError("nope")

    def test_subclass_caught_by_parent(self):
        """子类异常可被父类 except 子句捕获（多态）。"""
        with pytest.raises(CryptoError):
            raise DecryptionError("x")
        with pytest.raises(CryptoError):
            raise InvalidKeyError("x")
        with pytest.raises(CryptoError):
            raise SignatureVerificationError("x")


class TestAppErrorCompatAttributes:
    """验证 AppError 的兼容属性在 crypto 异常上可用。"""

    def test_detail_alias(self):
        """.detail 应返回 message。"""
        err = DecryptionError("hello")
        assert err.detail == "hello"

    def test_status_code_alias(self):
        """.status_code 应返回 http_status。"""
        err = SignatureVerificationError("hello")
        assert err.status_code == 403

    def test_to_dict(self):
        """to_dict() 应返回 code 与 message。"""
        err = InvalidKeyError("empty key")
        d = err.to_dict()
        assert d == {"code": "INVALID_KEY", "message": "empty key"}

    def test_context_default_empty(self):
        """默认 context 应为空字典。"""
        err = CryptoError("boom")
        assert err.context == {}
