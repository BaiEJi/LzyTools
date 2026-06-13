"""
KDF 模块测试。

测试 HKDF 和 PBKDF2 密钥派生功能。
"""

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.kdf import derive_key_hkdf, derive_key_pbkdf2


class TestHKDF:
    """HKDF 密钥派生测试。"""

    def test_hkdf_different_info_different_keys(self):
        """不同 info 派生出不同的密钥。"""
        key = b"master_key_1234567890123456789012"
        salt = b"random_salt_1234567"
        k1 = derive_key_hkdf(key, salt, b"encryption")
        k2 = derive_key_hkdf(key, salt, b"signing")
        assert k1 != k2

    def test_hkdf_deterministic(self):
        """相同输入始终派生出相同密钥。"""
        key = b"master_key_1234567890123456789012"
        salt = b"random_salt_1234567"
        k1 = derive_key_hkdf(key, salt, b"encryption")
        k2 = derive_key_hkdf(key, salt, b"encryption")
        assert k1 == k2

    def test_hkdf_default_length(self):
        """默认输出长度为 32 字节。"""
        key = b"master_key_1234567890123456789012"
        salt = b"random_salt_1234567"
        derived = derive_key_hkdf(key, salt, b"context")
        assert len(derived) == 32


class TestPBKDF2:
    """PBKDF2 密钥派生测试。"""

    def test_pbkdf2_deterministic(self):
        """相同输入始终派生出相同密钥。"""
        password = b"my_password"
        salt = b"unique_salt_1234567"
        k1 = derive_key_pbkdf2(password, salt)
        k2 = derive_key_pbkdf2(password, salt)
        assert k1 == k2


class TestCryptoConfig:
    """CryptoConfig 自定义参数测试。"""

    def test_custom_argon2_params(self):
        """CryptoConfig 支持自定义 argon2_time_cost 和 argon2_memory_cost。"""
        config1 = CryptoConfig(argon2_time_cost=10)
        assert config1.argon2_time_cost == 10

        config2 = CryptoConfig(argon2_memory_cost=8192)
        assert config2.argon2_memory_cost == 8192
