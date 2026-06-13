"""basic_tool.email — 异步邮件发送模块。

提供统一的邮件发送抽象层，支持 SMTP 发送、Jinja2 模板渲染、
批量发送和测试模式（DryRunSender）。

典型用法:
    from basic_tool.email import Email, EmailConfig, SmtpSender

    config = EmailConfig(host="smtp.example.com", username="user", password="pass")
    sender = SmtpSender(config)
    result = await sender.send(Email(to="to@example.com", subject="Hi", body="Hello"))
"""
from basic_tool.email.config import EmailConfig
from basic_tool.email.dry_run import DryRunSender
from basic_tool.email.exceptions import EmailError, SendError, TemplateError
from basic_tool.email.models import Attachment, Email, InlineImage, SendResult
from basic_tool.email.sender import EmailSender, SmtpSender
from basic_tool.email.task import send_email_task, setup_email_worker

__all__ = [
    # config
    "EmailConfig",
    # models
    "Email",
    "Attachment",
    "InlineImage",
    "SendResult",
    # sender
    "EmailSender",
    "SmtpSender",
    # dry_run
    "DryRunSender",
    # task
    "send_email_task",
    "setup_email_worker",
    # exceptions
    "EmailError",
    "SendError",
    "TemplateError",
]
