"""
密码学异常模块。

定义密码学操作中使用的所有异常类型。
所有异常继承自 CryptoError，便于上层统一捕获。
"""


class CryptoError(Exception):
    """密码学操作的基础异常。"""


class DecryptionError(CryptoError):
    """解密失败异常（密钥错误、密文损坏或 TTL 过期）。"""


class SignatureVerificationError(CryptoError):
    """签名验证失败异常。"""


class InvalidKeyError(CryptoError):
    """密钥无效异常。"""
