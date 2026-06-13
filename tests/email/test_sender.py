"""basic_tool.email.sender 的单元测试。

覆盖 SmtpSender 构造、_build_message 各种场景、send() 的成功/失败路径、
BCC 隐私保证和 MIMEMultipart 结构验证。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from basic_tool.email.config import EmailConfig
from basic_tool.email.exceptions import SendError
from basic_tool.email.models import Attachment, Email, InlineImage, SendResult
from basic_tool.email.sender import SmtpSender


def _make_config(**overrides) -> EmailConfig:
    """创建测试用 EmailConfig，提供合理默认值。"""
    defaults = dict(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        sender="noreply@example.com",
        sender_name="TestApp",
    )
    defaults.update(overrides)
    return EmailConfig(**defaults)


def _make_sender(**config_overrides) -> SmtpSender:
    """创建测试用 SmtpSender。"""
    return SmtpSender(_make_config(**config_overrides))


# --- Case 12: SmtpSender construction ---


def test_smtp_sender_stores_config():
    """Case 12 — SmtpSender 构造后 config 正确存储。"""
    config = _make_config(host="mail.test.com", port=465)
    sender = SmtpSender(config)
    assert sender.config is config
    assert sender.config.host == "mail.test.com"
    assert sender.config.port == 465
    assert sender._smtp is None


# --- Case 13: _build_message From/To/Cc/Subject headers ---


def test_build_message_basic_headers():
    """Case 13 — _build_message 设置 From/To/Cc/Subject 头部。"""
    sender = _make_sender()
    email = Email(
        to=["alice@example.com", "bob@example.com"],
        cc="cc@example.com",
        subject="Hello",
        body="World",
    )
    msg = sender._build_message(email)

    assert msg["From"] == "TestApp <noreply@example.com>"
    assert msg["To"] == "alice@example.com, bob@example.com"
    assert msg["Cc"] == "cc@example.com"
    assert msg["Subject"] == "Hello"


# --- Case 14: _build_message with attachments ---


def test_build_message_with_attachments():
    """Case 14 — _build_message 包含附件，附件以 base64 编码附着到 root。"""
    sender = _make_sender()
    email = Email(
        to="user@example.com",
        subject="Report",
        body="See attached",
        attachments=[
            Attachment(filename="report.pdf", content=b"%PDF-1.4", content_type="application/pdf"),
        ],
    )
    msg = sender._build_message(email)

    parts = list(msg.walk())
    attachment_parts = [p for p in parts if p.get("Content-Disposition", "").startswith("attachment")]
    assert len(attachment_parts) == 1
    att = attachment_parts[0]
    assert "report.pdf" in att.get("Content-Disposition", "")


# --- Case 15: _build_message with inline images, Content-ID set ---


def test_build_message_inline_images_content_id():
    """Case 15 — _build_message 内嵌图片设置 Content-ID 和 inline disposition。"""
    sender = _make_sender()
    email = Email(
        to="user@example.com",
        subject="Logo",
        body='<img src="cid:logo">',
        content_type="text/html",
        inline_images=[
            InlineImage(cid="logo", content=b"\x89PNG\r\n", content_type="image/png"),
        ],
    )
    msg = sender._build_message(email)

    parts = list(msg.walk())
    img_parts = [p for p in parts if p.get("Content-ID") is not None]
    assert len(img_parts) == 1
    assert img_parts[0]["Content-ID"] == "<logo>"
    assert "inline" in img_parts[0].get("Content-Disposition", "")


# --- Case 16: _build_message with reply_to ---


def test_build_message_reply_to():
    """Case 16 — _build_message 设置 Reply-To 头部。"""
    sender = _make_sender()
    email = Email(
        to="user@example.com",
        subject="Reply me",
        body="body",
        reply_to="support@example.com",
    )
    msg = sender._build_message(email)
    assert msg["Reply-To"] == "support@example.com"


# --- Case 17: _build_message with custom headers ---


def test_build_message_custom_headers():
    """Case 17 — _build_message 设置自定义头部。"""
    sender = _make_sender()
    email = Email(
        to="user@example.com",
        subject="Test",
        body="body",
        headers={"X-Mailer": "TestRunner", "X-Priority": "1"},
    )
    msg = sender._build_message(email)
    assert msg["X-Mailer"] == "TestRunner"
    assert msg["X-Priority"] == "1"


# --- Case 18: send() connection failure raises SendError ---


async def test_send_connection_failure_raises_send_error():
    """Case 18 — send() 连接失败时抛出 SendError。"""
    sender = _make_sender()
    email = Email(to="user@example.com", subject="Test", body="body")

    mock_smtp = AsyncMock()
    mock_smtp.connect = AsyncMock(side_effect=OSError("Network unreachable"))
    mock_smtp.is_connected = False

    with patch("basic_tool.email.sender.aiosmtplib.SMTP", return_value=mock_smtp):
        with pytest.raises(SendError, match="SMTP connection failed"):
            await sender.send(email)


# --- Case 19: send() SMTP rejection returns SendResult(success=False) ---


async def test_send_smtp_rejection_returns_failure():
    """Case 19 — send() SMTP 拒绝时返回 SendResult(success=False)。"""
    sender = _make_sender()
    email = Email(to="user@example.com", subject="Test", body="body")

    mock_smtp = AsyncMock()
    mock_smtp.is_connected = True
    mock_smtp.send_message = AsyncMock(
        side_effect=aiosmtplib.SMTPResponseException(550, "Mailbox not found")
    )

    sender._smtp = mock_smtp

    result = await sender.send(email)
    assert result.success is False
    assert "550" in result.error or "Mailbox not found" in result.error
    assert result.recipient == "user@example.com"


# --- BCC privacy: BCC NOT in MIME headers but IN all_recipients ---


def test_bcc_not_in_mime_headers():
    """BCC 隐私 — BCC 地址不出现在 MIME 头部中。"""
    sender = _make_sender()
    email = Email(
        to="to@example.com",
        cc="cc@example.com",
        bcc="secret@example.com",
        subject="Private",
        body="body",
    )
    msg = sender._build_message(email)

    assert msg["Bcc"] is None
    assert msg["To"] == "to@example.com"
    assert msg["Cc"] == "cc@example.com"


def test_bcc_in_all_recipients():
    """BCC 隐私 — BCC 地址在 all_recipients 中，确保实际发送时包含。"""
    email = Email(
        to="to@example.com",
        bcc="secret@example.com",
        subject="Private",
        body="body",
    )
    assert "secret@example.com" in email.all_recipients


# --- MIMEMultipart structure validation ---


def test_build_message_produces_multipart_mixed():
    """MIME 结构 — _build_message 产生 MIMEMultipart('mixed') 根节点。"""
    sender = _make_sender()
    email = Email(to="user@example.com", subject="Test", body="Hello")
    msg = sender._build_message(email)

    assert msg.get_content_type() == "multipart/mixed"


def test_build_message_with_inline_images_has_related():
    """MIME 结构 — 有内嵌图片时存在 multipart/related 子结构。"""
    sender = _make_sender()
    email = Email(
        to="user@example.com",
        subject="Test",
        body='<img src="cid:logo">',
        content_type="text/html",
        inline_images=[InlineImage(cid="logo", content=b"\x89PNG", content_type="image/png")],
    )
    msg = sender._build_message(email)

    parts = list(msg.walk())
    related_parts = [p for p in parts if p.get_content_type() == "multipart/related"]
    assert len(related_parts) == 1


# --- send() success path ---


async def test_send_success_returns_send_result():
    """send() 成功路径 — 返回 SendResult(success=True) 含 message_id。"""
    sender = _make_sender()
    email = Email(to="user@example.com", subject="Test", body="body")

    mock_smtp = AsyncMock()
    mock_smtp.is_connected = True
    mock_smtp.send_message = AsyncMock(return_value=({}, "<msg123@smtp>"))

    sender._smtp = mock_smtp

    result = await sender.send(email)
    assert result.success is True
    assert result.message_id == "<msg123@smtp>"
    assert result.recipient == "user@example.com"


# --- send_bulk batches correctly ---


async def test_send_bulk_respects_batch_size():
    """send_bulk — 按 bulk_batch_size 分批发送。"""
    config = _make_config(bulk_batch_size=2)
    sender = SmtpSender(config)

    emails = [
        Email(to=f"user{i}@example.com", subject=f"Test {i}", body="body")
        for i in range(5)
    ]

    mock_smtp = AsyncMock()
    mock_smtp.is_connected = True
    mock_smtp.send_message = AsyncMock(return_value=({}, "<id@smtp>"))
    sender._smtp = mock_smtp

    results = await sender.send_bulk(emails)
    assert len(results) == 5
    assert all(r.success for r in results)


# --- close() graceful shutdown ---


async def test_close_quits_smtp():
    """close() — 优雅关闭 SMTP 连接。"""
    sender = _make_sender()
    mock_smtp = AsyncMock()
    sender._smtp = mock_smtp

    await sender.close()
    mock_smtp.quit.assert_awaited_once()
    assert sender._smtp is None


async def test_close_idempotent():
    """close() — 无连接时调用不报错。"""
    sender = _make_sender()
    await sender.close()
    assert sender._smtp is None
