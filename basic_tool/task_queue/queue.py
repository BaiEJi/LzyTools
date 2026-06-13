"""ARQ 任务队列生产者端。

负责入队任务、查询任务状态、健康检查。
对接 FastAPI lifespan：init() / close()。
"""

import time
from typing import Any

from loguru import logger

from basic_tool.context.propagation import serialize_context
from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.task import validate_task_name


class TaskQueue:
    """ARQ 任务队列生产者端。

    负责入队任务、查询任务状态、健康检查。
    对接 FastAPI lifespan：init() / close()。

    使用示例::

        config = TaskConfig(redis_url="redis://localhost:6379/0")
        queue = TaskQueue(config)
        await queue.init()

        # 入队
        job_id = await queue.enqueue("send_email", "user@example.com", "Hello")

        # 查询状态
        status = await queue.job_status(job_id)
        result = await queue.job_result(job_id, timeout=10)

        await queue.close()
    """

    def __init__(self, config: TaskConfig) -> None:
        """初始化 TaskQueue。

        Args:
            config: 任务队列配置。
        """
        self._config = config
        self._redis = None

    @property
    def client(self):
        """返回底层 ArqRedis 实例。

        Returns:
            ArqRedis 连接实例。

        Raises:
            RuntimeError: 未调用 init() 时访问。
        """
        if self._redis is None:
            raise RuntimeError("TaskQueue 未初始化，请先调用 await init()")
        return self._redis

    async def init(self) -> None:
        """初始化 ARQ Redis 连接池。

        幂等操作：已初始化时直接返回。

        Raises:
            连接失败时抛出原始异常。
        """
        if self._redis is not None:
            logger.warning("TaskQueue 已初始化，跳过重复初始化")
            return

        try:
            from arq.connections import RedisSettings, create_pool

            settings = RedisSettings.from_url(self._config.redis_url)
            self._redis = await create_pool(settings)
            logger.info("TaskQueue 连接池初始化完成 | redis_url={} queue={}", self._config.redis_url, self._config.queue_name)
        except Exception as e:
            logger.error("TaskQueue 连接池初始化失败 | redis_url={} error={}", self._config.redis_url, e)
            self._redis = None
            raise

    async def close(self) -> None:
        """关闭 ARQ Redis 连接池。"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            logger.info("TaskQueue 连接池已关闭")

    async def enqueue(
        self,
        name: str,
        *args: Any,
        _job_id: str | None = None,
        _defer_by: int | float | None = None,
        _defer_until: Any = None,
        _expires: int | None = None,
    ) -> str | None:
        """入队一个任务。

        自动序列化当前请求上下文（trace_id、user_id 等）随任务传递，
        Worker 执行时通过 _wrap_function 恢复上下文，实现跨进程传播。
        无活跃上下文时传递空字典，Worker 端跳过恢复。

        Args:
            name: 任务名称（必须已在 @task 注册表中）。
            *args: 任务参数（不含 ctx，Worker 自动注入）。
            _job_id: 任务 ID，用于去重。相同 ID 的任务不会重复入队。
            _defer_by: 延迟执行秒数。
            _defer_until: 延迟到指定时间执行。
            _expires: 任务过期秒数，超时未执行则丢弃。

        Returns:
            任务 ID，任务已存在（去重）时返回 None。
        """
        validate_task_name(name)

        # 序列化当前请求上下文，供 Worker 进程恢复
        ctx_snapshot = serialize_context()

        logger.info(
            "任务入队 | name={} job_id={} defer_by={} expires={}",
            name, _job_id, _defer_by, _expires,
        )

        job = await self.client.enqueue_job(
            name,
            *args,
            _context_snapshot=ctx_snapshot,
            _queue_name=self._config.queue_name,
            _job_id=_job_id,
            _defer_by=_defer_by,
            _defer_until=_defer_until,
            _expires=_expires,
        )

        if job is None:
            logger.warning("任务已存在（去重） | name={} job_id={}", name, _job_id)
            return None

        logger.info("任务入队成功 | name={} job_id={}", name, job.job_id)
        return job.job_id

    async def job_status(self, job_id: str) -> dict:
        """查询任务状态。

        Args:
            job_id: 任务 ID。

        Returns:
            状态字典，包含 job_id 和 status 字段。
        """
        from arq.jobs import Job

        job = Job(job_id, redis=self.client)
        status = await job.status()
        return {"job_id": job_id, "status": str(status)}

    async def job_result(self, job_id: str, timeout: float = 10.0) -> Any:
        """获取任务结果（阻塞等待）。

        Args:
            job_id: 任务 ID。
            timeout: 等待超时秒数。

        Returns:
            任务函数的返回值。

        Raises:
            任务失败时抛出任务异常。
        """
        from arq.jobs import Job

        job = Job(job_id, redis=self.client)
        return await job.result(timeout=timeout)

    async def abort_job(self, job_id: str) -> bool:
        """中止一个任务。

        Args:
            job_id: 任务 ID。

        Returns:
            True 表示成功中止，False 表示任务不存在或已完成。
        """
        from arq.jobs import Job

        job = Job(job_id, redis=self.client)
        aborted = await job.abort()
        if aborted:
            logger.info("任务已中止 | job_id={}", job_id)
        else:
            logger.warning("任务中止失败（不存在或已完成） | job_id={}", job_id)
        return aborted
