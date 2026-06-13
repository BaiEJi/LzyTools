"""
basic_tool.crypto 包的初始化模块。

统一导出密码学相关组件:
    from basic_tool.crypto import hash_password, encrypt, sign, derive_key_hkdf, CryptoConfig
"""

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.encrypt import decrypt, decrypt_str, encrypt, encrypt_str, generate_fernet_key
from basic_tool.crypto.exceptions import CryptoError, DecryptionError, InvalidKeyError, SignatureVerificationError
from basic_tool.crypto.kdf import derive_key_hkdf, derive_key_pbkdf2
from basic_tool.crypto.password import generate_hex_token, generate_token, hash_password, needs_rehash, verify_password
from basic_tool.crypto.sign import sha256, sha256_hex, sign, verify

__all__ = [
    "CryptoConfig",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "generate_token",
    "generate_hex_token",
    "generate_fernet_key",
    "encrypt",
    "decrypt",
    "encrypt_str",
    "decrypt_str",
    "sign",
    "verify",
    "sha256",
    "sha256_hex",
    "derive_key_hkdf",
    "derive_key_pbkdf2",
]
