# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project Constraints

### Code Documentation

- **All methods must have docstrings** describing purpose, parameters, return values, and exceptions.
- **All modules must have a file-level docstring** describing the module's role in the architecture.

### basic_tool Package Rules

- **Each package under `basic_tool/` must have its own `README.md`** documenting:
  - What the package does
  - All public APIs with signatures and descriptions
- **`basic_tool/` is read-only during normal feature development.** Do not modify files under `basic_tool/` unless:
  - Explicitly asked by the user
  - A genuine bug is found that needs fixing
- **Every modification to `basic_tool/` must update the corresponding `README.md`** to keep documentation in sync.

### Multi-File Module Convention

**When a logical module spans multiple files, it must be organized as a folder with an `__init__.py`:**

```
# Good — client is a folder with __init__.py + Mixin files
basic_tool/redis/client/
├── __init__.py          # Cache class definition + lifecycle
├── _string.py           # StringMixin
├── _hash.py             # HashMixin
└── ...

# Bad — flat files with loose coupling
basic_tool/redis/
├── client.py            # Cache class
├── _string.py           # Mixin
├── _hash.py             # Mixin
└── ...
```

Rule: **If a module has more than one implementation file (e.g., class + mixins), put them in a folder.** Single-file modules (like `config.py`, `health.py`) can stay as flat files.

### Mixin Pattern for Cache Client

The `Cache` class in `basic_tool/redis/client/` uses the **Mixin pattern** to organize methods by Redis data type:

- Each Redis category lives in a separate `_<category>.py` file as a Mixin class.
- `client/__init__.py` contains only the `Cache` class definition (lifecycle + Mixin composition).
- All Mixin files use `_` prefix (e.g., `_string.py`, `_hash.py`) — they are internal implementation details.
- Users import only `from basic_tool.redis import Cache` — the Mixin composition is invisible to them.

**Current Mixin files:**

| File | Mixin Class | Covers |
|---|---|---|
| `_string.py` | `StringMixin` | get/set/delete/expire/ttl/incr/decr/mget/mset/scan |
| `_hash.py` | `HashMixin` | hget/hset/hgetall/hdel |
| `_set.py` | `SetMixin` | sadd/srem/smembers |
| `_list.py` | `ListMixin` | lpush/rpush/lpop/rpop/lrange/llen/lindex/lset/lrem/lmove/blpop/brpop/blmove |
| `_sorted_set.py` | `SortedSetMixin` | zadd/zrem/zrange/zrangebyscore/zcard/zscore/zrank/zremrangebyscore |
| `_script.py` | `ScriptMixin` | eval/evalsha/register_script |
| `_pubsub.py` | `PubSubMixin` | publish/pubsub/subscribe/psubscribe |
| `_json.py` | `JsonMixin` | get_json/set_json |
| `_raw.py` | `RawMixin` | execute_command/pipeline |

**When adding new Redis operations:**
1. If it fits an existing Mixin category, add the method to that `_<category>.py` file.
2. If it's a new category (e.g., HyperLogLog, Bitmap, Stream), create a new `_hyperloglog.py` with a `HyperLogLogMixin` class and add it to `Cache`'s inheritance list in `client.py`.
3. Every new/modified method must have a docstring.
4. Every change must include corresponding tests.
5. Update `README.md` after any change.

### Log Module

`basic_tool/logger/` 使用 Loguru 封装，自定义格式: `level||file:line||k1=v1||k2=v2||message`

- `config.py` — `LogConfig` 配置类
- `logger.py` — `setup()` 初始化、`get()` 获取 logger、`_formatter()` 自定义格式化

**格式说明:**
- 无 extra 字段: `INFO||app.py:42||hello world`
- 有 extra 字段: `INFO||app.py:42||user_id=123||action=login||hello world`
- extra 通过 `logger.info("msg", key=val)` 传入

### Testing

- **Every modification must be verified by unit tests before being considered complete.**
- When adding a new feature, write tests first or alongside the implementation.
- When fixing a bug, write a test that reproduces it, then make it pass.
- When refactoring, ensure all existing tests pass before and after.
- Tests live under `tests/`, mirroring the `basic_tool/` structure.
- Run tests with: `pytest tests/ -v`

### Development Workflow

1. Read the task carefully
2. Explore the codebase before making changes
3. Follow the four principles above
4. Write tests to verify changes
5. Run `pytest tests/ -v` and ensure all tests pass
6. Keep changes minimal and focused
