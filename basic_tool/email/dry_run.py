"""DryRunSender：测试模式邮件发送器。

不真实发送邮件，将所有发送记录到内存列表，
供开发调试和单元测试断言使用。
"""
from __future__ import annotations

from loguru import logger

from basic_tool.email.models import Email, SendResult
from basic_tool.email.sender import EmailSender


class DryRunSender(EmailSender):
    """测试模式发送器。

    不真实发送邮件，记录到 sent_emails 列表。
    适用于开发环境和 pytest 单元测试。

    Examples:
        sender = DryRunSender()
        result = await sender.send(Email(to="test@example.com", subject="Hi", body="Hello"))

        assert result.success
        assert len(sender.sent_emails) == 1
        assert sender.sent_emails[0].subject == "Hi"

        # 重置记录
        sender.reset()
    """

    def __init__(self) -> None:
        """初始化 DryRunSender。"""
        self._sent: list[Email] = []

    @property
    def sent_emails(self) -> list[Email]:
        """已发送的邮件列表（只读副本）。"""
        return list(self._sent)

    @property
    def sent_count(self) -> int:
        """已发送邮件数量。"""
        return len(self._sent)

    def reset(self) -> None:
        """清空已发送记录。"""
        self._sent.clear()

    async def send(self, email: Email) -> SendResult:
        """记录邮件（不真实发送）。

        Args:
            email: 邮件数据模型。

        Returns:
            SendResult(success=True)，message_id 为 dry-run 标识。
        """
        self._sent.append(email)
        message_id = f"dry-run-{len(self._sent)}"
        logger.debug(
            "dry-run email recorded | to={} subject={}",
            email.to_list,
            email.subject,
        )
        return SendResult(
            success=True,
            message_id=message_id,
            recipient=", ".join(email.to_list),
        )
