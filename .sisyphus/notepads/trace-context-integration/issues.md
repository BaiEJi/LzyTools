# Issues — trace-context-integration

(Updated as issues are discovered)

## F4 Scope Fidelity Check (2026-06-13)
- VERDICT: APPROVE — all 6 tasks compliant, id_generator untouched, no scope creep
- 2 justified deviations (both genuine bug fixes for Starlette architecture):
  1. middleware.py: BaseHTTPMiddleware → pure ASGI (plan exception clause #4)
  2. handler.py: reads scope["basic_tool.traceparent"] for 500 response headers
- Modified files (16) map 1:1 to T1-T6 spec; tests/errors/ correctly NOT modified
- All cross-cutting checks clean: 0 request_id in source, 0 uuid in context/, 0 uuid in fastapi middleware

## F3 QA Finding: T6.4 Exception handler can't read trace_id from ContextVar

**Date**: 2026-06-13
**Severity**: Medium (affects observability for unhandled exceptions only)

### Problem
The global Exception handler (registered via `@app.exception_handler(Exception)`)
runs in ServerErrorMiddleware, which is OUTSIDE ContextMiddleware. Therefore,
`ctx.get("trace_id")` returns empty string for unhandled exceptions (RuntimeError,
ValueError, etc.).

### Root Cause
Starlette's `build_middleware_stack` (applications.py:62-66):
```python
for key, value in self.exception_handlers.items():
    if key in (500, Exception):
        error_handler = value          # -> ServerErrorMiddleware (OUTSIDE ContextMiddleware)
    else:
        exception_handlers[key] = value # -> ExceptionMiddleware (INSIDE ContextMiddleware)
```

### Impact
- AppError (business errors): trace_id IS in error log ✓
- Unhandled exceptions: trace_id NOT in error log ✗
- Response traceparent: correctly set for both (from scope) ✓

### Fix
Parse trace_id from `request.scope["basic_tool.traceparent"]` in global_exception_handler
instead of relying on ContextVar. Same approach already used for response header.

### Key Learning
**Starlette puts the Exception catch-all handler on ServerErrorMiddleware (outermost),
NOT ExceptionMiddleware (innermost).** This means any middleware-set ContextVars are
NOT available in the catch-all Exception handler. Specific exception handlers (AppError,
HTTPException, etc.) ARE available because they're on ExceptionMiddleware (innermost).
