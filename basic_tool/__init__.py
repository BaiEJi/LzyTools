"""
basic_tool — 基础设施库，提供与 Web 框架无关的通用能力。

当前模块:
- redis: Redis 异步客户端，支持连接池管理、分布式锁、缓存装饰器
- logger: Loguru 日志系统，自定义格式 level||file:line||k1=v1||k2=v2||message
- email: 异步邮件发送模块，支持 SMTP 发送、Jinja2 模板渲染、批量发送、测试模式
- concurrency: 异步并发工具集，提供批量并发执行、并发限流、超时保护、重试和错误聚合能力
- crypto: 密码学工具集，提供密码哈希、对称加密、签名验证、密钥派生等能力
- context: 请求级上下文管理，基于 ContextVar 实现日志注入、HTTP 透传、FastAPI 中间件
- metrics: 指标采集、Redis Streams 缓冲、VictoriaMetrics 持久化、PromQL 查询、告警评估、健康检查
"""
