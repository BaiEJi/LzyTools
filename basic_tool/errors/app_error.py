"""AppError 业务异常基类。

提供统一的业务异常，携带错误码、消息、HTTP 状态码和上下文信息。
向后兼容旧 API：通过 .detail 和 .status_code 属性别名。
"""

from typing import Any


class AppError(Exception):
    """业务异常基类，自动转换为标准化 JSON 响应。

    Attributes:
        code: 错误码（如 'PARAM_MISSING'）。
        message: 人类可读的错误消息。
        http_status: HTTP 状态码。
        context: 额外上下文字典（可选）。
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        context: dict[str, Any] | None = None,
    ) -> None:
        """初始化 AppError。

        Args:
            code: 错误码。
            message: 错误消息。
            http_status: HTTP 状态码，默认 400。
            context: 额外上下文，默认空字典。
        """
        self.code = code
        self.message = message
        self.http_status = http_status
        self.context = context if context is not None else {}
        super().__init__(message)

    @property
    def detail(self) -> str:
        """向后兼容别名，返回 message。

        Returns:
            错误消息字符串。
        """
        return self.message

    @property
    def status_code(self) -> int:
        """向后兼容别名，返回 http_status。

        Returns:
            HTTP 状态码。
        """
        return self.http_status

    def to_dict(self, include_context: bool = False) -> dict[str, Any]:
        """转换为可序列化的字典。

        Args:
            include_context: 是否包含 context 字段。

        Returns:
            包含 code、message（及可选 context）的字典。
        """
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if include_context and self.context:
            result["context"] = self.context
        return result

    def __repr__(self) -> str:
        """返回调试友好的表示。"""
        return f"AppError(code={self.code!r}, message={self.message!r}, http_status={self.http_status})"
