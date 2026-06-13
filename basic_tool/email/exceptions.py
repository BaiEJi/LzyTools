"""邮件模块统一异常类型。"""


class EmailError(Exception):
    """邮件模块基础异常。"""


class SendError(EmailError):
    """邮件发送失败（SMTP 连接错误、认证失败、被拒绝等）。

    Attributes:
        message: 错误描述。
        original: 原始异常（可选）。
    """

    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


class TemplateError(EmailError):
    """模板渲染失败（模板不存在、语法错误、变量缺失等）。"""
