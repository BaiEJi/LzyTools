"""
Fernet 对称加密模块。

提供基于 Fernet 的对称加密/解密能力，支持 TTL 过期检查。
"""

from cryptography.fernet import Fernet, InvalidToken

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.exceptions import DecryptionError, InvalidKeyError


def _get_fernet(config: CryptoConfig) -> Fernet:
    """
    从配置中获取 Fernet 实例。

    Args:
        config: 密码学配置，必须包含 fernet_key

    Returns:
        Fernet 实例

    Raises:
        InvalidKeyError: fernet_key 为空或无效时抛出
    """
    if not config.fernet_key:
        raise InvalidKeyError("fernet_key is empty")
    try:
        return Fernet(
            config.fernet_key.encode()
            if isinstance(config.fernet_key, str)
            else config.fernet_key
        )
    except Exception as e:
        raise InvalidKeyError(f"invalid fernet_key: {e}")


def generate_fernet_key() -> str:
    """
    生成一个新的 Fernet 密钥。

    Returns:
        URL-safe base64 编码的密钥字符串，可直接用于 CryptoConfig.fernet_key
    """
    return Fernet.generate_key().decode()


def encrypt(data: bytes, config: CryptoConfig) -> bytes:
    """
    加密二进制数据。

    Args:
        data: 待加密的明文字节
        config: 密码学配置，必须包含 fernet_key

    Returns:
        Fernet 加密后的密文字节

    Raises:
        InvalidKeyError: fernet_key 为空或无效时抛出
    """
    fernet = _get_fernet(config)
    return fernet.encrypt(data)


def decrypt(token: bytes, config: CryptoConfig, ttl: int | None = None) -> bytes:
    """
    解密二进制密文。

    Args:
        token: Fernet 加密的密文字节
        config: 密码学配置，必须包含 fernet_key
        ttl: 生存时间（秒），超过则视为过期。为 None 时不检查过期

    Returns:
        解密后的明文字节

    Raises:
        DecryptionError: 解密失败（密钥错误、密文损坏或 TTL 过期）
        InvalidKeyError: fernet_key 为空或无效
    """
    fernet = _get_fernet(config)
    try:
        return fernet.decrypt(token, ttl=ttl)
    except InvalidToken as e:
        raise DecryptionError(f"decryption failed: {e}")


def encrypt_str(text: str, config: CryptoConfig) -> bytes:
    """
    加密字符串。

    Args:
        text: 待加密的明文字符串（UTF-8 编码）
        config: 密码学配置，必须包含 fernet_key

    Returns:
        Fernet 加密后的密文字节

    Raises:
        InvalidKeyError: fernet_key 为空或无效时抛出
    """
    return encrypt(text.encode("utf-8"), config)


def decrypt_str(token: bytes, config: CryptoConfig, ttl: int | None = None) -> str:
    """
    解密密文为字符串。

    Args:
        token: Fernet 加密的密文字节
        config: 密码学配置，必须包含 fernet_key
        ttl: 生存时间（秒），超过则视为过期

    Returns:
        解密后的 UTF-8 字符串

    Raises:
        DecryptionError: 解密失败
        InvalidKeyError: fernet_key 为空或无效
    """
    return decrypt(token, config, ttl=ttl).decode("utf-8")
