# basic_tool.logger — Loguru 日志系统

基于 `loguru` 的日志封装，支持两种输出格式：

**logfmt 格式**（默认）:
```
2024-01-15T10:30:00||INFO||app.py:42||user_id=123||action=login||user logged in
2024-01-15T10:30:00||ERROR||db.py:99||connection lost
```

**JSON 格式**（`json_output=True`）:
```json
{"time":"2024-01-15T10:30:00+00:00","level":"INFO","file":"app.py","line":42,"function":"main","message":"user logged in","user_id":123,"action":"login"}
```

## 依赖

- `loguru>=0.7.0` — 日志库
- `orjson>=3.9.0` — JSON 序列化（JSON 模式使用）

## 模块结构

```
basic_tool/logger/
├── __init__.py    # 统一导出
├── config.py      # LogConfig 配置类（dataclass）
├── logger.py      # setup() / get() + 格式化函数
└── README.md
```

## API 文档

---

### `config.py` — LogConfig

```python
@dataclass
class LogConfig:
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    sink: list[str] = ["sys.stderr"]     # 输出目标列表
    rotation: str | None = None          # 文件轮转策略，如 "500 MB", "00:00"
    retention: str | None = None         # 文件保留策略，如 "10 days"
    enqueue: bool = True                 # 线程安全写入
    json_output: bool = False            # JSON 格式输出
    backtrace: bool = True               # 异常时打印完整调用栈
    diagnose: bool = False               # 异常时显示变量值
```

---

### `logger.py`

#### `setup(config: LogConfig | None = None) -> None`

初始化日志系统。移除 loguru 默认 sink，按配置重新添加。可重复调用。

```python
# 默认 logfmt 格式
setup(LogConfig(level="DEBUG"))

# JSON 格式（便于 ELK/Datadog/Loki 采集）
setup(LogConfig(json_output=True))

# 多 sink（同时写 stderr 和文件）
setup(LogConfig(sink=["sys.stderr", "/var/log/app.log"], rotation="500 MB", retention="10 days"))
```

#### `get() -> loguru.Logger`

获取已配置的 logger 实例。如果 `setup()` 尚未调用，会自动以默认配置初始化。

```python
log = get()
log.info("server started", host="0.0.0.0", port=8080)
# logfmt: 2024-01-15T10:30:00||INFO||server.py:10||host=0.0.0.0||port=8080||server started
```

---

## 使用示例

```python
from basic_tool.logger import setup, get, LogConfig

# 初始化（通常在应用启动时调用一次）
setup(LogConfig(level="DEBUG"))

# 获取 logger 并使用
log = get()

log.info("request received", method="GET", path="/api/users", user_id=123)
# 2024-01-15T10:30:00||INFO||app.py:15||method=GET||path=/api/users||user_id=123||request received

log.warning("slow query", sql="SELECT ...", duration_ms=500)
# 2024-01-15T10:30:00||WARNING||app.py:16||sql=SELECT ...||duration_ms=500||slow query

# JSON 格式（生产环境推荐）
setup(LogConfig(json_output=True))
log.info("user logged in", user_id=123)
# {"time":"2024-01-15T10:30:00+00:00","level":"INFO","file":"app.py","line":20,"function":"main","message":"user logged in","user_id":123}

# 文件输出 + 轮转
setup(LogConfig(
    level="INFO",
    sink=["sys.stderr", "/var/log/app.log"],
    rotation="500 MB",
    retention="30 days",
))
```
