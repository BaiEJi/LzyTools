"""ARQ 任务队列配置。

使用 Pydantic 模型统一管理 ARQ Worker 和队列的所有配置参数。
"""

from pydantic import BaseModel


class TaskConfig(BaseModel):
    """ARQ 任务队列配置。

    Attributes:
        redis_url: Redis 连接地址。
        queue_name: 队列名称。
        max_jobs: Worker 最大并发任务数。
        job_timeout: 单个任务超时秒数。
        max_tries: 默认最大重试次数。
        keep_result: 任务结果保留秒数。
        health_check_interval: 健康检查间隔秒数。
        poll_delay: 轮询新任务间隔秒数。
    """

    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "arq:queue"
    max_jobs: int = 10
    job_timeout: int = 300
    max_tries: int = 5
    keep_result: int = 3600
    health_check_interval: int = 60
    poll_delay: float = 0.5
