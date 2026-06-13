"""
basic_tool — 基础设施库，提供与 Web 框架无关的通用能力。

当前模块:
- redis: Redis 异步客户端，支持连接池管理、分布式锁、缓存装饰器
- logger: Loguru 日志系统，自定义格式 level||file:line||k1=v1||k2=v2||message
- email: 异步邮件发送模块，支持 SMTP 发送、Jinja2 模板渲染、批量发送、测试模式
- concurrency: 异步并发工具集，提供批量并发执行、并发限流、超时保护、重试和错误聚合能力
"""
