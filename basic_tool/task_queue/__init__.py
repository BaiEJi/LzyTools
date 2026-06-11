"""ARQ 任务队列 SDK。

基于 ARQ 的异步任务队列封装，提供统一配置、@task 装饰器注册、
结构化日志、健康检查和 Worker 生命周期管理。

使用示例::

    from basic_tool.task_queue import TaskConfig, TaskQueue, task, WorkerRunner

    # 1. 定义任务
    @task(max_tries=3)
    async def send_email(ctx, to: str, subject: str):
        ...

    # 2. 生产者端（FastAPI 应用）
    config = TaskConfig(redis_url="redis://localhost:6379/0")
    queue = TaskQueue(config)
    await queue.init()
    await queue.enqueue("send_email", "user@example.com", "Hello")

    # 3. 消费者端（Worker 进程）
    runner = WorkerRunner(config)
    await runner.run()
"""

from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.queue import TaskQueue
from basic_tool.task_queue.task import task, get_registry, validate_task_name
from basic_tool.task_queue.worker import WorkerRunner, build_settings

__all__ = [
    "TaskConfig",
    "TaskQueue",
    "WorkerRunner",
    "build_settings",
    "task",
    "get_registry",
    "validate_task_name",
]
