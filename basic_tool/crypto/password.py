"""
密码哈希与 Token 生成模块。

提供 Argon2id 密码哈希、验证、重哈希检测，以及 CSPRNG Token 生成。
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError, VerificationError
from secrets import token_hex, token_urlsafe

from basic_tool.crypto.config import CryptoConfig
from basic_tool.crypto.exceptions import CryptoError  # 保留导入供未来使用


def _get_hasher(config: CryptoConfig | None = None) -> PasswordHasher:
    """根据配置创建 Argon2id PasswordHasher 实例。"""
    if config is None:
        config = CryptoConfig()
    return PasswordHasher(
        memory_cost=config.argon2_memory_cost,
        time_cost=config.argon2_time_cost,
        parallelism=config.argon2_parallelism,
        hash_len=config.argon2_hash_len,
        salt_len=config.argon2_salt_len,
    )


def hash_password(password: str, config: CryptoConfig | None = None) -> str:
    """
    使用 Argon2id 算法哈希密码。

    Args:
        password: 明文密码
        config: 密码学配置，为 None 时使用默认配置

    Returns:
        Argon2id 哈希字符串，格式如 $argon2id$v=19$m=65536,t=3,p=1$...
    """
    hasher = _get_hasher(config)
    return hasher.hash(password)


def verify_password(password: str, hash: str, config: CryptoConfig | None = None) -> bool:
    """
    验证密码是否匹配 Argon2id 哈希。

    Args:
        password: 待验证的明文密码
        hash: Argon2id 哈希字符串
        config: 密码学配置，为 None 时使用默认配置

    Returns:
        True 表示密码匹配，False 表示不匹配或哈希无效（不抛异常）
    """
    hasher = _get_hasher(config)
    try:
        hasher.verify(hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash, Exception):
        return False


def needs_rehash(hash: str, config: CryptoConfig | None = None) -> bool:
    """
    检查哈希是否需要使用新参数重新计算。

    Args:
        hash: 现有的 Argon2id 哈希字符串
        config: 目标配置参数，为 None 时使用默认配置

    Returns:
        True 表示哈希参数与当前配置不符，需要重新哈希
    """
    hasher = _get_hasher(config)
    return hasher.check_needs_rehash(hash)


def generate_token(length: int | None = None, config: CryptoConfig | None = None) -> str:
    """
    生成 URL-safe 的随机 Token。

    Args:
        length: Token 的字节长度，为 None 时使用 config.token_bytes
        config: 密码学配置，为 None 时使用默认配置

    Returns:
        URL-safe base64 编码的 Token 字符串（32 字节 → 43 字符）
    """
    if length is None:
        if config is None:
            config = CryptoConfig()
        length = config.token_bytes
    return token_urlsafe(length)


def generate_hex_token(length: int | None = None, config: CryptoConfig | None = None) -> str:
    """
    生成十六进制编码的随机 Token。

    Args:
        length: Token 的字节长度，为 None 时使用 config.token_bytes
        config: 密码学配置，为 None 时使用默认配置

    Returns:
        十六进制编码的 Token 字符串（32 字节 → 64 字符）
    """
    if length is None:
        if config is None:
            config = CryptoConfig()
        length = config.token_bytes
    return token_hex(length)
