"""邮件异步任务 — @task 集成。

提供模块级 @task 装饰的 send_email_task 函数，通过 ARQ 任务队列异步发送邮件。
setup_email_worker() 工厂返回 on_startup/on_shutdown 回调，将 SmtpSender 注入 Worker 上下文。
"""
from __future__ import annotations

from typing import Callable

from basic_tool.email.config import EmailConfig
from basic_tool.email.models import Email, SendResult
from basic_tool.email.sender import EmailSender, SmtpSender
from basic_tool.task_queue.task import task


@task()
async def send_email_task(
    ctx: dict,
    to: list[str],
    subject: str,
    body: str,
    content_type: str = "text/plain",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> SendResult:
    """异步发送邮件任务。

    从 Worker 上下文中获取 EmailSender 实例，构造 Email 模型并发送。
    通过 @task 装饰器注册到 ARQ 任务注册表，可经由任务队列异步执行。

    Args:
        ctx: ARQ Worker 上下文字典，必须包含 "email_sender" 键。
        to: 收件人地址列表。
        subject: 邮件主题。
        body: 邮件正文。
        content_type: 正文类型，默认 "text/plain"。
        cc: 抄送地址列表，可选。
        bcc: 密送地址列表，可选。

    Returns:
        SendResult: 邮件发送结果。

    Raises:
        RuntimeError: 上下文中缺少 "email_sender" 时抛出。
    """
    sender: EmailSender | None = ctx.get("email_sender")
    if sender is None:
        raise RuntimeError("email_sender not found in worker context")

    email = Email(
        to=to,
        subject=subject,
        body=body,
        content_type=content_type,
        cc=cc,
        bcc=bcc,
    )
    return await sender.send(email)


def setup_email_worker(email_config: EmailConfig) -> tuple[Callable, Callable]:
    """创建邮件 Worker 的启动/关闭回调。

    返回 (on_startup, on_shutdown) 回调对：
    - on_startup: 创建 SmtpSender 并注入 ctx["email_sender"]
    - on_shutdown: 从 ctx 取出 sender 并关闭连接

    用于 WorkerRunner 或 build_settings() 的 on_startup/on_shutdown 参数。

    Args:
        email_config: SMTP 邮件配置。

    Returns:
        (on_startup, on_shutdown) 异步回调元组。

    Examples:
        config = EmailConfig(host="smtp.example.com", username="u", password="p")
        on_startup, on_shutdown = setup_email_worker(config)
        runner = WorkerRunner(task_config, on_startup=on_startup, on_shutdown=on_shutdown)
    """

    async def on_startup(ctx: dict) -> None:
        """Worker 启动：创建 SmtpSender 并注入上下文。"""
        ctx["email_sender"] = SmtpSender(email_config)

    async def on_shutdown(ctx: dict) -> None:
        """Worker 关闭：关闭 SMTP 连接。"""
        sender = ctx.get("email_sender")
        if sender is not None:
            await sender.close()

    return on_startup, on_shutdown
