"""
密码学配置模块。

定义密码学操作所需的所有参数。
"""

from pydantic import BaseModel


class CryptoConfig(BaseModel):
    """
    密码学配置。

    Attributes:
        argon2_memory_cost: Argon2id 内存开销 (KB)，OWASP 推荐 65536 (64MB)
        argon2_time_cost: Argon2id 迭代次数，OWASP 推荐 3
        argon2_parallelism: Argon2id 并行度
        argon2_hash_len: Argon2id 哈希输出长度 (字节)
        argon2_salt_len: Argon2id 盐长度 (字节)
        token_bytes: 生成的随机 token 字节数
        fernet_key: Fernet 加密密钥 (base64 编码的 url-safe 字符串)，为空时需显式提供
    """

    argon2_memory_cost: int = 65536
    argon2_time_cost: int = 3
    argon2_parallelism: int = 1
    argon2_hash_len: int = 32
    argon2_salt_len: int = 16
    token_bytes: int = 32
    fernet_key: str = ""
