"""
Sign 模块测试。

测试 HMAC-SHA256 签名验证和 SHA-256 哈希。
"""

from basic_tool.crypto.sign import sha256, sha256_hex, sign, verify


class TestSignVerify:
    """HMAC-SHA256 签名与验证测试。"""

    def test_sign_verify_roundtrip(self):
        """sign → verify 往返应返回 True。"""
        data = b"hello world"
        key = b"secret-key"
        signature = sign(data, key)
        assert verify(data, key, signature) is True

    def test_verify_wrong_signature(self):
        """错误的签名应验证失败。"""
        data = b"hello world"
        key = b"secret-key"
        assert verify(data, key, "deadbeef") is False

    def test_verify_tampered_data(self):
        """篡改后的数据应验证失败。"""
        key = b"secret-key"
        signature = sign(b"original data", key)
        assert verify(b"tampered data", key, signature) is False


class TestSha256:
    """SHA-256 哈希测试。"""

    def test_sha256_deterministic(self):
        """相同输入应产生相同输出。"""
        data = b"hello world"
        assert sha256(data) == sha256(data)

    def test_sha256_hex_alias(self):
        """sha256_hex 是 sha256 的别名。"""
        data = b"hello world"
        assert sha256_hex(data) == sha256(data)

    def test_sha256_output_length(self):
        """SHA-256 十六进制输出应为 64 字符。"""
        data = b"hello world"
        assert len(sha256(data)) == 64
