# basic_tool.storage — 文件存储

统一文件存储抽象，支持本地文件系统后端（LocalBackend），使用 aiofiles 异步 I/O。

## 依赖

- `aiofiles>=23.0.0` — 异步文件 I/O
- `pydantic>=2.0.0` — 配置校验

## 模块结构

```
basic_tool/storage/
├── __init__.py        # 统一导出
├── config.py          # StorageConfig 配置类
├── backend.py         # StorageBackend ABC + FileInfo
├── local.py           # LocalBackend 本地文件系统实现
└── storage.py         # Storage 门面类
```

## API 文档

---

### `config.py` — StorageConfig

```python
class StorageConfig(BaseModel):
    backend: str = "local"          # 后端类型，v1 仅 "local"
    base_dir: str = "./uploads"     # 本地存储根目录
    url_prefix: str = ""            # url() 拼接前缀，空则返回 key 本身
    auto_create_dir: bool = True    # init() 时是否自动创建 base_dir
```

---

### `backend.py` — FileInfo

```python
class FileInfo:
    __slots__ = ("key", "size", "content_type", "last_modified", "metadata")
```

| 属性 | 类型 | 说明 |
|---|---|---|
| `key` | `str` | 文件键名（相对路径，如 `"photos/cat.jpg"`） |
| `size` | `int` | 文件大小（字节） |
| `content_type` | `str \| None` | MIME 类型（如 `"image/png"`），未设置时为 None |
| `last_modified` | `float` | 最后修改时间（Unix 时间戳，秒） |
| `metadata` | `dict \| None` | 自定义元数据（v1 不支持持久化，恒为 None） |

---

### `backend.py` — StorageBackend

存储后端抽象基类，定义 `init`/`close`/`put`/`get`/`delete`/`exists`/`info`/`list` 八个抽象方法。
业务方通过 `Storage` 门面使用，不直接接触 `StorageBackend` 实例。

---

### `storage.py` — Storage

```python
class Storage:
    def __init__(self, config: StorageConfig)
```

#### 生命周期

| 方法 | 说明 |
|---|---|
| `async init() -> None` | 初始化后端资源（创建目录等）。lifespan startup 调用 |
| `async close() -> None` | 释放后端资源。lifespan shutdown 调用 |
| `backend -> StorageBackend` | 底层后端实例，用于调用未封装的操作 |

#### 文件操作

| 方法 | 说明 |
|---|---|
| `async put(key, data, content_type=None, metadata=None) -> None` | 写入文件，**静默覆盖**同名文件。`content_type` 为 None 时清除旧值。`metadata` 在 v1 中被忽略（no-op） |
| `async get(key) -> bytes` | 读取完整文件内容 |
| `async delete(key) -> None` | 删除文件（不存在时抛 `FileNotFoundError`） |
| `async exists(key) -> bool` | 检查文件是否存在 |
| `async info(key) -> FileInfo` | 获取文件元信息（大小、content_type、修改时间等） |
| `async list(prefix="") -> list[FileInfo]` | 列出前缀下的文件（按路径排序）。`prefix` 为空列出全部 |

#### URL 生成

| 方法 | 说明 |
|---|---|
| `url(key) -> str` | **同步方法**。`url_prefix` 为空时返回 key 本身，否则拼接 `{url_prefix}/{key}` |

#### 安全

内置路径遍历防护：所有方法会校验解析后的路径必须位于 `base_dir` 内，
拦截绝对路径和 `..` 上跳。非法 key 抛 `ValueError`。

---

## 使用示例

```python
from basic_tool.storage import Storage, StorageConfig

config = StorageConfig(base_dir="/data/uploads", url_prefix="https://cdn.example.com")
storage = Storage(config)

async def lifespan(app):
    await storage.init()
    yield
    await storage.close()

# 写入文件
await storage.put("photos/cat.jpg", image_bytes, content_type="image/jpeg")

# 读取文件
data = await storage.get("photos/cat.jpg")

# 获取文件信息
info = await storage.info("photos/cat.jpg")
print(info.size, info.content_type, info.last_modified)

# 列出文件
files = await storage.list("photos/")
for f in files:
    print(f.key, f.size)

# 检查存在
if await storage.exists("photos/cat.jpg"):
    await storage.delete("photos/cat.jpg")

# 生成访问 URL（同步方法）
url = storage.url("photos/cat.jpg")  # "https://cdn.example.com/photos/cat.jpg"
```
