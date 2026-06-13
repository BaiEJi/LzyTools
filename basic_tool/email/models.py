"""邮件相关数据模型。

Email：邮件数据模型，包含收件人、主题、正文、附件等。
Attachment / InlineImage：附件和内嵌图片的结构化表示。
SendResult：发送结果。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, field_validator


class Attachment(BaseModel):
    """邮件附件。

    Attributes:
        filename: 文件名（如 "report.pdf"）。
        content: 文件内容（bytes）。
        content_type: MIME 类型（如 "application/pdf"），可选。
    """
    model_config = {"arbitrary_types_allowed": True}

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class InlineImage(BaseModel):
    """内嵌图片（HTML 中通过 CID 引用）。

    Attributes:
        cid: Content-ID（HTML 中 <img src="cid:xxx"> 的 xxx 部分）。
        content: 图片内容（bytes）。
        content_type: MIME 类型（如 "image/png"）。
    """
    model_config = {"arbitrary_types_allowed": True}

    cid: str
    content: bytes
    content_type: str = "image/png"


class Email(BaseModel):
    """邮件数据模型。

    支持纯文本/HTML 正文、附件、内嵌图片、自定义头部。

    Examples:
        email = Email(
            to="user@example.com",
            subject="Welcome",
            body="<h1>Hello</h1>",
            content_type="text/html",
        )
    """
    # 收件人（单个字符串或列表）
    to: str | list[str]
    # 抄送
    cc: str | list[str] | None = None
    # 密送
    bcc: str | list[str] | None = None
    # 主题
    subject: str
    # 正文
    body: str
    # 正文类型："text/plain" 或 "text/html"
    content_type: str = "text/plain"
    # 附件列表
    attachments: list[Attachment] = field(default_factory=list)
    # 内嵌图片列表
    inline_images: list[InlineImage] = field(default_factory=list)
    # 自定义邮件头部
    headers: dict[str, str] = field(default_factory=dict)
    # 回复地址
    reply_to: str | None = None

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        """主题不能为空。"""
        if not v or not v.strip():
            raise ValueError("subject must not be empty")
        return v.strip()

    @field_validator("to")
    @classmethod
    def to_not_empty(cls, v: str | list[str]) -> str | list[str]:
        """收件人不能为空。"""
        if isinstance(v, str):
            if not v or not v.strip():
                raise ValueError("to must not be empty")
            return v.strip()
        if not v:
            raise ValueError("to must not be empty")
        return [addr.strip() for addr in v if addr.strip()]

    @property
    def to_list(self) -> list[str]:
        """收件人列表（统一为 list）。"""
        if isinstance(self.to, str):
            return [self.to]
        return self.to

    @property
    def cc_list(self) -> list[str]:
        """抄送列表。"""
        if self.cc is None:
            return []
        if isinstance(self.cc, str):
            return [self.cc]
        return self.cc

    @property
    def bcc_list(self) -> list[str]:
        """密送列表。"""
        if self.bcc is None:
            return []
        if isinstance(self.bcc, str):
            return [self.bcc]
        return self.bcc

    @property
    def all_recipients(self) -> list[str]:
        """所有收件人（to + cc + bcc）。"""
        return self.to_list + self.cc_list + self.bcc_list


@dataclass
class SendResult:
    """邮件发送结果。

    Attributes:
        success: 是否发送成功。
        message_id: SMTP 返回的 Message-ID（成功时）。
        error: 错误信息（失败时）。
        recipient: 目标收件人。
    """
    success: bool
    message_id: str = ""
    error: str = ""
    recipient: str = ""
