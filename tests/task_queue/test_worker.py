"""WorkerRunner 和 build_settings 测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from basic_tool.errors import AppError
from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.task import _REGISTRY, _TASK_META, task
from basic_tool.task_queue.worker import WorkerRunner, build_settings, _wrap_function


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前后清理注册表。"""
    _REGISTRY.clear()
    _TASK_META.clear()
    yield
    _REGISTRY.clear()
    _TASK_META.clear()


@pytest.fixture
def config():
    """TaskConfig 实例。"""
    return TaskConfig(redis_url="redis://localhost:6379/0", queue_name="test:queue")


class TestBuildSettings:
    """build_settings 测试。"""

    def test_collects_registered_tasks(self, config):
        """自动收集注册表中的任务函数。"""

        @task()
        async def task_a(ctx):
            pass

        @task()
        async def task_b(ctx):
            pass

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            settings = build_settings(config)

        func_names = [f.__name__ for f in settings.functions]
        assert "task_a" in func_names
        assert "task_b" in func_names

    def test_applies_per_task_meta(self, config):
        """per-task 配置通过函数属性传递给 ARQ。"""

        @task(max_tries=3, job_timeout=60)
        async def my_task(ctx):
            pass

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            settings = build_settings(config)

        # 找到包装后的函数
        func = settings.functions[0]
        assert func.max_tries == 3
        assert func.job_timeout == 60

    def test_settings_has_lifecycle_hooks(self, config):
        """Settings 包含生命周期回调。"""

        @task()
        async def my_task(ctx):
            pass

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            settings = build_settings(config)

        assert hasattr(settings, "on_startup")
        assert hasattr(settings, "on_shutdown")
        assert hasattr(settings, "on_job_start")
        assert hasattr(settings, "on_job_end")
        assert callable(settings.on_startup)
        assert callable(settings.on_shutdown)

    def test_settings_config_values(self, config):
        """Settings 从 TaskConfig 正确读取配置值。"""

        @task()
        async def my_task(ctx):
            pass

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            settings = build_settings(config)

        assert settings.queue_name == "test:queue"
        assert settings.max_jobs == 10
        assert settings.job_timeout == 300
        assert settings.max_tries == 5
        assert settings.keep_result == 3600
        assert settings.health_check_interval == 60
        assert settings.poll_delay == 0.5

    def test_custom_lifecycle_callbacks(self, config):
        """自定义生命周期回调被正确链式调用。"""
        called = []

        async def my_startup(ctx):
            called.append("startup")

        async def my_shutdown(ctx):
            called.append("shutdown")

        @task()
        async def my_task(ctx):
            pass

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            settings = build_settings(config, on_startup=my_startup, on_shutdown=my_shutdown)

        # 模拟调用
        import asyncio

        async def test_hooks():
            ctx = {}
            await settings.on_startup(ctx)
            await settings.on_shutdown(ctx)

        asyncio.run(test_hooks())
        assert "startup" in called
        assert "shutdown" in called


class TestWorkerRunner:
    """WorkerRunner 测试。"""

    def test_init_stores_config(self, config):
        """初始化存储配置。"""

        @task()
        async def my_task(ctx):
            pass

        runner = WorkerRunner(config)
        assert runner._config is config
        assert runner._on_startup is None
        assert runner._on_shutdown is None

    def test_init_stores_callbacks(self, config):
        """初始化存储回调。"""

        @task()
        async def my_task(ctx):
            pass

        async def on_startup(ctx):
            pass

        async def on_shutdown(ctx):
            pass

        runner = WorkerRunner(config, on_startup=on_startup, on_shutdown=on_shutdown)
        assert runner._on_startup is on_startup
        assert runner._on_shutdown is on_shutdown

    @pytest.mark.asyncio
    async def test_run_burst(self, config):
        """burst 模式运行 Worker。"""

        @task()
        async def my_task(ctx):
            pass

        mock_worker = AsyncMock()
        mock_worker.async_run = AsyncMock()
        mock_worker.handle_sigterm = MagicMock()

        with patch("arq.connections.RedisSettings") as mock_rs:
            mock_rs.from_url.return_value = MagicMock()
            with patch("arq.Worker", return_value=mock_worker):
                runner = WorkerRunner(config)
                await runner.run(burst=True)

        mock_worker.async_run.assert_called_once()


class TestWrapFunctionErrorHandling:
    """_wrap_function 的 AppError 跳过重试逻辑测试。"""

    @pytest.mark.asyncio
    async def test_app_error_not_retried_returns_error_dict(self):
        """AppError 被捕获，函数仅调用一次，返回错误标记字典。"""
        call_count = 0

        async def failing_task(ctx):
            nonlocal call_count
            call_count += 1
            raise AppError(code="BIZ_ERR", message="业务异常示例")

        wrapped = _wrap_function(failing_task, max_tries=3)
        result = await wrapped({})

        assert call_count == 1
        assert result == {"_error": True, "code": "BIZ_ERR", "message": "业务异常示例"}
        assert wrapped.max_tries == 3

    @pytest.mark.asyncio
    async def test_non_app_error_is_reraised_for_retry(self):
        """非 AppError 异常照常抛出，由 ARQ 按重试策略处理。"""
        call_count = 0

        async def failing_task(ctx):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("redis down")

        wrapped = _wrap_function(failing_task, max_tries=3)

        with pytest.raises(ConnectionError):
            await wrapped({})

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_normal_result_passes_through(self):
        """无异常时结果正常透传。"""

        async def ok_task(ctx, x):
            return x * 2

        wrapped = _wrap_function(ok_task)
        assert await wrapped({}, 21) == 42


class TestWrapFunctionContextPropagation:
    """_wrap_function 的请求上下文恢复测试。"""

    @pytest.mark.asyncio
    async def test_restores_context_from_snapshot(self):
        """从 _context_snapshot 恢复请求上下文。"""
        from basic_tool.context.ctx import ctx

        captured = {}

        async def my_task(arq_ctx):
            captured["trace_id"] = ctx.get("trace_id")
            captured["user_id"] = ctx.get("user_id")

        wrapped = _wrap_function(my_task)
        await wrapped({}, _context_snapshot={"trace_id": "abc-123", "user_id": 99})

        assert captured["trace_id"] == "abc-123"
        assert captured["user_id"] == 99

    @pytest.mark.asyncio
    async def test_no_snapshot_executes_without_context(self):
        """无 _context_snapshot 时正常执行（向后兼容）。"""
        from basic_tool.context.ctx import ctx

        captured = {}

        async def my_task(arq_ctx):
            captured["trace_id"] = ctx.get("trace_id")

        wrapped = _wrap_function(my_task)
        await wrapped({})

        assert captured["trace_id"] is None

    @pytest.mark.asyncio
    async def test_empty_snapshot_skips_restoration(self):
        """空字典快照跳过上下文恢复。"""
        from basic_tool.context.ctx import ctx

        captured = {}

        async def my_task(arq_ctx):
            captured["trace_id"] = ctx.get("trace_id")

        wrapped = _wrap_function(my_task)
        await wrapped({}, _context_snapshot={})

        assert captured["trace_id"] is None

    @pytest.mark.asyncio
    async def test_context_restored_only_during_execution(self):
        """上下文仅在任务执行期间生效，退出后恢复。"""
        from basic_tool.context.ctx import ctx

        async def my_task(arq_ctx):
            pass

        wrapped = _wrap_function(my_task)
        await wrapped({}, _context_snapshot={"trace_id": "temp-id"})

        assert ctx.get("trace_id") is None

    @pytest.mark.asyncio
    async def test_app_error_with_context_restoration(self):
        """上下文恢复与 AppError 处理组合工作正常。"""
        from basic_tool.context.ctx import ctx

        seen_trace_id = {}

        async def failing_task(arq_ctx):
            seen_trace_id["val"] = ctx.get("trace_id")
            raise AppError(code="BIZ_ERR", message="业务异常")

        wrapped = _wrap_function(failing_task, max_tries=3)
        result = await wrapped({}, _context_snapshot={"trace_id": "err-trace"})

        assert seen_trace_id["val"] == "err-trace"
        assert result == {"_error": True, "code": "BIZ_ERR", "message": "业务异常"}
