# Learnings

## 2026-06-13 Session Start

### Project Conventions
- Logging format: `logger.info("msg | key={}", val)` with `|` separator
- `basic_tool/__init__.py` is docstring-only — NO import statements
- Pydantic BaseModel for config, dataclass for simple data containers
- Tests use pytest + pytest-asyncio with `asyncio_mode="auto"`
- `from __future__ import annotations` used in most modules

### Critical Design Constraints
- `aiosmtplib.SMTPMessage` does NOT exist — must use stdlib `email.mime.*`
- `send_message()` returns `tuple[dict, str]` — message_id is the SECOND element
- BCC must NOT appear in MIME headers — only passed to `send_message(recipients=...)`
- `autoescape=False` for Jinja2 Environment
- `dataclasses.field(default_factory=list)` for Email list fields — NOT Pydantic v2 canonical

## Scope Fidelity Check (F4) — 2026-06-13

- All 7 tasks (T1-T7) verified 1:1 compliant against plan spec
- All 14 guardrails (G1-G14) verified compliant
- `_build_message()` correctly uses stdlib `email.mime.*` — MIMEMultipart, MIMEText, MIMEImage, MIMEBase
- BCC privacy: not in MIME headers, confirmed via test and code review
- `basic_tool/__init__.py` docstring-only update — zero import statements
- Logging uses `|` separator format throughout all email module files
- Parallel module implementations share working tree but email changes are isolated
- pyproject.toml has extra deps (argon2-cffi, cryptography, aiofiles) from other modules — not email contamination
- `--import-mode=importlib` added to pytest config (shared infra change)
