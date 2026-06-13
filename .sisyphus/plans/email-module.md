# basic_tool.email Module Implementation

## TL;DR

> **Quick Summary**: Implement `basic_tool.email` — an async email sending module for the basic_tool SDK, with SMTP support (aiosmtplib), Jinja2 template rendering, DryRunSender for testing, and full test coverage.
> 
> **Deliverables**:
> - 7 source files under `basic_tool/email/`
> - 1 README.md documenting public APIs
> - 4 test files under `tests/email/` (24+ test cases)
> - Updated `pyproject.toml` with new dependencies
> - Updated `basic_tool/__init__.py` docstring
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: T1 → T3 → T4 → T5 → T6 → T7 → F1-F4

---

## Context

### Original Request
Implement the `basic_tool.email` module based on the design document at `doc/basic_tool_email_design.md`.

### Interview Summary
**Key Discussions**:
- User provided a complete design doc with all code, tests, and file structure
- Module provides async email sending, template rendering, and test mode
- Direct translation from spec with one critical fix (MIME construction)

**Research Findings**:
- `aiosmtplib.SMTPMessage` does NOT exist — must use stdlib `email.mime.*` classes
- `send_message()` returns `tuple[dict, str]` — message_id is the second element
- Project uses pytest + pytest-asyncio with `asyncio_mode="auto"`
- `basic_tool/__init__.py` is docstring-only — update docstring, do NOT add imports
- Logging format: `logger.info("msg | key={}", val)` with `|` separator

### Metis Review
**Identified Gaps** (addressed):
- `aiosmtplib.SMTPMessage` doesn't exist → Rewritten using `MIMEMultipart`/`MIMEText`/`MIMEImage`/`MIMEBase`
- `send_message()` return type → Extract message_id from tuple's second element
- BCC privacy → Added guardrail: BCC must NOT appear in MIME headers, added test case
- `jinja2` as required vs optional → Kept in required deps (design intent); `try/except` guard is defensive coding
- SmtpSender mock strategy → Specified `AsyncMock` + `patch("basic_tool.email.sender.aiosmtplib.SMTP")`
- Missing test cases → Added BCC privacy test, bulk empty test, MIME structure test

---

## Work Objectives

### Core Objective
Add a production-ready async email sending module to basic_tool SDK, following existing patterns.

### Concrete Deliverables
- `basic_tool/email/config.py` — EmailConfig Pydantic model
- `basic_tool/email/exceptions.py` — EmailError, SendError, TemplateError
- `basic_tool/email/models.py` — Email, Attachment, InlineImage, SendResult
- `basic_tool/email/sender.py` — EmailSender ABC + SmtpSender (aiosmtplib)
- `basic_tool/email/dry_run.py` — DryRunSender for testing
- `basic_tool/email/template.py` — TemplateRenderer (Jinja2)
- `basic_tool/email/__init__.py` — Flat exports
- `basic_tool/email/README.md` — Module documentation
- `tests/email/__init__.py` — Empty init
- `tests/email/test_models.py` — Model tests (cases 1-7)
- `tests/email/test_dry_run.py` — DryRunSender tests (cases 8-11)
- `tests/email/test_sender.py` — SmtpSender tests (cases 12-19)
- `tests/email/test_template.py` — Template tests (cases 20-23)
- Updated `pyproject.toml` — aiosmtplib + jinja2 deps
- Updated `basic_tool/__init__.py` — docstring update only

### Definition of Done
- [ ] `pytest tests/email/ -v` passes all tests
- [ ] `pytest tests/ -v` passes (no regressions)
- [ ] `python3 -c "from basic_tool.email import Email, EmailConfig, SmtpSender, DryRunSender"` succeeds
- [ ] No real SMTP server needed for tests

### Must Have
- All 7 source files exactly matching design doc's public API surface
- `_build_message()` rewritten using stdlib `email.mime.*` (NOT `aiosmtplib.SMTPMessage`)
- All 24+ test cases passing
- `basic_tool/email/README.md` documenting all public APIs
- Logging follows project format: `logger.info("msg | key={}", val)`

### Must NOT Have (Guardrails)
- G1: DO NOT modify `tests/conftest.py` — email fixtures stay in `tests/email/`
- G2: DO NOT add real SMTP server to test infrastructure — mock only
- G3: DO NOT add retry/backoff logic — not in design
- G4: DO NOT add connection pooling — single persistent connection only
- G5: DO NOT add `__aenter__`/`__aexit__` — only `close()`
- G6: DO NOT add email queue/scheduling
- G7: DO NOT add email address format validation — only "not empty"
- G8: DO NOT add `html2text`/`beautifulsoup4` deps — regex only
- G9: DO NOT modify files under `basic_tool/` outside `email/` except `__init__.py` docstring
- G10: DO NOT add import statements to `basic_tool/__init__.py` — docstring only
- G11: DO NOT use `aiosmtplib.SMTPMessage` — it does NOT exist
- G12: DO NOT add BCC to MIME message headers — BCC only in `send_message(recipients=...)`
- G13: Every method MUST have a docstring
- G14: Logging MUST use `|` separator format

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio)
- **Automated tests**: YES (tests alongside each module)
- **Framework**: pytest with asyncio_mode="auto"
- **Test command**: `pytest tests/email/ -v`

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module import**: Use Bash — `python3 -c "from basic_tool.email import ..."`
- **Tests**: Use Bash — `pytest tests/email/ -v`
- **Linter**: Use Bash — `python3 -m py_compile basic_tool/email/*.py`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation, all parallel):
├── T1: pyproject.toml + uv sync [quick]
├── T2: config.py + exceptions.py [quick]
└── T3: models.py + tests/test_models.py [quick]

Wave 2 (After Wave 1 — core modules, MAX PARALLEL):
├── T4: sender.py + tests/test_sender.py (depends: T1, T2, T3) [deep]
├── T5: dry_run.py + tests/test_dry_run.py (depends: T2, T3) [unspecified-low]
└── T6: template.py + tests/test_template.py (depends: T2) [unspecified-low]

Wave 3 (After Wave 2 — integration + docs):
└── T7: __init__.py + README.md + basic_tool/__init__.py update (depends: T4, T5, T6) [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T3 → T4 → T7 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 1 and Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1   | —         | T4     | 1    |
| T2   | —         | T4, T5, T6 | 1 |
| T3   | —         | T4, T5  | 1    |
| T4   | T1, T2, T3 | T7     | 2    |
| T5   | T2, T3    | T7     | 2    |
| T6   | T2        | T7     | 2    |
| T7   | T4, T5, T6 | F1-F4 | 3    |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 3 tasks — T4 → `deep`, T5 → `unspecified-low`, T6 → `unspecified-low`
- **Wave 3**: 1 task — T7 → `quick`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Add aiosmtplib + jinja2 Dependencies

  **What to do**:
  - Edit `pyproject.toml` to add `"aiosmtplib>=3.0.0"` and `"jinja2>=3.1.0"` to the `dependencies` array
  - Run `uv sync` to install the new dependencies
  - Verify both packages are importable

  **Must NOT do**:
  - Do not modify any other dependency entries
  - Do not add any optional dependency groups for email

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single config file edit + dependency install
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - N/A — trivial task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3)
  - **Blocks**: T4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pyproject.toml:10-23` — Current dependencies section. Add new entries following existing format.

  **WHY Each Reference Matters**:
  - The pyproject.toml shows exactly where to insert new dependencies (after existing entries in the `dependencies` array)

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: Dependencies installed and importable
    Tool: Bash
    Preconditions: pyproject.toml updated, uv sync completed
    Steps:
      1. Run: python3 -c "import aiosmtplib; print(aiosmtplib.__version__)"
      2. Run: python3 -c "import jinja2; print(jinja2.__version__)"
    Expected Result: Both commands succeed and print version strings
    Failure Indicators: ImportError, ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-1-deps-install.txt

  Scenario: Existing tests unaffected
    Tool: Bash
    Preconditions: Dependencies installed
    Steps:
      1. Run: pytest tests/redis/ tests/logger/ -v --tb=short
    Expected Result: All existing tests pass (same as before dependency change)
    Failure Indicators: Any test failure or import error
    Evidence: .sisyphus/evidence/task-1-existing-tests.txt
  ```

  **Commit**: YES
  - Message: `feat(email): add aiosmtplib and jinja2 dependencies`
  - Files: `pyproject.toml`, `uv.lock`
  - Pre-commit: `python3 -c "import aiosmtplib; import jinja2"`

- [x] 2. Implement config.py + exceptions.py

  **What to do**:
  - Create `basic_tool/email/` directory (with empty `__init__.py` placeholder for now)
  - Create `basic_tool/email/config.py` — EmailConfig Pydantic BaseModel with all fields from design doc section 3.1, including `from_address` property
  - Create `basic_tool/email/exceptions.py` — EmailError base, SendError(with original exception), TemplateError from design doc section 3.2
  - All methods and classes MUST have docstrings
  - Create `tests/email/` directory with empty `tests/email/__init__.py`

  **Must NOT do**:
  - Do not add `use_tls`/`use_ssl` mutual exclusivity validator — not in design
  - Do not add email address validation to EmailConfig
  - Do not import these in `basic_tool/__init__.py` yet (that's T7)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple Pydantic models and exception classes, directly from design doc
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - N/A — straightforward data model task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3)
  - **Blocks**: T4, T5, T6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:68-112` — EmailConfig exact code (copy verbatim)
  - `doc/basic_tool_email_design.md:116-139` — Exceptions exact code (copy verbatim)
  - `basic_tool/redis/config.py` — Reference for Pydantic config model pattern in this project

  **WHY Each Reference Matters**:
  - Design doc has the exact code to use — only fix if there's a real bug
  - Redis config shows how this project writes Pydantic config models

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: Config and exceptions import correctly
    Tool: Bash
    Preconditions: Files created
    Steps:
      1. Run: python3 -c "from basic_tool.email.config import EmailConfig; c = EmailConfig(host='smtp.test.com', username='u', password='p'); print(c.from_address)"
      2. Run: python3 -c "from basic_tool.email.exceptions import EmailError, SendError, TemplateError; print('OK')"
    Expected Result: Both succeed. from_address returns 'u' (since sender_name is empty)
    Failure Indicators: ImportError, ValidationError, AttributeError
    Evidence: .sisyphus/evidence/task-2-config-import.txt

  Scenario: EmailConfig from_address property with sender_name
    Tool: Bash
    Preconditions: config.py created
    Steps:
      1. Run: python3 -c "from basic_tool.email.config import EmailConfig; c = EmailConfig(host='h', username='u@x.com', password='p', sender_name='MyApp'); print(c.from_address)"
    Expected Result: Output is "MyApp <u@x.com>"
    Failure Indicators: Wrong format, missing angle brackets
    Evidence: .sisyphus/evidence/task-2-from-address.txt

  Scenario: SendError preserves original exception
    Tool: Bash
    Preconditions: exceptions.py created
    Steps:
      1. Run: python3 -c "
      from basic_tool.email.exceptions import SendError
      try:
          raise ValueError('inner')
      except ValueError as e:
          err = SendError('outer', original=e)
          assert err.original is e
          assert str(err) == 'outer'
      print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: AssertionError, AttributeError
    Evidence: .sisyphus/evidence/task-2-exceptions.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(email): add EmailConfig and exception types`
  - Files: `basic_tool/email/__init__.py` (placeholder), `basic_tool/email/config.py`, `basic_tool/email/exceptions.py`, `tests/email/__init__.py`
  - Pre-commit: `python3 -c "from basic_tool.email.config import EmailConfig; from basic_tool.email.exceptions import EmailError, SendError, TemplateError"`

- [x] 3. Implement models.py + tests/test_models.py

  **What to do**:
  - Create `basic_tool/email/models.py` — Attachment, InlineImage, Email (Pydantic BaseModel), SendResult (dataclass) from design doc section 3.3
  - **IMPORTANT**: Use `dataclasses.field(default_factory=list)` exactly as design doc specifies — do NOT change to Pydantic v2 canonical `list[T] = []`
  - Include all validators: `subject_not_empty`, `to_not_empty`
  - Include all properties: `to_list`, `cc_list`, `bcc_list`, `all_recipients`
  - Create `tests/email/test_models.py` — Test cases 1-7 from design doc:
    1. Email basic creation (to, subject, body correct)
    2. Email to as list → to_list returns correct list
    3. Email empty subject → ValidationError
    4. Email empty to → ValidationError
    5. Email all_recipients (to + cc + bcc)
    6. Attachment creation
    7. InlineImage creation

  **Must NOT do**:
  - Do not add email format validation — only "not empty" check
  - Do not add dedup for recipients
  - Do not validate body is non-empty

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pydantic models + basic tests, directly from design doc
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2)
  - **Blocks**: T4, T5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:142-287` — Models exact code
  - `doc/basic_tool_email_design.md:1051-1058` — Test cases 1-7 specification
  - `tests/redis/test_client.py` — Reference for test class organization (class-based or function-based)

  **WHY Each Reference Matters**:
  - Design doc has exact model code — implement as-is
  - Test cases specify what to assert for each scenario

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: All model tests pass
    Tool: Bash
    Preconditions: models.py and test_models.py created
    Steps:
      1. Run: pytest tests/email/test_models.py -v
    Expected Result: 7 tests, 0 failures
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-3-model-tests.txt

  Scenario: Email validators reject invalid input
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. Run: python3 -c "
      from basic_tool.email.models import Email
      from pydantic import ValidationError
      try:
          Email(to='a@b.com', subject='', body='x')
          print('FAIL: should have raised')
      except ValidationError:
          print('OK: subject validation works')
      try:
          Email(to='', subject='s', body='x')
          print('FAIL: should have raised')
      except ValidationError:
          print('OK: to validation works')"
    Expected Result: Both validation prints show 'OK'
    Failure Indicators: No ValidationError raised, or wrong error
    Evidence: .sisyphus/evidence/task-3-validators.txt

  Scenario: Email all_recipients combines to + cc + bcc
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. Run: python3 -c "
      from basic_tool.email.models import Email
      e = Email(to='a@b.com', cc='c@d.com', bcc='e@f.com', subject='test', body='x')
      assert e.all_recipients == ['a@b.com', 'c@d.com', 'e@f.com']
      print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: AssertionError, wrong list contents
    Evidence: .sisyphus/evidence/task-3-all-recipients.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(email): add Email data models with tests`
  - Files: `basic_tool/email/models.py`, `tests/email/test_models.py`
  - Pre-commit: `pytest tests/email/test_models.py -v`

- [x] 4. Implement sender.py + tests/test_sender.py

  **What to do**:
  - Create `basic_tool/email/sender.py` with:
    - `EmailSender` ABC: abstract `send()`, default `send_bulk()`
    - `SmtpSender(EmailSender)`: async SMTP implementation with:
      - `_ensure_connection()` — persistent connection with auto-reconnect
      - `_build_message()` — **CRITICAL REWRITE**: use stdlib `email.mime.multipart.MIMEMultipart`, `email.mime.text.MIMEText`, `email.mime.image.MIMEImage`, `email.mime.base.MIMEBase` — NOT `aiosmtplib.SMTPMessage` (which does NOT exist)
      - `send()` — sends with lock, returns SendResult, raises SendError on connection errors
      - `send_bulk()` — batches by `bulk_batch_size`
      - `close()` — graceful disconnect
  - Create `tests/email/test_sender.py` — Test cases 12-19 using mocked aiosmtplib:
    - Mock pattern: `patch("basic_tool.email.sender.aiosmtplib.SMTP")` with `AsyncMock`
    - 12. SmtpSender construction
    - 13. _build_message: From/To/Cc/Subject headers
    - 14. _build_message: attachments
    - 15. _build_message: inline images with Content-ID
    - 16. _build_message: reply_to header
    - 17. _build_message: custom headers
    - 18. send() connection failure → raises SendError
    - 19. send() SMTP rejection → returns SendResult(success=False)
    - **EXTRA**: BCC privacy test — BCC addresses NOT in MIME headers but IN all_recipients
    - **EXTRA**: _build_message produces valid MIMEMultipart structure

  **Must NOT do**:
  - Do NOT use `aiosmtplib.SMTPMessage` — it does NOT exist
  - Do NOT add BCC to MIME message headers
  - Do NOT add retry/backoff logic
  - Do NOT add `__aenter__`/`__aexit__`
  - Do NOT use real SMTP server in tests — mock only
  - Do NOT add connection pooling — single persistent connection only

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Most complex task — MIME construction rewrite + mock setup + many test cases. The `_build_message()` rewrite from the broken design doc requires understanding MIME structure.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - N/A — pure Python, no UI or external skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES (within Wave 2)
  - **Parallel Group**: Wave 2 (with T5, T6)
  - **Blocks**: T7
  - **Blocked By**: T1 (deps), T2 (config+exceptions), T3 (models)

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:292-548` — SmtpSender design code (use as guide, but rewrite _build_message)
  - `doc/basic_tool_email_design.md:1063-1078` — Test cases 12-19 specification
  - `basic_tool/redis/client/__init__.py` — Reference for how this project organizes classes with async lifecycle (init/close pattern)
  - `tests/redis/test_client.py` — Reference for mock/test patterns in this project

  **API/Type References**:
  - `basic_tool/email/config.py` — EmailConfig (consumed by SmtpSender)
  - `basic_tool/email/exceptions.py` — SendError (raised by SmtpSender)
  - `basic_tool/email/models.py` — Email, SendResult (input/output types)

  **External References**:
  - Python stdlib `email.mime` docs: https://docs.python.org/3/library/email.mime.html
  - `aiosmtplib` API: `SMTP(hostname, port, timeout, use_tls)`, `.connect()`, `.starttls()`, `.login()`, `.send_message(msg, recipients=...)` returns `tuple[dict[str, SMTPResponse], str]`
  - `MIMEMultipart("mixed")` for attachments, `MIMEMultipart("related")` for inline images, `MIMEText(body, subtype)` for text/html body

  **WHY Each Reference Matters**:
  - Design doc code is the baseline but `_build_message()` MUST be rewritten — the design's use of `aiosmtplib.SMTPMessage` will fail at runtime
  - Redis client shows async lifecycle patterns used in this project (connect/close with lock)
  - `aiosmtplib.SMTP.send_message()` returns a tuple — message_id is the SECOND element, not read from `msg["Message-ID"]`

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: All sender tests pass
    Tool: Bash
    Preconditions: sender.py and test_sender.py created, aiosmtplib installed
    Steps:
      1. Run: pytest tests/email/test_sender.py -v
    Expected Result: 10+ tests (12-19 + BCC + MIME structure), 0 failures
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-4-sender-tests.txt

  Scenario: No SMTPMessage references in code
    Tool: Bash
    Preconditions: sender.py created
    Steps:
      1. Run: grep -r "SMTPMessage" basic_tool/email/
    Expected Result: No matches found (empty output)
    Failure Indicators: Any line containing SMTPMessage
    Evidence: .sisyphus/evidence/task-4-no-smtpmessage.txt

  Scenario: SmtpSender imports succeed
    Tool: Bash
    Preconditions: sender.py created
    Steps:
      1. Run: python3 -c "from basic_tool.email.sender import EmailSender, SmtpSender; print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-4-sender-import.txt

  Scenario: _build_message produces valid MIMEMultipart
    Tool: Bash
    Preconditions: sender.py created
    Steps:
      1. Run: python3 -c "
      from basic_tool.email.config import EmailConfig
      from basic_tool.email.sender import SmtpSender
      from basic_tool.email.models import Email
      config = EmailConfig(host='h', username='u@x.com', password='p')
      sender = SmtpSender(config)
      email = Email(to='to@x.com', subject='Test', body='Hello')
      msg = sender._build_message(email)
      assert msg['From'] is not None
      assert msg['To'] == 'to@x.com'
      assert msg['Subject'] == 'Test'
      print('MIME OK')"
    Expected Result: Prints 'MIME OK'
    Failure Indicators: AssertionError, AttributeError
    Evidence: .sisyphus/evidence/task-4-mime-structure.txt

  Scenario: BCC not leaked in MIME headers
    Tool: Bash
    Preconditions: sender.py created
    Steps:
      1. Run: python3 -c "
      from basic_tool.email.config import EmailConfig
      from basic_tool.email.sender import SmtpSender
      from basic_tool.email.models import Email
      config = EmailConfig(host='h', username='u@x.com', password='p')
      sender = SmtpSender(config)
      email = Email(to='to@x.com', bcc='secret@x.com', subject='Test', body='Hello')
      msg = sender._build_message(email)
      msg_str = str(msg)
      assert 'secret@x.com' not in msg_str, 'BCC leaked in headers!'
      assert 'secret@x.com' in email.all_recipients
      print('BCC privacy OK')"
    Expected Result: Prints 'BCC privacy OK'
    Failure Indicators: AssertionError with 'BCC leaked'
    Evidence: .sisyphus/evidence/task-4-bcc-privacy.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(email): add EmailSender ABC, SmtpSender, and sender tests`
  - Files: `basic_tool/email/sender.py`, `tests/email/test_sender.py`
  - Pre-commit: `pytest tests/email/test_sender.py -v`

- [x] 5. Implement dry_run.py + tests/test_dry_run.py

  **What to do**:
  - Create `basic_tool/email/dry_run.py` — DryRunSender(EmailSender) from design doc section 3.5
  - Properties: `sent_emails` (readonly copy), `sent_count`
  - Methods: `send()` (records to list), `reset()` (clears list)
  - Create `tests/email/test_dry_run.py` — Test cases 8-11:
    - 8. send() records to sent_emails, returns success=True
    - 9. send_bulk() records all, sent_count correct
    - 10. reset() clears records
    - 11. sent_emails returns readonly copy (modifying returned list doesn't affect internal state)

  **Must NOT do**:
  - Do not add thread safety / asyncio.Lock to DryRunSender
  - Do not add validation beyond what Email already does

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Simple in-memory sender, minimal complexity
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (within Wave 2)
  - **Parallel Group**: Wave 2 (with T4, T6)
  - **Blocks**: T7
  - **Blocked By**: T2 (exceptions), T3 (models)

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:552-622` — DryRunSender exact code
  - `doc/basic_tool_email_design.md:1059-1062` — Test cases 8-11 specification

  **API/Type References**:
  - `basic_tool/email/sender.py` — EmailSender ABC (parent class)
  - `basic_tool/email/models.py` — Email, SendResult

  **WHY Each Reference Matters**:
  - Design doc has complete code — straightforward implementation

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: All dry_run tests pass
    Tool: Bash
    Preconditions: dry_run.py and test_dry_run.py created
    Steps:
      1. Run: pytest tests/email/test_dry_run.py -v
    Expected Result: 4 tests, 0 failures
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-5-dryrun-tests.txt

  Scenario: DryRunSender records and resets correctly
    Tool: Bash
    Preconditions: dry_run.py created
    Steps:
      1. Run: python3 -c "
      import asyncio
      from basic_tool.email.dry_run import DryRunSender
      from basic_tool.email.models import Email
      sender = DryRunSender()
      email = Email(to='test@example.com', subject='Hi', body='Hello')
      result = asyncio.run(sender.send(email))
      assert result.success
      assert sender.sent_count == 1
      assert sender.sent_emails[0].subject == 'Hi'
      sender.reset()
      assert sender.sent_count == 0
      print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-5-dryrun-functional.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(email): add DryRunSender for testing`
  - Files: `basic_tool/email/dry_run.py`, `tests/email/test_dry_run.py`
  - Pre-commit: `pytest tests/email/test_dry_run.py -v`

- [x] 6. Implement template.py + tests/test_template.py

  **What to do**:
  - Create `basic_tool/email/template.py` — TemplateRenderer from design doc section 3.6
  - `_html_to_plain()` — regex-based HTML→text conversion
  - `TemplateRenderer.__init__(template_dir)` — creates Jinja2 Environment with FileSystemLoader, raises ImportError if jinja2 missing
  - `TemplateRenderer.render(template_name, **context)` — returns `(html, plain_text)` tuple
  - Create `tests/email/test_template.py` — Test cases 20-23:
    - 20. render() with template variables
    - 21. render() with non-existent template → TemplateError
    - 22. render() plain text fallback (tags removed)
    - 23. _html_to_plain() conversion (br→newline, tags stripped)
  - Create a temporary test template file for tests (use `tmp_path` fixture or create in tests/email/templates/)

  **Must NOT do**:
  - Do not add `html2text` or `beautifulsoup4` dependencies
  - Do not set `autoescape=True` — design explicitly uses `autoescape=False`
  - Do not add template caching beyond Jinja2's built-in

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Moderate complexity, well-defined by design doc
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (within Wave 2)
  - **Parallel Group**: Wave 2 (with T4, T5)
  - **Blocks**: T7
  - **Blocked By**: T2 (exceptions)

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:628-724` — TemplateRenderer exact code
  - `doc/basic_tool_email_design.md:1070-1078` — Test cases 20-23 specification

  **API/Type References**:
  - `basic_tool/email/exceptions.py` — TemplateError (raised by renderer)

  **WHY Each Reference Matters**:
  - Design doc has complete code. Tests need a sample template file.

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: All template tests pass
    Tool: Bash
    Preconditions: template.py and test_template.py created
    Steps:
      1. Run: pytest tests/email/test_template.py -v
    Expected Result: 4 tests, 0 failures
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-6-template-tests.txt

  Scenario: TemplateRenderer renders and converts to plain text
    Tool: Bash
    Preconditions: template.py created
    Steps:
      1. Run: python3 -c "
      import tempfile, os
      from basic_tool.email.template import TemplateRenderer
      with tempfile.TemporaryDirectory() as td:
          with open(os.path.join(td, 'test.html'), 'w') as f:
              f.write('<h1>Hello {{ name }}</h1>')
          r = TemplateRenderer(td)
          html, plain = r.render('test.html', name='World')
          assert 'Hello World' in html
          assert '<h1>' not in plain
          assert 'Hello World' in plain
      print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-6-template-functional.txt

  Scenario: TemplateRenderer raises TemplateError for missing template
    Tool: Bash
    Preconditions: template.py created
    Steps:
      1. Run: python3 -c "
      import tempfile
      from basic_tool.email.template import TemplateRenderer
      from basic_tool.email.exceptions import TemplateError
      with tempfile.TemporaryDirectory() as td:
          r = TemplateRenderer(td)
          try:
              r.render('nonexistent.html')
              print('FAIL')
          except TemplateError:
              print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: Prints 'FAIL' or unhandled exception
    Evidence: .sisyphus/evidence/task-6-template-missing.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(email): add TemplateRenderer with Jinja2 support`
  - Files: `basic_tool/email/template.py`, `tests/email/test_template.py`
  - Pre-commit: `pytest tests/email/test_template.py -v`

- [x] 7. Finalize __init__.py exports, README.md, and package registration

  **What to do**:
  - Create `basic_tool/email/__init__.py` — flat exports from design doc section 3.7 (replace placeholder)
  - Update `basic_tool/__init__.py` — add `- email: ...` line to docstring ONLY, do NOT add imports
  - Create `basic_tool/email/README.md` — document ALL public APIs following `basic_tool/redis/README.md` pattern:
    - Module overview
    - Dependencies
    - Quick start example
    - Full API reference for each public class/function
    - Usage examples matching design doc section 五

  **Must NOT do**:
  - Do NOT add import statements to `basic_tool/__init__.py` — only docstring update
  - Do NOT modify any files outside `basic_tool/email/` except `basic_tool/__init__.py` docstring
  - Do NOT add `TemplateRenderer` to `__init__.py` exports (it's imported separately from `basic_tool.email.template`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Boilerplate exports + documentation writing
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential, after Wave 2)
  - **Blocks**: F1-F4
  - **Blocked By**: T4, T5, T6

  **References**:

  **Pattern References**:
  - `doc/basic_tool_email_design.md:728-765` — __init__.py exact exports
  - `basic_tool/redis/README.md` — README structure pattern (dependency → structure → API → examples)
  - `basic_tool/__init__.py` — Current docstring to extend
  - `doc/basic_tool_email_design.md:767-865` — API reference tables for README content
  - `doc/basic_tool_email_design.md:867-1027` — Usage examples for README

  **WHY Each Reference Matters**:
  - Redis README shows the documentation standard for this project
  - Design doc sections 八 and 五 have the exact API tables and examples to include

  **Acceptance Criteria**:

  QA Scenarios (MANDATORY):

  ```
  Scenario: Full module import works
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. Run: python3 -c "from basic_tool.email import Email, EmailConfig, SmtpSender, DryRunSender, EmailSender, SendResult, Attachment, InlineImage, EmailError, SendError, TemplateError; print('all imports OK')"
    Expected Result: Prints 'all imports OK'
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-7-full-import.txt

  Scenario: TemplateRenderer importable from submodule
    Tool: Bash
    Preconditions: template.py and __init__.py created
    Steps:
      1. Run: python3 -c "from basic_tool.email.template import TemplateRenderer; print('OK')"
    Expected Result: Prints 'OK'
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-7-template-import.txt

  Scenario: All email tests pass
    Tool: Bash
    Preconditions: All files complete
    Steps:
      1. Run: pytest tests/email/ -v
    Expected Result: 24+ tests, 0 failures
    Failure Indicators: Any test failure
    Evidence: .sisyphus/evidence/task-7-all-tests.txt

  Scenario: No regressions in existing tests
    Tool: Bash
    Preconditions: All files complete
    Steps:
      1. Run: pytest tests/ -v
    Expected Result: All tests pass (existing + new email tests)
    Failure Indicators: Any test failure in non-email tests
    Evidence: .sisyphus/evidence/task-7-no-regressions.txt

  Scenario: basic_tool/__init__.py has docstring update only
    Tool: Bash
    Preconditions: basic_tool/__init__.py updated
    Steps:
      1. Run: python3 -c "
      with open('basic_tool/__init__.py') as f:
          content = f.read()
      assert 'import ' not in content, 'Found import statements!'
      assert 'email' in content.lower(), 'Missing email in docstring!'
      print('docstring-only update OK')"
    Expected Result: Prints 'docstring-only update OK'
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-7-init-docstring.txt

  Scenario: README.md documents all public APIs
    Tool: Bash
    Preconditions: README.md created
    Steps:
      1. Run: python3 -c "
      with open('basic_tool/email/README.md') as f:
          content = f.read()
      for name in ['EmailConfig', 'Email', 'Attachment', 'InlineImage', 'SendResult', 'EmailSender', 'SmtpSender', 'DryRunSender', 'EmailError', 'SendError', 'TemplateError', 'TemplateRenderer']:
          assert name in content, f'Missing {name} in README'
      print('README completeness OK')"
    Expected Result: Prints 'README completeness OK'
    Failure Indicators: AssertionError for missing API names
    Evidence: .sisyphus/evidence/task-7-readme-complete.txt
  ```

  **Commit**: YES
  - Message: `feat(email): add module exports, README, and package registration`
  - Files: `basic_tool/email/__init__.py` (replace placeholder), `basic_tool/__init__.py`, `basic_tool/email/README.md`
  - Pre-commit: `pytest tests/email/ -v && python3 -c "from basic_tool.email import Email, EmailConfig, SmtpSender"`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns (`SMTPMessage`, `__aenter__`, retry logic, BCC in MIME headers, imports in basic_tool/__init__.py). Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python3 -m py_compile` on all new files. Run `pytest tests/ -v`. Review all new files for: missing docstrings, `as any` patterns, empty catches, console.log equivalents (print statements in prod code), unused imports. Check AI slop: excessive comments, over-abstraction. Verify logging uses `|` separator format. Check all 75+ existing tests still pass.
  Output: `Compile [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task. Verify cross-module integration: `from basic_tool.email import Email, EmailConfig, SmtpSender, DryRunSender, EmailSender, SendResult, Attachment, InlineImage, EmailError, SendError, TemplateError`. Run `pytest tests/ -v` to verify no regressions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Detect files touched outside planned scope. Verify `_build_message` uses stdlib `email.mime.*` not `aiosmtplib.SMTPMessage`. Verify `basic_tool/__init__.py` only changed docstring.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(email): add aiosmtplib and jinja2 dependencies` — pyproject.toml, uv.lock
- **T2-T6**: Individual commits per module (grouped by wave completion)
- **T7**: `feat(email): add module exports, README, and package init` — __init__.py, README.md
- **Final**: Squash or keep individual based on preference

---

## Success Criteria

### Verification Commands
```bash
# Dependencies installed
python3 -c "import aiosmtplib; import jinja2; print('deps OK')"
# Expected: deps OK

# Module importable
python3 -c "from basic_tool.email import Email, EmailConfig, SmtpSender, DryRunSender, EmailSender, SendResult, Attachment, InlineImage, EmailError, SendError, TemplateError; print('imports OK')"
# Expected: imports OK

# All email tests pass
pytest tests/email/ -v
# Expected: 24+ tests, 0 failures

# No regressions
pytest tests/ -v
# Expected: all existing tests pass + new email tests pass

# No SMTPMessage references (guardrail check)
grep -r "SMTPMessage" basic_tool/email/
# Expected: no matches
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] README.md documents all public APIs
- [ ] No regressions in existing tests
