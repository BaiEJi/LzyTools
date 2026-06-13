# Decisions

## 2026-06-13 Session Start

### Module Architecture
- 7 source files under `basic_tool/email/`
- Mixin pattern NOT needed — simple module with flat files
- `EmailSender` ABC with `SmtpSender` and `DryRunSender` implementations
- `TemplateRenderer` imported separately from `basic_tool.email.template` (NOT in `__init__.py` exports)

### MIME Construction
- Use `MIMEMultipart("mixed")` for attachments
- Use `MIMEMultipart("related")` for inline images
- Use `MIMEText(body, subtype)` for text/html body
- `_build_message()` returns stdlib `email.message.EmailMessage` / `MIMEMultipart`
