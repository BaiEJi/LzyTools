# basic_tool.email — 异步邮件发送模块

基于 `aiosmtplib` 的异步邮件发送封装，提供统一的发送抽象层、Jinja2 模板渲染、批量发送和测试模式。

## 依赖

- `aiosmtplib>=3.0.0` — 异步 SMTP 客户端
- `jinja2>=3.1.0` — 邮件模板渲染（可选，仅 `TemplateRenderer` 使用）
- `pydantic>=2.0.0` — 配置校验与数据模型

## 模块结构

```
basic_tool/email/
├── __init__.py          # 统一导出
├── config.py            # EmailConfig 配置类
├── exceptions.py        # EmailError / SendError / TemplateError
├── models.py            # Email / Attachment / InlineImage / SendResult
├── sender.py            # EmailSender ABC + SmtpSender 实现
├── dry_run.py           # DryRunSender 测试模式
├── template.py          # TemplateRenderer 模板渲染（单独导入）
└── task.py              # send_email_task / setup_email_worker（@task 集成）
```

## API 文档

---

### `config.py` — EmailConfig

```python
class EmailConfig(BaseModel):
    """SMTP 邮件发送配置。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `host` | `str` | — (必填) | SMTP 服务器地址 |
| `port` | `int` | `587` | SMTP 端口（587=STARTTLS，465=SSL） |
| `username` | `str` | — (必填) | SMTP 用户名 |
| `password` | `str` | — (必填) | SMTP 密码 |
| `sender` | `str` | `""` | 发件人地址（空则用 username） |
| `sender_name` | `str` | `""` | 发件人显示名 |
| `use_tls` | `bool` | `True` | 是否使用 STARTTLS |
| `use_ssl` | `bool` | `False` | 是否使用 SSL（与 use_tls 互斥） |
| `timeout` | `float` | `30.0` | 连接超时（秒） |
| `template_dir` | `str` | `""` | Jinja2 模板文件目录路径 |
| `bulk_batch_size` | `int` | `50` | 批量发送每批数量 |

| 属性 | 返回类型 | 说明 |
|---|---|---|
| `from_address` | `str` | 发件人完整地址。有 sender_name 时格式为 `Name <addr>`，否则返回 sender 或 username |

---

### `models.py` — Email / Attachment / InlineImage / SendResult

#### Attachment

```python
class Attachment(BaseModel):
    """邮件附件。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `filename` | `str` | — (必填) | 文件名（如 `"report.pdf"`） |
| `content` | `bytes` | — (必填) | 文件内容 |
| `content_type` | `str` | `"application/octet-stream"` | MIME 类型 |

#### InlineImage

```python
class InlineImage(BaseModel):
    """内嵌图片（HTML 中通过 CID 引用）。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `cid` | `str` | — (必填) | Content-ID（HTML 中 `<img src="cid:xxx">`） |
| `content` | `bytes` | — (必填) | 图片内容 |
| `content_type` | `str` | `"image/png"` | MIME 类型 |

#### Email

```python
class Email(BaseModel):
    """邮件数据模型。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `to` | `str \| list[str]` | — (必填) | 收件人 |
| `cc` | `str \| list[str] \| None` | `None` | 抄送 |
| `bcc` | `str \| list[str] \| None` | `None` | 密送 |
| `subject` | `str` | — (必填，非空) | 主题 |
| `body` | `str` | — (必填) | 正文 |
| `content_type` | `str` | `"text/plain"` | 正文类型 |
| `attachments` | `list[Attachment]` | `[]` | 附件列表 |
| `inline_images` | `list[InlineImage]` | `[]` | 内嵌图片列表 |
| `headers` | `dict[str, str]` | `{}` | 自定义邮件头部 |
| `reply_to` | `str \| None` | `None` | 回复地址 |

**校验器：**
- `subject` 不能为空字符串
- `to` 不能为空

| 属性 | 返回类型 | 说明 |
|---|---|---|
| `to_list` | `list[str]` | 收件人列表（统一为 list） |
| `cc_list` | `list[str]` | 抄送列表 |
| `bcc_list` | `list[str]` | 密送列表 |
| `all_recipients` | `list[str]` | 所有收件人（to + cc + bcc） |

#### SendResult

```python
@dataclass
class SendResult:
    """邮件发送结果。"""
```

| 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `success` | `bool` | — (必填) | 是否发送成功 |
| `message_id` | `str` | `""` | SMTP 返回的 Message-ID |
| `error` | `str` | `""` | 错误信息（失败时） |
| `recipient` | `str` | `""` | 目标收件人 |

---

### `sender.py` — EmailSender (ABC) / SmtpSender

#### EmailSender

```python
class EmailSender(ABC):
    """邮件发送器抽象基类。"""
```

| 方法 | 签名 | 说明 |
|---|---|---|
| `send()` | `async (email: Email) -> SendResult` | 发送单封邮件（抽象方法） |
| `send_bulk()` | `async (emails: list[Email]) -> list[SendResult]` | 批量发送（默认逐封发送） |

#### SmtpSender

```python
class SmtpSender(EmailSender):
    """基于 aiosmtplib 的异步 SMTP 邮件发送器。"""
```

特性：持久连接复用（自动重连）、STARTTLS/SSL 支持、批量发送分批控制、完整日志记录。

| 方法 | 签名 | 说明 |
|---|---|---|
| `__init__()` | `(config: EmailConfig)` | 初始化 |
| `send()` | `async (email: Email) -> SendResult` | 发送单封邮件。SMTP 协议级错误返回 `SendResult(success=False)`，连接级错误抛出 `SendError` |
| `send_bulk()` | `async (emails: list[Email]) -> list[SendResult]` | 批量发送，按 `bulk_batch_size` 分批 |
| `close()` | `async () -> None` | 关闭 SMTP 连接 |

---

### `dry_run.py` — DryRunSender

```python
class DryRunSender(EmailSender):
    """测试模式发送器，不真实发送邮件。"""
```

适用于开发环境和 pytest 单元测试，将所有邮件记录到内存列表供断言。

| 方法/属性 | 签名 | 说明 |
|---|---|---|
| `send()` | `async (email: Email) -> SendResult` | 记录邮件（不发送），返回 `SendResult(success=True, message_id="dry-run-N")` |
| `sent_emails` | `list[Email]` (property) | 已发送的邮件列表（只读副本） |
| `sent_count` | `int` (property) | 已发送邮件数量 |
| `reset()` | `() -> None` | 清空已发送记录 |

---

### `template.py` — TemplateRenderer

**注意：** `TemplateRenderer` 需单独导入：`from basic_tool.email.template import TemplateRenderer`

```python
class TemplateRenderer:
    """Jinja2 邮件模板渲染器。"""
```

| 方法 | 签名 | 说明 |
|---|---|---|
| `__init__()` | `(template_dir: str)` | 初始化。jinja2 未安装时抛出 `ImportError`，目录不存在时抛出 `TemplateError` |
| `render()` | `(template_name: str, **context) -> tuple[str, str]` | 渲染模板，返回 `(html正文, 纯文本fallback)` |

---

### `exceptions.py` — 异常类型

| 异常 | 基类 | 说明 |
|---|---|---|
| `EmailError` | `Exception` | 邮件模块基础异常 |
| `SendError` | `EmailError` | 邮件发送失败。属性：`message`(str)、`original`(Exception \| None) |
| `TemplateError` | `EmailError` | 模板渲染失败（模板不存在、语法错误、变量缺失等） |

---

## 使用示例

### 基本发送

```python
from basic_tool.email import Email, EmailConfig, SmtpSender

config = EmailConfig(
    host="smtp.example.com",
    port=587,
    username="noreply@example.com",
    password="smtp-password",
    sender_name="My App",
)
sender = SmtpSender(config)

email = Email(
    to="user@example.com",
    subject="Welcome to My App",
    body="<h1>Hello!</h1><p>Welcome aboard.</p>",
    content_type="text/html",
)
result = await sender.send(email)
print(result.success, result.message_id)

await sender.close()
```

### 带附件和内嵌图片

```python
from basic_tool.email import Email, Attachment, InlineImage

# 附件
pdf_attachment = Attachment(
    filename="report.pdf",
    content=pdf_bytes,
    content_type="application/pdf",
)

# 内嵌图片（HTML 中用 cid:logo 引用）
logo = InlineImage(
    cid="logo",
    content=logo_png_bytes,
    content_type="image/png",
)

email = Email(
    to="user@example.com",
    subject="Monthly Report",
    body='<p>Please find the report attached.</p><img src="cid:logo">',
    content_type="text/html",
    attachments=[pdf_attachment],
    inline_images=[logo],
)
await sender.send(email)
```

### 模板渲染发送

```python
from basic_tool.email import Email, EmailConfig, SmtpSender
from basic_tool.email.template import TemplateRenderer

config = EmailConfig(
    host="smtp.example.com",
    username="noreply@example.com",
    password="smtp-password",
    template_dir="/app/templates/email",
)
sender = SmtpSender(config)

renderer = TemplateRenderer(config.template_dir)
html, plain = renderer.render("welcome.html", name="Alice", action_url="https://example.com/confirm")

email = Email(
    to="alice@example.com",
    subject="Welcome!",
    body=html,
    content_type="text/html",
)
await sender.send(email)
```

### 异步发送（@task 集成）

通过 `basic_tool.task_queue` 的 `@task` 装饰器将邮件发送注册为 ARQ 任务，
经 Redis 任务队列异步执行。`setup_email_worker()` 工厂返回启动/关闭回调，
自动将 `SmtpSender` 注入 Worker 上下文 `ctx["email_sender"]`。

```python
from basic_tool.email import EmailConfig, send_email_task, setup_email_worker
from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.worker import WorkerRunner

# 1. 配置邮件
email_config = EmailConfig(
    host="smtp.example.com",
    username="noreply@example.com",
    password="smtp-password",
)

# 2. 创建 Worker 回调（SmtpSender 在 startup 注入，shutdown 关闭连接）
on_startup, on_shutdown = setup_email_worker(email_config)

# 3. 启动 Worker（send_email_task 已通过 @task 自动注册）
task_config = TaskConfig()
runner = WorkerRunner(task_config, on_startup=on_startup, on_shutdown=on_shutdown)
await runner.run()
```

入队发送（生产者侧）：

```python
from basic_tool.task_queue.queue import TaskQueue

queue = TaskQueue(task_config)
await queue.enqueue(
    "send_email_task",
    to=["user@example.com"],
    subject="Welcome",
    body="<h1>Hello!</h1>",
    content_type="text/html",
)
```

| 函数 | 签名 | 说明 |
|---|---|---|
| `send_email_task()` | `async (ctx, to, subject, body, content_type="text/plain", cc=None, bcc=None) -> SendResult` | `@task` 装饰的模块级异步函数。从 `ctx["email_sender"]` 获取 sender，构造 Email 并发送。sender 缺失时抛 `RuntimeError` |
| `setup_email_worker()` | `(email_config: EmailConfig) -> tuple[on_startup, on_shutdown]` | 返回回调对：startup 创建 `SmtpSender` 注入 ctx；shutdown 调用 `sender.close()` |

---

### 批量发送

```python
emails = [
    Email(to=f"user{i}@example.com", subject="Notification", body=f"Hello user {i}!")
    for i in range(100)
]
results = await sender.send_bulk(emails)
success_count = sum(1 for r in results if r.success)
print(f"Sent {success_count}/{len(results)}")
```

### DryRunSender 测试

```python
import pytest
from basic_tool.email import DryRunSender, Email

@pytest.fixture
def email_sender():
    return DryRunSender()

async def test_welcome_email(email_sender: DryRunSender):
    email = Email(to="test@example.com", subject="Welcome", body="Hello!")
    result = await email_sender.send(email)

    assert result.success
    assert email_sender.sent_count == 1
    assert email_sender.sent_emails[0].subject == "Welcome"
    assert email_sender.sent_emails[0].to == "test@example.com"

async def test_bulk_send(email_sender: DryRunSender):
    emails = [
        Email(to=f"user{i}@example.com", subject=f"Hi {i}", body="Hello!")
        for i in range(5)
    ]
    results = await email_sender.send_bulk(emails)
    assert all(r.success for r in results)
    assert email_sender.sent_count == 5
```

### FastAPI 集成

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from basic_tool.email import Email, EmailConfig, SmtpSender

email_config = EmailConfig(
    host="smtp.example.com",
    username="noreply@example.com",
    password="smtp-password",
    template_dir="/app/templates/email",
)
email_sender = SmtpSender(email_config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await email_sender.close()

app = FastAPI(lifespan=lifespan)

@app.post("/send-reset-password")
async def send_reset_password(email_addr: str, token: str):
    email = Email(
        to=email_addr,
        subject="Password Reset",
        body=f"<p>Click <a href='https://example.com/reset?token={token}'>here</a> to reset.</p>",
        content_type="text/html",
    )
    result = await email_sender.send(email)
    return {"success": result.success, "message_id": result.message_id}
```
