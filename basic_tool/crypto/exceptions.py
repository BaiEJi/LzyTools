"""
密码学异常模块。

定义密码学操作中使用的所有异常类型。
所有异常继承自 CryptoError，便于上层统一捕获。
CryptoError 继承自 AppError，携带错误码与 HTTP 状态码，
可被统一错误处理中间件转换为标准化 JSON 响应。
"""

from basic_tool.errors import AppError


class CryptoError(AppError):
    """密码学操作的基础异常。

    所有具体密码学异常的基类，直接继承 AppError。
    一般不直接抛出，用于上层统一捕获。

    Attributes:
        code: 错误码，固定为 'CRYPTO_ERROR'。
        http_status: HTTP 状态码，固定为 500。
    """

    def __init__(self, message: str) -> None:
        """初始化 CryptoError。

        Args:
            message: 人类可读的错误消息。
        """
        super().__init__(code="CRYPTO_ERROR", message=message, http_status=500)


class DecryptionError(CryptoError):
    """解密失败异常（密钥错误、密文损坏或 TTL 过期）。

    Attributes:
        code: 错误码，固定为 'DECRYPTION_ERROR'。
        http_status: HTTP 状态码，固定为 400。
    """

    def __init__(self, message: str) -> None:
        """初始化 DecryptionError。

        Args:
            message: 人类可读的错误消息。
        """
        super().__init__(message)
        self.code = "DECRYPTION_ERROR"
        self.http_status = 400


class SignatureVerificationError(CryptoError):
    """签名验证失败异常。

    Attributes:
        code: 错误码，固定为 'SIGNATURE_VERIFICATION_FAILED'。
        http_status: HTTP 状态码，固定为 403。
    """

    def __init__(self, message: str) -> None:
        """初始化 SignatureVerificationError。

        Args:
            message: 人类可读的错误消息。
        """
        super().__init__(message)
        self.code = "SIGNATURE_VERIFICATION_FAILED"
        self.http_status = 403


class InvalidKeyError(CryptoError):
    """密钥无效异常。

    Attributes:
        code: 错误码，固定为 'INVALID_KEY'。
        http_status: HTTP 状态码，固定为 400。
    """

    def __init__(self, message: str) -> None:
        """初始化 InvalidKeyError。

        Args:
            message: 人类可读的错误消息。
        """
        super().__init__(message)
        self.code = "INVALID_KEY"
        self.http_status = 400
