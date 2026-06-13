# basic_tool.crypto — 密码学工具集

面向 Web 应用的密码学工具集合，覆盖密码哈希、Token 生成、对称加密、HMAC 签名和密钥派生。默认参数遵循 OWASP 2025 建议：Argon2id（64MB 内存、3 次迭代）、PBKDF2-SHA256（600,000 次迭代）。生产环境建议保持默认参数，除非有明确的性能或合规理由调整。

## 依赖

- `argon2-cffi>=23.1.0` — Argon2id 密码哈希
- `cryptography>=42.0.0` — Fernet 对称加密、HKDF、PBKDF2

## 模块结构

```
basic_tool/crypto/
├── __init__.py    # 统一导出 17 个公开符号
├── config.py      # CryptoConfig 配置类（Pydantic BaseModel）
├── password.py    # Argon2id 密码哈希、Token 生成
├── encrypt.py     # Fernet 对称加密/解密
├── sign.py        # HMAC-SHA256 签名、SHA-256 哈希
├── kdf.py         # HKDF、PBKDF2 密钥派生
├── exceptions.py  # 异常层次结构
└── README.md
```

## API 文档

---

### 密码哈希 (password.py)

#### `hash_password(password: str, config: CryptoConfig | None = None) -> str`

使用 Argon2id 算法哈希密码。每次调用自动生成随机盐。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| password | `str` | — | 明文密码 |
| config | `CryptoConfig \| None` | `None` | 密码学配置，`None` 时使用默认配置 |

返回 Argon2id 哈希字符串，格式如 `$argon2id$v=19$m=65536,t=3,p=1$...`，可直接存入数据库。

---

#### `verify_password(password: str, hash: str, config: CryptoConfig | None = None) -> bool`

验证密码是否匹配 Argon2id 哈希。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| password | `str` | — | 待验证的明文密码 |
| hash | `str` | — | Argon2id 哈希字符串 |
| config | `CryptoConfig \| None` | `None` | 密码学配置 |

返回 `True` 表示匹配，`False` 表示不匹配或哈希无效。本函数不抛异常，所有验证失败均返回 `False`。

---

#### `needs_rehash(hash: str, config: CryptoConfig | None = None) -> bool`

检查现有哈希是否需要用新参数重新计算。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| hash | `str` | — | 现有的 Argon2id 哈希字符串 |
| config | `CryptoConfig \| None` | `None` | 目标配置参数 |

返回 `True` 表示哈希参数（内存、迭代次数等）与当前配置不符，应在用户下次登录时重新哈希。

**安全提示**：OWASP 推荐在登录验证成功后调用此函数，逐步将旧参数哈希升级到当前推荐参数。

---

#### `generate_token(length: int | None = None, config: CryptoConfig | None = None) -> str`

生成 URL-safe 的随机 Token，基于 `secrets.token_urlsafe`（CSPRNG）。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| length | `int \| None` | `None` | Token 字节长度，`None` 时使用 `config.token_bytes` |
| config | `CryptoConfig \| None` | `None` | 密码学配置 |

返回 URL-safe base64 编码字符串（默认 32 字节产生 43 字符）。适用于 API Token、会话 ID、密码重置链接。

---

#### `generate_hex_token(length: int | None = None, config: CryptoConfig | None = None) -> str`

生成十六进制编码的随机 Token，基于 `secrets.token_hex`（CSPRNG）。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| length | `int \| None` | `None` | Token 字节长度，`None` 时使用 `config.token_bytes` |
| config | `CryptoConfig \| None` | `None` | 密码学配置 |

返回十六进制字符串（默认 32 字节产生 64 字符）。适用于需要纯字母数字字符的场景，如数据库主键、OTP 种子。

---

### 对称加密 (encrypt.py)

#### `generate_fernet_key() -> str`

生成一个新的 Fernet 密钥。

无参数。返回 URL-safe base64 编码的密钥字符串，可直接赋值给 `CryptoConfig.fernet_key`。

**注意**：密钥应安全存储（如环境变量、密钥管理服务），丢失后所有加密数据将无法解密。

---

#### `encrypt(data: bytes, config: CryptoConfig) -> bytes`

加密二进制数据。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| data | `bytes` | — | 待加密的明文字节 |
| config | `CryptoConfig` | — | 必须包含 `fernet_key` |

返回 Fernet 加密后的密文字节。

**异常**：
- `InvalidKeyError` — `fernet_key` 为空或无效时抛出

---

#### `decrypt(token: bytes, config: CryptoConfig, ttl: int | None = None) -> bytes`

解密二进制密文。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| token | `bytes` | — | Fernet 加密的密文字节 |
| config | `CryptoConfig` | — | 必须包含 `fernet_key` |
| ttl | `int \| None` | `None` | 生存时间（秒），超过则视为过期；`None` 时不检查 |

返回解密后的明文字节。

**异常**：
- `DecryptionError` — 解密失败（密钥错误、密文损坏或 TTL 过期）
- `InvalidKeyError` — `fernet_key` 为空或无效

---

#### `encrypt_str(text: str, config: CryptoConfig) -> bytes`

加密字符串，等价于 `encrypt(text.encode("utf-8"), config)`。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| text | `str` | — | 待加密的明文字符串（UTF-8 编码） |
| config | `CryptoConfig` | — | 必须包含 `fernet_key` |

返回 Fernet 加密后的密文字节。

**异常**：
- `InvalidKeyError` — `fernet_key` 为空或无效时抛出

---

#### `decrypt_str(token: bytes, config: CryptoConfig, ttl: int | None = None) -> str`

解密密文为字符串，等价于 `decrypt(token, config, ttl).decode("utf-8")`。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| token | `bytes` | — | Fernet 加密的密文字节 |
| config | `CryptoConfig` | — | 必须包含 `fernet_key` |
| ttl | `int \| None` | `None` | 生存时间（秒），超过则视为过期 |

返回解密后的 UTF-8 字符串。

**异常**：
- `DecryptionError` — 解密失败
- `InvalidKeyError` — `fernet_key` 为空或无效

---

### 签名与哈希 (sign.py)

#### `sign(data: bytes, key: bytes) -> str`

使用 HMAC-SHA256 对数据签名。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| data | `bytes` | — | 待签名的数据 |
| key | `bytes` | — | 签名密钥 |

返回十六进制编码的 HMAC-SHA256 签名（64 字符）。纯标准库实现，无外部依赖。

---

#### `verify(data: bytes, key: bytes, signature: str) -> bool`

验证 HMAC-SHA256 签名，使用 `hmac.compare_digest` 进行常量时间比较以抵抗时序攻击。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| data | `bytes` | — | 原始数据 |
| key | `bytes` | — | 签名密钥 |
| signature | `str` | — | 待验证的十六进制签名 |

返回 `True` 表示签名匹配，`False` 表示不匹配。不抛异常。

---

#### `sha256(data: bytes) -> str`

计算 SHA-256 哈希。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| data | `bytes` | — | 待哈希的数据 |

返回十六进制编码的 SHA-256 哈希（64 字符）。纯标准库实现。

---

#### `sha256_hex = sha256`

`sha256_hex` 是 `sha256` 的别名，两者完全等价。

---

### 密钥派生 (kdf.py)

#### `derive_key_hkdf(master_key: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes`

使用 HKDF（HMAC-based Extract-and-Expand Key Derivation Function）从主密钥派生子密钥。

适用于已有高熵主密钥（如 32 字节随机密钥）的密钥扩展场景。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| master_key | `bytes` | — | 主密钥（高熵随机数据） |
| salt | `bytes` | — | 盐值（随机但不要求保密） |
| info | `bytes` | — | 上下文信息，不同 info 派生出不同密钥 |
| length | `int` | `32` | 输出密钥长度（字节） |

返回派生出的密钥字节。

---

#### `derive_key_pbkdf2(password: bytes, salt: bytes, iterations: int = 600000, length: int = 32) -> bytes`

使用 PBKDF2-HMAC-SHA256 从密码派生密钥。

适用于低熵密码的密钥派生场景，通过高迭代次数抵抗暴力破解。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| password | `bytes` | — | 用户密码（低熵） |
| salt | `bytes` | — | 盐值（随机且唯一） |
| iterations | `int` | `600000` | 迭代次数，OWASP 2025 推荐 ≥ 600,000 |
| length | `int` | `32` | 输出密钥长度（字节） |

返回派生出的密钥字节。

**安全提示**：OWASP 2025 推荐 PBKDF2-SHA256 迭代次数不低于 600,000。默认值已满足此要求，调低会降低安全性。

---

### 配置与异常

#### `CryptoConfig` (Pydantic BaseModel)

密码学配置。所有密码学操作共享此配置。

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| argon2_memory_cost | `int` | `65536` | Argon2id 内存开销 (KB)，OWASP 推荐 65536 (64MB) |
| argon2_time_cost | `int` | `3` | Argon2id 迭代次数，OWASP 推荐 3 |
| argon2_parallelism | `int` | `1` | Argon2id 并行度 |
| argon2_hash_len | `int` | `32` | Argon2id 哈希输出长度（字节） |
| argon2_salt_len | `int` | `16` | Argon2id 盐长度（字节） |
| token_bytes | `int` | `32` | 生成的随机 token 字节数 |
| fernet_key | `str` | `""` | Fernet 加密密钥（base64 url-safe 字符串），为空时需显式提供 |

**安全提示**：Argon2id 默认参数（64MB 内存、3 次迭代）符合 OWASP 2025 推荐基线。仅在硬件资源受限且有明确理由时调低，调低会降低抵抗 GPU/ASIC 破解的能力。

```python
from basic_tool.crypto import CryptoConfig, generate_fernet_key

# 默认配置（OWASP 推荐参数）
config = CryptoConfig()

# 自定义配置（同时设置加密密钥）
config = CryptoConfig(
    argon2_memory_cost=131072,  # 128MB，更高安全性
    fernet_key=generate_fernet_key(),
)
```

---

#### 异常类型

所有异常继承自 `CryptoError`，便于上层统一捕获。

```
CryptoError                       # 基础异常
├── DecryptionError               # 解密失败（密钥错误、密文损坏、TTL 过期）
├── SignatureVerificationError    # 签名验证失败
└── InvalidKeyError               # 密钥无效
```

| 异常 | 抛出场景 |
|------|----------|
| `CryptoError` | 基础异常，一般不直接抛出，用于统一捕获 |
| `DecryptionError` | `decrypt` / `decrypt_str` 解密失败时抛出 |
| `SignatureVerificationError` | 签名验证相关错误（当前 `sign.verify` 返回布尔值不抛此异常，保留供未来使用） |
| `InvalidKeyError` | `fernet_key` 为空或格式无效时抛出 |

---

## 使用示例

### 密码哈希

```python
from basic_tool.crypto import hash_password, verify_password, needs_rehash

# 注册时哈希密码
password = "user_password_123"
hashed = hash_password(password)
# '$argon2id$v=19$m=65536,t=3,p=1$c2FsdHNhbHQ...'

# 存入数据库后，登录时验证
is_valid = verify_password(password, hashed)
# True

is_valid = verify_password("wrong_password", hashed)
# False

# 登录成功后检查是否需要升级哈希参数
if verify_password(password, hashed) and needs_rehash(hashed):
    new_hashed = hash_password(password)
    # 更新数据库中的哈希
```

### Token 生成

```python
from basic_tool.crypto import generate_token, generate_hex_token

# URL-safe Token（适合放入 URL，如密码重置链接）
api_token = generate_token()
# 'a3Bf2xKp9wQ_rT5mN8vL1yH4...'

# 指定长度
short_token = generate_token(length=16)

# 十六进制 Token（适合数据库存储、OTP）
hex_token = generate_hex_token()
# 'f3a2b1c4d5e6f7a8b9c0d1e2f3a4b5c6...'

# 用于 API Key
api_key = generate_token(length=48)
```

### 对称加密

```python
from basic_tool.crypto import (
    CryptoConfig,
    generate_fernet_key,
    encrypt_str,
    decrypt_str,
)

# 生成密钥（只需一次，安全存储到环境变量或密钥管理服务）
key = generate_fernet_key()
config = CryptoConfig(fernet_key=key)

# 加密字符串
plaintext = "sensitive data to encrypt"
ciphertext = encrypt_str(plaintext, config)

# 解密
decrypted = decrypt_str(ciphertext, config)
# 'sensitive data to encrypt'

# 带 TTL 的加密（如临时令牌，60 秒后过期）
import time
ciphertext = encrypt_str("temporary secret", config)
time.sleep(1)
decrypted = decrypt_str(ciphertext, config, ttl=60)
```

### HMAC 签名

```python
from basic_tool.crypto import sign, verify, sha256

# 签名 Webhook 请求体
secret_key = b"webhook_signing_secret"
payload = b'{"event":"order.created","id":12345}'
signature = sign(payload, secret_key)
# 'a1b2c3d4e5f6...'

# 接收方验证签名
is_valid = verify(payload, secret_key, signature)
# True

# 篡改后验证失败
is_valid = verify(b'{"event":"order.deleted"}', secret_key, signature)
# False

# 计算文件指纹（无密钥哈希）
fingerprint = sha256(b"file content here")
# '9f86d081884c7d65...'
```

### 密钥派生

```python
from basic_tool.crypto import derive_key_hkdf, derive_key_pbkdf2

# HKDF: 从主密钥派生多个子密钥（用于加密不同数据域）
master_key = b"32-byte-high-entropy-random-key!!!!!"
salt = b"application_salt_2025"

encryption_key = derive_key_hkdf(
    master_key=master_key,
    salt=salt,
    info=b"user_data_encryption",
)
auth_key = derive_key_hkdf(
    master_key=master_key,
    salt=salt,
    info=b"session_signing",
)
# 两个密钥互不相同

# PBKDF2: 从用户密码派生密钥（用于本地加密）
password = b"user_password_123"
user_salt = b"unique_per_user_salt_16B"
derived = derive_key_pbkdf2(
    password=password,
    salt=user_salt,
    iterations=600000,  # OWASP 2025 推荐
)
# 32 字节密钥
```
