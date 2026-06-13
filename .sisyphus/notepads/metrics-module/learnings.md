# Learnings — metrics-module

## Codebase Patterns
- Mixin pattern: each Redis data type in `_<type>.py`, imported in `client/__init__.py`
- All Mixins use `self.client` to access the underlying `redis.asyncio.Redis` instance
- Docstring format: module-level docstring + class docstring + method docstrings with Args/Returns
- Tests: class-based, Chinese docstrings, fakeredis, plain assert
- pytest-asyncio auto mode (no `@pytest.mark.asyncio` needed)
- Config classes: Pydantic BaseModel with docstrings listing Attributes
- `__init__.py` pattern: docstring + imports + `__all__`

## Key Decisions
- eval() in collector.py → replaced with tuple(sorted(p.labels.items())) as dict key
- flush_to_vm creates httpx client in init(), not per-call
- _do_flush: copy buffer before pop to prevent data loss on failure
- StreamMixin only adds xadd, no other stream operations
- generate_exposition NOT exported in __init__.py __all__

## collector.py implementation
- tuple(sorted(p.labels.items())) is hashable and avoids eval() — works as dict key directly
- copy-then-clear pattern: collect all points from buffers, POST, only clear on success
- httpx.MockTransport(lambda req: httpx.Response(200)) for mocking HTTP in tests
- No @pytest.mark.asyncio needed — pytest-asyncio auto mode
- subprocess.run(["grep", "-c", "eval(", ...]) for security verification in tests
- defaultdict(list) for _buffers — .clear() works on defaultdict values

## writer.py implementation
- httpx.AsyncClient created in init(), stored as self._http, closed in close() — connection reuse across flush_to_vm calls
- self.cache property guards _initialized flag, raises RuntimeError if not initialized
- Tests that call flush_to_vm must use MockTransport (replaces real client) — even for client-reuse test
- fakeredis supports xadd — can verify stream entries via fake_client.xrange()
- Empty batch to flush_to_vm still sends POST (body="") — MockTransport needed even for empty batch test

## AlertEvaluator Learnings
- State machine: OK → PENDING → FIRING → OK, pure sync logic
- _parse_condition regex: `r"^\s*(>=|<=|!=|==|>|<)\s*([\d.]+)\s*$"` — no negative threshold support
- _parse_duration regex: `r"^\s*(\d+)\s*([smhd])\s*$"`
- NaN comparison: `float('nan') > 80` is False in Python — no alert triggered for NaN
- Cooldown checked BEFORE duration — order matters in evaluate()
- OK event pops from _states dict (not just sets to OK)
- get_all_states returns dict(self._states) — defensive copy
- When testing operator parsing: use different test value vs threshold (e.g., 90 vs 80) to get meaningful True/False

## StreamMixin re-creation (2026-06-13)
- _stream.py follows exact _pubsub.py structure; only xadd added (no xread/xlen/xrange in Mixin)
- Import placement: alphabetical — _stream goes between _sorted_set and _string in client/__init__.py
- tests/redis/ has NO __init__.py but works fine (existing test_advanced.py proves it) — did not create one
- fakeredis xrange returns list of (id, fields_dict) tuples — test_xadd_data_stored verifies via cache.client.xrange()
- Pyright reportAttributeAccessIssue on self.client is the accepted Mixin pattern (same in _pubsub.py) — not a real error
- README Stream section placed after Pub/Sub, before the --- preceding ### health.py

## config.py re-creation (2026-06-13)
- Pattern follows basic_tool/redis/config.py exactly: module docstring + Pydantic BaseModel + class docstring with Attributes list
- Fields: vm_url, redis_url, service_name, flush_interval (float), flush_batch_size (int), stream_prefix, stream_max_len (100_000 underscore literal), alert_interval (float)
- basic_tool/metrics/__init__.py created as minimal docstring-only (no exports yet — later task handles __all__)
- tests/metrics/ created WITHOUT __init__.py (matches tests/redis/ convention, learnings line 47 confirms this works)
- Test style: class TestMetricsConfig with Chinese docstrings, plain assert, import ValidationError from pydantic

## models.py re-creation (2026-06-13)
- Pattern follows config.py: module docstring + Pydantic BaseModel classes with Attributes docstrings
- 8 types: MetricType (str Enum), MetricPoint, MetricBatch, TimeRange, QueryResult, AlertRule, AlertState (str Enum), AlertEvent
- Mutable defaults ({}, []) safe in Pydantic v2 fields — Pydantic handles deepcopy, no Field(default_factory=...) needed
- MetricType/AlertState are str-Enum — test .value with == comparison (e.g., MetricType.COUNTER.value == "counter")
- `from typing import Any` needed for QueryResult.values: list[list[Any]] (timestamp can be int/float, value can be str/float)
- `datetime | None` modern union syntax works in Python 3.13 + Pydantic v2
- Test file imports 8 model classes in grouped parenthesized import block — alphabetical order
- 12 tests across 7 classes (MetricPoint has 3, MetricBatch has 2, Enums has 2, others 1 each)
- Tests use plain datetime import, no pytest.mark.asyncio (sync models, no async needed)

## collector.py re-creation (2026-06-13)
- Pattern follows http_client/client.py lifecycle: __init__ stores config/endpoint/buffers, init() creates httpx.AsyncClient + starts flush_task, close() cancels task + closes client (guarded against double-close)
- defaultdict(list) for _buffers — .clear() works in-place on the list value
- prometheus_exposition aggregation: tuple(sorted(p.labels.items())) as dict key, sum values per label set — produces one line per unique label combination
- str(float_value) gives "42.0" — substring checks like "queue_depth 42" still pass (substring of "queue_depth 42.0")
- Empty buffers → return "\n" (checked via any(self._buffers.values()))
- _do_flush reuses self.prometheus_exposition() for body (DRY) — safe because no await between snapshot and exposition call
- copy-then-clear: snapshot = list(points) copy, POST, only clear on raise_for_status success
- Pyright reportOptionalMemberAccess on self._http.post() — fixed with `if self._http is None: return` guard at top of _do_flush
- Tests inject MockTransport via collector._http = httpx.AsyncClient(transport=transport) — do NOT call init() (avoids starting flush loop)
- subprocess.run with text=True for grep -c eval( test — avoids bytes/str comparison issue
- flush_interval=999 in test_init_creates_http_client to prevent flush loop from firing during test

## writer.py creation (2026-06-13)
- Pyright reportOptionalMemberAccess on self.cache.xadd() — fixed by: (1) importing Cache from basic_tool.redis, (2) typing cache param as `Cache | None`, (3) typing self._cache as `Cache | None`, (4) property returns `-> Cache` with combined guard `if not self._initialized or self._cache is None`
- The combined guard narrows _cache to non-None for Pyright (checking _initialized alone doesn't narrow _cache's type)
- Pyright reportOptionalMemberAccess on self._http.post() — fixed with `if self._http is None: return 0` guard at top of flush_to_vm (after empty-points check), same pattern as collector._do_flush
- flush_to_vm posts to RELATIVE path "/api/v1/import/prometheus" — AsyncClient MUST have base_url set, else httpx raises UnsupportedProtocol. Tests that manually set _http must include base_url (e.g., httpx.AsyncClient(base_url="http://test", transport=transport))
- test_write_batch verifies stream via cache.client.xrange("metrics:test_svc") — fakeredis supports xrange, returns list of (id, fields_dict) tuples
- No circular import: basic_tool.redis import in metrics.writer is safe (redis doesn't import metrics)
- Newly created writer.py shows reportMissingImports in test file initially — Pyright index lag, NOT a real error (runtime import works, pattern identical to test_collector.py)

## reader.py creation (2026-06-13)
- Module docstring + import block specified VERBATIM by task spec — must use exact text
- Spec deviation from writer.py: reader.py guards on `self._http is None` directly in `client` property (NOT `_initialized` flag like writer.py). RuntimeError message: "MetricsReader 未初始化，请先调用 init()"
- close() uses same idempotent guard as writer.py: `if self._http is not None: await self._http.aclose(); self._http = None` — no separate _initialized flag needed since None check covers it
- query_range: params dict with `start`/`end` as `.timestamp()` (unix float) and `step` as PromQL string. Parse `data.result` array, each item has `metric` dict + `values` list-of-lists
- query_instant: params `{"query": query, "time": "now"}`. Each result has single `value` (not `values`) — wrap with ternary: `[item["value"]] if "value" in item else item.get("values", [])` for robustness
- label_values: GET `/api/v1/label/{label}/values` with NO params. Response shape differs: `{"status":"success","data":[...]}` (data is array directly, NOT nested under result)
- Tests: spec says NO @pytest.mark.asyncio (pytest-asyncio mode=auto handles it) — confirmed by test_writer.py pattern
- Test pattern for tests 1-3: manually set `reader._http = httpx.AsyncClient(transport=transport, base_url="...")` WITHOUT calling init() (avoids real client). Cleanup with `await reader.close()`
- Test 4 (test_not_initialized_raises) is SYNC (no async needed) — `with pytest.raises(RuntimeError, match="未初始化"): _ = reader.client`
- All 4 tests passed in 0.14s — no fakeredis/cache fixture needed (pure HTTP mocking)
- Pyright reportMissingImports on test file → known index-lag false positive (same as test_writer.py learnings line 78), runtime import works
