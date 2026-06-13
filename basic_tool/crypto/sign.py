"""
HMAC 签名与哈希模块。

提供 HMAC-SHA256 签名/验证和 SHA-256 哈希计算。
纯标准库实现，无外部依赖。
"""

import hashlib
import hmac

from basic_tool.crypto.exceptions import CryptoError  # 保留导入供未来使用


def sign(data: bytes, key: bytes) -> str:
    """
    使用 HMAC-SHA256 对数据签名。

    Args:
        data: 待签名的数据
        key: 签名密钥

    Returns:
        十六进制编码的 HMAC-SHA256 签名（64 字符）
    """
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify(data: bytes, key: bytes, signature: str) -> bool:
    """
    验证 HMAC-SHA256 签名。

    Args:
        data: 原始数据
        key: 签名密钥
        signature: 待验证的十六进制签名

    Returns:
        True 表示签名匹配，False 表示不匹配
    """
    expected = sign(data, key)
    return hmac.compare_digest(expected, signature)


def sha256(data: bytes) -> str:
    """
    计算 SHA-256 哈希。

    Args:
        data: 待哈希的数据

    Returns:
        十六进制编码的 SHA-256 哈希（64 字符）
    """
    return hashlib.sha256(data).hexdigest()


# sha256_hex 是 sha256 的别名
sha256_hex = sha256
