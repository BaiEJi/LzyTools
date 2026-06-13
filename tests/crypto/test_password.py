"""
Password 模块测试。

测试 Argon2id 密码哈希、验证、重哈希检测和 Token 生成。
"""

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.password import (
    generate_hex_token,
    generate_token,
    hash_password,
    needs_rehash,
    verify_password,
)

# 低开销配置，加速测试
LOW_CONFIG = CryptoConfig(argon2_memory_cost=1024, argon2_time_cost=1, argon2_parallelism=1)


class TestPasswordHashing:
    """密码哈希与验证测试。"""

    def test_hash_password_generates_argon2id(self):
        """hash_password 返回以 $argon2id$ 开头的非空哈希。"""
        h = hash_password("my_secret", config=LOW_CONFIG)
        assert h
        assert h.startswith("$argon2id$")

    def test_verify_password_correct(self):
        """verify_password 对正确密码返回 True。"""
        h = hash_password("correct_pass", config=LOW_CONFIG)
        assert verify_password("correct_pass", h, config=LOW_CONFIG) is True

    def test_verify_password_wrong(self):
        """verify_password 对错误密码返回 False，不抛异常。"""
        h = hash_password("correct_pass", config=LOW_CONFIG)
        assert verify_password("wrong_pass", h, config=LOW_CONFIG) is False

    def test_verify_password_tampered_hash(self):
        """verify_password 对篡改的哈希字符串返回 False。"""
        h = hash_password("correct_pass", config=LOW_CONFIG)
        tampered = h[:-4] + "AAAA"
        assert verify_password("correct_pass", tampered, config=LOW_CONFIG) is False

    def test_verify_password_invalid_hash_string(self):
        """verify_password 对完全无效字符串返回 False。"""
        assert verify_password("correct_pass", "not-a-hash", config=LOW_CONFIG) is False


class TestNeedsRehash:
    """重哈希检测测试。"""

    def test_needs_rehash_default_params(self):
        """默认配置生成的哈希不需要 rehash。"""
        h = hash_password("secret", config=LOW_CONFIG)
        assert needs_rehash(h, config=LOW_CONFIG) is False

    def test_needs_rehash_different_params(self):
        """用低参数哈希、用更高参数检测时返回 True。"""
        h = hash_password("secret", config=LOW_CONFIG)
        high_config = CryptoConfig(argon2_memory_cost=1024, argon2_time_cost=10, argon2_parallelism=1)
        assert needs_rehash(h, config=high_config) is True


class TestTokenGeneration:
    """Token 生成测试。"""

    def test_generate_token_default_length(self):
        """generate_token 默认返回 43 字符（32 字节 URL-safe）。"""
        token = generate_token()
        assert len(token) == 43

    def test_generate_token_uniqueness(self):
        """连续生成 100 次 generate_token 无重复。"""
        tokens = {generate_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_generate_hex_token_default_length(self):
        """generate_hex_token 默认返回 64 字符（32 字节 hex）。"""
        token = generate_hex_token()
        assert len(token) == 64

    def test_generate_hex_token_uniqueness(self):
        """连续生成 100 次 generate_hex_token 无重复。"""
        tokens = {generate_hex_token() for _ in range(100)}
        assert len(tokens) == 100
