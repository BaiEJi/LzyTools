"""basic_tool.email.task 的单元测试。

覆盖 send_email_task 的正常/异常路径、参数传递、@task 注册，
以及 setup_email_worker 工厂的 on_startup/on_shutdown 回调。
"""
from unittest.mock import AsyncMock, patch

import pytest

from basic_tool.email.config import EmailConfig
from basic_tool.email.models import Email, SendResult
from basic_tool.email.sender import SmtpSender
from basic_tool.email.task import send_email_task, setup_email_worker
from basic_tool.task_queue.task import get_registry, validate_task_name


def _make_config(**overrides) -> EmailConfig:
    """创建测试用 EmailConfig。"""
    defaults = dict(
        host="smtp.example.com",
        username="user@example.com",
        password="secret",
    )
    defaults.update(overrides)
    return EmailConfig(**defaults)


# --- send_email_task 注册 ---


def test_send_email_task_registered():
    """send_email_task 通过 @task 注册到全局注册表。"""
    assert validate_task_name("send_email_task")
    assert "send_email_task" in get_registry()


def test_send_email_task_is_module_level():
    """send_email_task 是模块级函数（ARQ 序列化要求）。"""
    assert send_email_task.__module__ == "basic_tool.email.task"


# --- send_email_task 正常路径 ---


async def test_send_email_task_basic():
    """send_email_task 从 ctx 获取 sender 并发送邮件。"""
    mock_sender = AsyncMock()
    expected = SendResult(success=True, message_id="abc-123", recipient="a@b.com")
    mock_sender.send.return_value = expected
    ctx = {"email_sender": mock_sender}

    result = await send_email_task(ctx, to=["a@b.com"], subject="test", body="hello")

    assert result is expected
    mock_sender.send.assert_awaited_once()
    sent_email: Email = mock_sender.send.call_args.args[0]
    assert sent_email.to == ["a@b.com"]
    assert sent_email.subject == "test"
    assert sent_email.body == "hello"
    assert sent_email.content_type == "text/plain"
    assert sent_email.cc is None
    assert sent_email.bcc is None


async def test_send_email_task_html_content():
    """send_email_task 支持 text/html content_type。"""
    mock_sender = AsyncMock()
    mock_sender.send.return_value = SendResult(success=True)
    ctx = {"email_sender": mock_sender}

    await send_email_task(
        ctx,
        to=["x@y.com"],
        subject="html",
        body="<h1>Hi</h1>",
        content_type="text/html",
    )

    sent_email: Email = mock_sender.send.call_args.args[0]
    assert sent_email.content_type == "text/html"


async def test_send_email_task_with_cc_bcc():
    """send_email_task 传递 cc/bcc 参数到 Email 模型。"""
    mock_sender = AsyncMock()
    mock_sender.send.return_value = SendResult(success=True)
    ctx = {"email_sender": mock_sender}

    await send_email_task(
        ctx,
        to=["to@example.com"],
        subject="cc/bcc test",
        body="body",
        cc=["cc1@example.com", "cc2@example.com"],
        bcc=["bcc@example.com"],
    )

    sent_email: Email = mock_sender.send.call_args.args[0]
    assert sent_email.cc == ["cc1@example.com", "cc2@example.com"]
    assert sent_email.bcc == ["bcc@example.com"]
    assert sent_email.all_recipients == [
        "to@example.com",
        "cc1@example.com",
        "cc2@example.com",
        "bcc@example.com",
    ]


# --- send_email_task 异常路径 ---


async def test_send_email_task_missing_sender():
    """ctx 中缺少 email_sender 时抛出 RuntimeError。"""
    ctx = {}

    with pytest.raises(RuntimeError, match="email_sender not found in worker context"):
        await send_email_task(ctx, to=["a@b.com"], subject="test", body="hello")


async def test_send_email_task_sender_is_none():
    """ctx["email_sender"] 为 None 时抛出 RuntimeError。"""
    ctx = {"email_sender": None}

    with pytest.raises(RuntimeError, match="email_sender not found in worker context"):
        await send_email_task(ctx, to=["a@b.com"], subject="test", body="hello")


# --- setup_email_worker ---


async def test_setup_email_worker_on_startup():
    """on_startup 创建 SmtpSender 并注入 ctx["email_sender"]。"""
    config = _make_config()
    on_startup, _ = setup_email_worker(config)
    ctx: dict = {}

    await on_startup(ctx)

    assert "email_sender" in ctx
    assert isinstance(ctx["email_sender"], SmtpSender)
    assert ctx["email_sender"].config is config


async def test_setup_email_worker_on_shutdown():
    """on_shutdown 从 ctx 取出 sender 并调用 close()。"""
    config = _make_config()
    on_startup, on_shutdown = setup_email_worker(config)
    ctx: dict = {}

    await on_startup(ctx)
    sender = ctx["email_sender"]
    with patch.object(sender, "close", new_callable=AsyncMock) as mock_close:
        await on_shutdown(ctx)
        mock_close.assert_awaited_once()


async def test_setup_email_worker_on_shutdown_no_sender():
    """on_shutdown 在 ctx 无 sender 时不报错。"""
    config = _make_config()
    _, on_shutdown = setup_email_worker(config)
    ctx: dict = {}

    await on_shutdown(ctx)


async def test_setup_email_worker_full_lifecycle():
    """完整生命周期：startup → send → shutdown。"""
    config = _make_config()
    on_startup, on_shutdown = setup_email_worker(config)
    ctx: dict = {}

    await on_startup(ctx)
    real_sender = ctx["email_sender"]
    # 用 mock 替换 send 方法避免真实 SMTP 连接
    real_sender.send = AsyncMock(return_value=SendResult(success=True, message_id="m1"))

    result = await send_email_task(ctx, to=["a@b.com"], subject="s", body="b")

    assert result.success
    assert result.message_id == "m1"
    real_sender.send.assert_awaited_once()

    with patch.object(real_sender, "close", new_callable=AsyncMock) as mock_close:
        await on_shutdown(ctx)
        mock_close.assert_awaited_once()


def test_setup_email_worker_returns_two_callables():
    """setup_email_worker 返回 (on_startup, on_shutdown) 二元组。"""
    config = _make_config()
    result = setup_email_worker(config)

    assert isinstance(result, tuple)
    assert len(result) == 2
    on_startup, on_shutdown = result
    assert callable(on_startup)
    assert callable(on_shutdown)
