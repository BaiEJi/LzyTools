"""邮件发送器 — ABC 接口与 SMTP 实现。

提供 EmailSender 抽象基类和基于 aiosmtplib 的 SmtpSender 实现。
SmtpSender 维护单条持久 SMTP 连接，自动重连，使用 asyncio.Lock 保证并发安全。
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from loguru import logger

from basic_tool.email.config import EmailConfig
from basic_tool.email.exceptions import SendError
from basic_tool.email.models import Email, SendResult


class EmailSender(ABC):
    """邮件发送器抽象基类。

    所有邮件发送实现必须继承此类并实现 send() 方法。
    send_bulk() 提供默认的逐封发送实现。
    """

    @abstractmethod
    async def send(self, email: Email) -> SendResult:
        """发送单封邮件。

        Args:
            email: 邮件数据模型，包含收件人、主题、正文等。

        Returns:
            SendResult: 发送结果（成功/失败、message_id、错误信息）。

        Raises:
            SendError: 连接级别错误（网络不可达、认证失败等）。
        """
        ...

    async def send_bulk(self, emails: list[Email]) -> list[SendResult]:
        """批量发送邮件。

        默认实现逐封调用 send()。子类可覆盖以提供更高效的批量发送。

        Args:
            emails: 待发送邮件列表。

        Returns:
            list[SendResult]: 与输入顺序对应的发送结果列表。
        """
        results: list[SendResult] = []
        for email in emails:
            result = await self.send(email)
            results.append(result)
        return results


class SmtpSender(EmailSender):
    """基于 aiosmtplib 的 SMTP 邮件发送器。

    维护单条持久 SMTP 连接，使用 asyncio.Lock 保证并发安全。
    连接断开时自动重连。

    Attributes:
        config: SMTP 配置。
    """

    def __init__(self, config: EmailConfig) -> None:
        """初始化 SMTP 发送器。

        Args:
            config: SMTP 配置（主机、端口、认证信息等）。
        """
        self.config = config
        self._smtp: aiosmtplib.SMTP | None = None
        self._lock = asyncio.Lock()

    def _build_message(self, email: Email) -> MIMEMultipart:
        """将 Email 模型转换为 MIME 邮件消息。

        使用标准库 email.mime.* 构建 MIME 树，不依赖 aiosmtplib.SMTPMessage。

        结构：
        - 无内嵌图片：root(mixed) -> body + attachments
        - 有内嵌图片：root(mixed) -> related(body + inline_images) + attachments

        BCC 地址不会出现在 MIME 头部中，仅在 send() 时通过 recipients 参数传递。

        Args:
            email: 邮件数据模型。

        Returns:
            MIMEMultipart: 构建好的 MIME 消息。
        """
        subtype = "html" if email.content_type == "text/html" else "plain"

        root = MIMEMultipart("mixed")
        root["From"] = self.config.from_address
        root["To"] = ", ".join(email.to_list)
        root["Subject"] = email.subject

        if email.cc_list:
            root["Cc"] = ", ".join(email.cc_list)

        if email.reply_to:
            root["Reply-To"] = email.reply_to

        for key, value in email.headers.items():
            root[key] = value

        body_part = MIMEText(email.body, subtype)

        if email.inline_images:
            related = MIMEMultipart("related")
            related.attach(body_part)
            for img in email.inline_images:
                mime_img = MIMEImage(img.content, _subtype=img.content_type.split("/")[-1])
                mime_img.add_header("Content-ID", f"<{img.cid}>")
                mime_img.add_header("Content-Disposition", "inline", filename=img.cid)
                related.attach(mime_img)
            root.attach(related)
        else:
            root.attach(body_part)

        for att in email.attachments:
            maintype, _, subtype_part = att.content_type.partition("/")
            if not subtype_part:
                maintype, subtype_part = "application", "octet-stream"
            mime_att = MIMEBase(maintype, subtype_part)
            mime_att.set_payload(att.content)
            encoders.encode_base64(mime_att)
            mime_att.add_header("Content-Disposition", "attachment", filename=att.filename)
            root.attach(mime_att)

        return root

    async def _ensure_connection(self) -> aiosmtplib.SMTP:
        """确保 SMTP 连接可用，断开时自动重连。

        Returns:
            aiosmtplib.SMTP: 已连接的 SMTP 客户端实例。

        Raises:
            SendError: 连接或认证失败。
        """
        if self._smtp is not None:
            try:
                if getattr(self._smtp, "is_connected", False):
                    return self._smtp
            except Exception:
                self._smtp = None

        smtp = aiosmtplib.SMTP(
            hostname=self.config.host,
            port=self.config.port,
            timeout=self.config.timeout,
            use_tls=self.config.use_ssl,
        )
        try:
            await smtp.connect()
            if self.config.use_tls and not self.config.use_ssl:
                await smtp.starttls()
            if self.config.username:
                await smtp.login(self.config.username, self.config.password)
            self._smtp = smtp
            logger.info("smtp connected | host={} port={}", self.config.host, self.config.port)
            return self._smtp
        except Exception as e:
            self._smtp = None
            raise SendError(f"SMTP connection failed: {e}", original=e) from e

    async def send(self, email: Email) -> SendResult:
        """发送单封邮件。

        通过持久的 SMTP 连接发送邮件，使用 asyncio.Lock 保证并发安全。
        BCC 地址不会出现在邮件头部，但会包含在实际收件人列表中。

        Args:
            email: 邮件数据模型。

        Returns:
            SendResult: 发送结果。

        Raises:
            SendError: 连接级别错误（网络中断等）。
        """
        recipients = email.all_recipients
        msg = self._build_message(email)
        async with self._lock:
            try:
                smtp = await self._ensure_connection()
                result = await smtp.send_message(msg, recipients=recipients)
                message_id = result[1] if isinstance(result, tuple) else ""
                logger.info(
                    "email sent | to={} subject={} message_id={}",
                    email.to_list,
                    email.subject,
                    message_id,
                )
                return SendResult(
                    success=True,
                    message_id=message_id,
                    recipient=", ".join(email.to_list),
                )
            except aiosmtplib.SMTPException as e:
                logger.error(
                    "smtp rejection | to={} subject={} error={}",
                    email.to_list,
                    email.subject,
                    str(e),
                )
                return SendResult(
                    success=False,
                    error=str(e),
                    recipient=", ".join(email.to_list),
                )
            except SendError:
                raise
            except Exception as e:
                logger.error(
                    "send failed | to={} subject={} error={}",
                    email.to_list,
                    email.subject,
                    str(e),
                )
                raise SendError(f"Failed to send email: {e}", original=e) from e

    async def send_bulk(self, emails: list[Email]) -> list[SendResult]:
        """批量发送邮件，按 bulk_batch_size 分批。

        Args:
            emails: 待发送邮件列表。

        Returns:
            list[SendResult]: 与输入顺序对应的发送结果列表。
        """
        results: list[SendResult] = []
        batch_size = self.config.bulk_batch_size
        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            for email in batch:
                result = await self.send(email)
                results.append(result)
        return results

    async def close(self) -> None:
        """优雅关闭 SMTP 连接。"""
        if self._smtp is not None:
            try:
                await self._smtp.quit()
            except Exception:
                pass
            finally:
                self._smtp = None
            logger.info("smtp connection closed")
