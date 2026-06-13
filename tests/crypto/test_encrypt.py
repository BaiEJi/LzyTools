"""
Encrypt 模块测试。

测试 Fernet 对称加密/解密功能。
"""

import time

import pytest
from cryptography.fernet import Fernet

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.encrypt import (
    decrypt,
    decrypt_str,
    encrypt,
    encrypt_str,
    generate_fernet_key,
)
from basic_tool.crypto.exceptions import DecryptionError, InvalidKeyError


class TestEncryptDecrypt:
    """Fernet 加密解密测试。"""

    def setup_method(self):
        """每个测试前生成新的密钥。"""
        self.key = generate_fernet_key()
        self.config = CryptoConfig(fernet_key=self.key)

    def test_encrypt_decrypt_roundtrip(self):
        """加密后解密应还原原始字节。"""
        plaintext = b"hello world"
        token = encrypt(plaintext, self.config)
        assert decrypt(token, self.config) == plaintext

    def test_decrypt_wrong_key(self):
        """用不同密钥解密应抛出 DecryptionError。"""
        key1 = generate_fernet_key()
        key2 = generate_fernet_key()
        config1 = CryptoConfig(fernet_key=key1)
        config2 = CryptoConfig(fernet_key=key2)
        token = encrypt(b"secret", config1)
        with pytest.raises(DecryptionError):
            decrypt(token, config2)

    def test_decrypt_tampered_ciphertext(self):
        """篡改密文后解密应抛出 DecryptionError。"""
        token = encrypt(b"original data", self.config)
        last_char = token[-1:]
        replacement = b"Z" if last_char != b"Z" else b"Y"
        tampered = token[:-1] + replacement
        with pytest.raises(DecryptionError):
            decrypt(tampered, self.config)

    def test_decrypt_ttl_expired(self):
        """TTL 过期后解密应抛出 DecryptionError。"""
        token = encrypt(b"will expire", self.config)
        time.sleep(2.1)
        with pytest.raises(DecryptionError):
            decrypt(token, self.config, ttl=1)

    def test_encrypt_str_decrypt_str_roundtrip(self):
        """字符串加密/解密往返测试（含非 ASCII 字符）。"""
        text = "你好世界"
        token = encrypt_str(text, self.config)
        assert decrypt_str(token, self.config) == text

    def test_generate_fernet_key_valid(self):
        """generate_fernet_key 返回的密钥能创建 Fernet 实例。"""
        key = generate_fernet_key()
        Fernet(key.encode() if isinstance(key, str) else key)

    def test_empty_fernet_key_raises(self):
        """空密钥加密应抛出 InvalidKeyError。"""
        config = CryptoConfig(fernet_key="")
        with pytest.raises(InvalidKeyError):
            encrypt(b"anything", config)

    def test_empty_bytes_roundtrip(self):
        """空字节加密/解密往返测试。"""
        token = encrypt(b"", self.config)
        assert decrypt(token, self.config) == b""
