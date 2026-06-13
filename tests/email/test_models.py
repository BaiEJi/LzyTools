"""basic_tool.email.models 的单元测试。"""
import pytest
from pydantic import ValidationError

from basic_tool.email.models import Attachment, Email, InlineImage, SendResult


def test_email_basic_creation():
    """测试 Email 基本创建 — 验证 to、subject、body 正确设置。"""
    email = Email(to="user@example.com", subject="Hello", body="World")
    assert email.to == "user@example.com"
    assert email.subject == "Hello"
    assert email.body == "World"
    assert email.content_type == "text/plain"


def test_email_to_as_list():
    """测试 Email to 为列表时 to_list 返回正确列表。"""
    email = Email(
        to=["a@example.com", "b@example.com"],
        subject="Test",
        body="body",
    )
    assert email.to_list == ["a@example.com", "b@example.com"]


def test_email_empty_subject_raises():
    """测试空主题引发 ValidationError。"""
    with pytest.raises(ValidationError, match="subject must not be empty"):
        Email(to="user@example.com", subject="", body="body")


def test_email_empty_to_raises():
    """测试空收件人引发 ValidationError。"""
    with pytest.raises(ValidationError, match="to must not be empty"):
        Email(to="", subject="Test", body="body")


def test_email_all_recipients():
    """测试 all_recipients 合并 to + cc + bcc。"""
    email = Email(
        to="to@example.com",
        cc="cc@example.com",
        bcc="bcc@example.com",
        subject="Test",
        body="body",
    )
    assert email.all_recipients == [
        "to@example.com",
        "cc@example.com",
        "bcc@example.com",
    ]


def test_attachment_creation():
    """测试 Attachment 创建 — 验证 filename、content、content_type。"""
    att = Attachment(filename="report.pdf", content=b"%PDF-1.4")
    assert att.filename == "report.pdf"
    assert att.content == b"%PDF-1.4"
    assert att.content_type == "application/octet-stream"


def test_inline_image_creation():
    """测试 InlineImage 创建 — 验证 cid、content、content_type。"""
    img = InlineImage(cid="logo", content=b"\x89PNG")
    assert img.cid == "logo"
    assert img.content == b"\x89PNG"
    assert img.content_type == "image/png"
