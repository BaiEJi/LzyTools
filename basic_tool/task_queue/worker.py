"""ARQ Worker 运行器和配置生成器。

封装 Worker 生命周期、信号处理、优雅关闭。
自动从 @task 注册表收集任务函数生成 WorkerSettings。
"""

import signal
from typing import Any, Callable

from loguru import logger

from basic_tool.context.propagation import deserialize_context
from basic_tool.errors import AppError
from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.task import get_registry, get_task_meta


def build_settings(
    config: TaskConfig,
    on_startup: Callable | None = None,
    on_shutdown: Callable | None = None,
) -> type:
    """从 TaskConfig + @task 注册表自动生成 WorkerSettings 类。

    自动收集所有 @task 注册的函数，合并到 functions 列表。
    用户的 on_startup/on_shutdown 回调会与内部日志回调链式调用。

    Args:
        config: 任务队列配置。
        on_startup: Worker 启动回调，接收 ctx 参数。
        on_shutdown: Worker 关闭回调，接收 ctx 参数。

    Returns:
        可直接传给 arq.Worker 的 Settings 类。
    """
    from arq.connections import RedisSettings

    registry = get_registry()
    functions = list(registry.values())

    async def _on_startup(ctx: dict) -> None:
        """Worker 启动回调。"""
        logger.info("Worker 启动 | queue={} max_jobs={}", config.queue_name, config.max_jobs)
        if on_startup:
            await on_startup(ctx)

    async def _on_shutdown(ctx: dict) -> None:
        """Worker 关闭回调。"""
        logger.info("Worker 关闭 | queue={}", config.queue_name)
        if on_shutdown:
            await on_shutdown(ctx)

    async def _on_job_start(ctx: dict) -> None:
        """任务开始回调。"""
        logger.info("任务开始执行 | job_id={}", ctx.get("job_id"))

    async def _on_job_end(ctx: dict) -> None:
        """任务结束回调。"""
        logger.info("任务执行完成 | job_id={}", ctx.get("job_id"))

    # 构造 per-task 函数包装，注入独立的 max_tries / job_timeout
    wrapped_functions = []
    for func in functions:
        meta = get_task_meta(func.__name__) or {}
        max_tries = meta.get("max_tries")
        job_timeout = meta.get("job_timeout")
        func = _wrap_function(func, max_tries=max_tries, job_timeout=job_timeout)
        wrapped_functions.append(func)

    settings_class = type("WorkerSettings", (), {
        "functions": wrapped_functions,
        "redis_settings": RedisSettings.from_url(config.redis_url),
        "queue_name": config.queue_name,
        "max_jobs": config.max_jobs,
        "job_timeout": config.job_timeout,
        "max_tries": config.max_tries,
        "keep_result": config.keep_result,
        "health_check_interval": config.health_check_interval,
        "poll_delay": config.poll_delay,
        "on_startup": _on_startup,
        "on_shutdown": _on_shutdown,
        "on_job_start": _on_job_start,
        "on_job_end": _on_job_end,
    })

    logger.info("WorkerSettings 生成完成 | tasks={} queue={}", [f.__name__ for f in wrapped_functions], config.queue_name)
    return settings_class


def _wrap_function(func: Callable, max_tries: int | None = None, job_timeout: int | None = None) -> Callable:
    """为任务函数包装 per-task 配置、上下文恢复和业务异常处理。

    ARQ 通过函数属性 `max_tries` 和 `job_timeout` 实现 per-task 配置。
    入队时序列化的请求上下文通过 _context_snapshot kwarg 传入，
    包装器在执行前恢复上下文（deserialize_context），实现跨进程传播。
    AppError 被视为业务异常：记录 WARNING 后返回错误标记字典，不触发 ARQ 重试。
    其他异常照常抛出，由 ARQ 按重试策略处理。

    Args:
        func: 原始任务函数。
        max_tries: 此任务的最大重试次数。
        job_timeout: 此任务的超时秒数。

    Returns:
        包装后的函数（恢复上下文、捕获 AppError、保留配置属性）。
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        snapshot = kwargs.pop("_context_snapshot", None)

        async def _execute() -> Any:
            try:
                return await func(*args, **kwargs)
            except AppError as exc:
                logger.warning(
                    "task 业务异常 跳过重试 | code={} message={}",
                    exc.code,
                    exc.message,
                )
                return {"_error": True, "code": exc.code, "message": exc.message}

        if snapshot:
            async with deserialize_context(snapshot):
                return await _execute()
        return await _execute()

    if max_tries is not None:
        wrapper.max_tries = max_tries
    if job_timeout is not None:
        wrapper.job_timeout = job_timeout

    return wrapper


class WorkerRunner:
    """ARQ Worker 运行器，封装生命周期和信号处理。

    使用示例::

        config = TaskConfig(max_jobs=5)
        runner = WorkerRunner(config)
        await runner.run()  # 阻塞直到 SIGINT/SIGTERM

        # 或 burst 模式（队列空自动退出）
        await runner.run(burst=True)

        # 带启动/关闭回调
        async def on_startup(ctx):
            ctx["db"] = await create_db_pool()

        runner = WorkerRunner(config, on_startup=on_startup)
        await runner.run()
    """

    def __init__(
        self,
        config: TaskConfig,
        on_startup: Callable | None = None,
        on_shutdown: Callable | None = None,
    ) -> None:
        """初始化 WorkerRunner。

        Args:
            config: 任务队列配置。
            on_startup: Worker 启动回调。
            on_shutdown: Worker 关闭回调。
        """
        self._config = config
        self._on_startup = on_startup
        self._on_shutdown = on_shutdown

    async def run(self, burst: bool = False) -> None:
        """运行 Worker。

        阻塞直到收到 SIGINT/SIGTERM 信号或 burst 模式下队列为空。

        Args:
            burst: True 表示队列空后自动退出。
        """
        from arq import Worker

        settings = build_settings(
            self._config,
            on_startup=self._on_startup,
            on_shutdown=self._on_shutdown,
        )

        worker = Worker(settings)

        # 注册信号处理
        loop = None
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: worker.handle_sigterm())
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            pass

        logger.info("Worker 开始运行 | queue={} burst={}", self._config.queue_name, burst)

        if burst:
            await worker.async_run()
        else:
            await worker.async_run()

        logger.info("Worker 已退出 | queue={}", self._config.queue_name)
