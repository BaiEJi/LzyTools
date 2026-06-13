"""
密钥派生模块。

提供 HKDF 和 PBKDF2 密钥派生函数，用于从主密钥/密码派生出安全的子密钥。
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_hkdf(
    master_key: bytes,
    salt: bytes,
    info: bytes,
    length: int = 32,
) -> bytes:
    """
    使用 HKDF 从主密钥派生子密钥。

    HKDF 适用于已有高熵主密钥的密钥扩展场景。

    Args:
        master_key: 主密钥（高熵随机数据）
        salt: 盐值（随机但不要求保密）
        info: 上下文信息，不同 info 派生出不同密钥
        length: 输出密钥长度（字节），默认 32

    Returns:
        派生出的密钥字节
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(master_key)


def derive_key_pbkdf2(
    password: bytes,
    salt: bytes,
    iterations: int = 600000,
    length: int = 32,
) -> bytes:
    """
    使用 PBKDF2 从密码派生密钥。

    PBKDF2 适用于低熵密码的密钥派生场景，通过高迭代次数抵抗暴力破解。
    OWASP 2025 推荐 PBKDF2-SHA256 迭代次数 ≥ 600,000。

    Args:
        password: 用户密码（低熵）
        salt: 盐值（随机且唯一）
        iterations: 迭代次数，默认 600,000（OWASP 2025 推荐）
        length: 输出密钥长度（字节），默认 32

    Returns:
        派生出的密钥字节
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password)
