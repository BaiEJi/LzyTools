"""DryRunSender 单元测试。

覆盖：send 记录、send_bulk 批量、reset 清空、sent_emails 只读副本。
"""
from __future__ import annotations

import pytest

from basic_tool.email.dry_run import DryRunSender
from basic_tool.email.models import Email


def _email(to: str = "a@test.com", subject: str = "Hi", body: str = "Hello") -> Email:
    """创建测试用 Email 的快捷工厂。"""
    return Email(to=to, subject=subject, body=body)


class TestDryRunSender:
    """DryRunSender 测试集。"""

    async def test_send_records_and_returns_success(self) -> None:
        """send() 记录到 sent_emails 并返回 success=True。"""
        sender = DryRunSender()
        email = _email(subject="Test1")

        result = await sender.send(email)

        assert result.success
        assert result.message_id == "dry-run-1"
        assert result.recipient == "a@test.com"
        assert len(sender.sent_emails) == 1
        assert sender.sent_emails[0].subject == "Test1"

    async def test_send_bulk_records_all(self) -> None:
        """send_bulk() 记录所有邮件，sent_count 正确。"""
        sender = DryRunSender()
        emails = [_email(subject="A"), _email(subject="B"), _email(subject="C")]

        results = await sender.send_bulk(emails)

        assert len(results) == 3
        assert sender.sent_count == 3
        assert all(r.success for r in results)
        assert [r.message_id for r in results] == [
            "dry-run-1",
            "dry-run-2",
            "dry-run-3",
        ]

    async def test_reset_clears_records(self) -> None:
        """reset() 清空已发送记录。"""
        sender = DryRunSender()
        await sender.send(_email())
        assert sender.sent_count == 1

        sender.reset()

        assert sender.sent_count == 0
        assert sender.sent_emails == []

    async def test_sent_emails_returns_readonly_copy(self) -> None:
        """sent_emails 返回只读副本，修改不影响内部状态。"""
        sender = DryRunSender()
        await sender.send(_email(subject="Original"))

        copy = sender.sent_emails
        copy.clear()

        assert sender.sent_count == 1
        assert sender.sent_emails[0].subject == "Original"
