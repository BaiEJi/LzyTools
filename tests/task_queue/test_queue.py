"""TaskQueue 生产者端测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from basic_tool.task_queue.config import TaskConfig
from basic_tool.task_queue.queue import TaskQueue
from basic_tool.task_queue.task import _REGISTRY, _TASK_META, task


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


@pytest.fixture
def queue(config):
    """TaskQueue 实例（未初始化）。"""
    return TaskQueue(config)


@pytest.fixture
def initialized_queue(config):
    """TaskQueue 实例（已初始化，mock Redis）。"""
    q = TaskQueue(config)
    q._redis = AsyncMock()
    return q


class TestTaskQueueInit:
    """TaskQueue 初始化测试。"""

    def test_init_stores_config(self, queue, config):
        """初始化存储配置。"""
        assert queue._config is config
        assert queue._redis is None

    def test_client_before_init_raises(self, queue):
        """未初始化时访问 client 抛出 RuntimeError。"""
        with pytest.raises(RuntimeError, match="未初始化"):
            _ = queue.client

    @pytest.mark.asyncio
    async def test_init_creates_pool(self, queue):
        """init() 创建 ARQ Redis 连接池。"""
        mock_pool = AsyncMock()

        with patch("arq.connections.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            with patch("arq.connections.RedisSettings") as mock_settings:
                mock_settings.from_url.return_value = MagicMock()
                await queue.init()

        assert queue._redis is mock_pool

    @pytest.mark.asyncio
    async def test_init_idempotent(self, queue):
        """重复 init() 不会创建新连接池。"""
        mock_pool = AsyncMock()

        with patch("arq.connections.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            with patch("arq.connections.RedisSettings") as mock_settings:
                mock_settings.from_url.return_value = MagicMock()
                await queue.init()
                await queue.init()

        assert queue._redis is mock_pool

    @pytest.mark.asyncio
    async def test_close(self, queue):
        """close() 关闭连接池。"""
        mock_pool = AsyncMock()

        with patch("arq.connections.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            with patch("arq.connections.RedisSettings") as mock_settings:
                mock_settings.from_url.return_value = MagicMock()
                await queue.init()

        await queue.close()
        assert queue._redis is None
        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_when_not_initialized(self, queue):
        """未初始化时 close() 不报错。"""
        await queue.close()  # 应该静默通过


class TestTaskQueueEnqueue:
    """TaskQueue 入队测试。"""

    @pytest.mark.asyncio
    async def test_enqueue_success(self, initialized_queue):
        """入队成功返回 job_id。"""

        @task()
        async def send_email(ctx, to: str):
            pass

        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        initialized_queue._redis.enqueue_job = AsyncMock(return_value=mock_job)

        job_id = await initialized_queue.enqueue("send_email", "user@example.com")

        assert job_id == "job-123"
        initialized_queue._redis.enqueue_job.assert_called_once_with(
            "send_email",
            "user@example.com",
            _queue_name="test:queue",
            _job_id=None,
            _defer_by=None,
            _defer_until=None,
            _expires=None,
        )

    @pytest.mark.asyncio
    async def test_enqueue_with_options(self, initialized_queue):
        """入队时传递所有可选参数。"""

        @task()
        async def send_email(ctx, to: str):
            pass

        mock_job = MagicMock()
        mock_job.job_id = "job-456"
        initialized_queue._redis.enqueue_job = AsyncMock(return_value=mock_job)

        job_id = await initialized_queue.enqueue(
            "send_email",
            "user@example.com",
            _job_id="dedup-1",
            _defer_by=30,
            _expires=3600,
        )

        assert job_id == "job-456"
        initialized_queue._redis.enqueue_job.assert_called_once_with(
            "send_email",
            "user@example.com",
            _queue_name="test:queue",
            _job_id="dedup-1",
            _defer_by=30,
            _defer_until=None,
            _expires=3600,
        )

    @pytest.mark.asyncio
    async def test_enqueue_duplicate_returns_none(self, initialized_queue):
        """去重时返回 None。"""

        @task()
        async def send_email(ctx, to: str):
            pass

        initialized_queue._redis.enqueue_job = AsyncMock(return_value=None)

        job_id = await initialized_queue.enqueue("send_email", "user@example.com", _job_id="dedup-1")
        assert job_id is None

    @pytest.mark.asyncio
    async def test_enqueue_unregistered_task_logs_warning(self, initialized_queue):
        """入队未注册任务时记录警告但仍入队。"""
        mock_job = MagicMock()
        mock_job.job_id = "job-789"
        initialized_queue._redis.enqueue_job = AsyncMock(return_value=mock_job)

        job_id = await initialized_queue.enqueue("nonexistent_task")
        assert job_id == "job-789"


class TestTaskQueueJobOps:
    """TaskQueue 任务操作测试。"""

    @pytest.mark.asyncio
    async def test_job_status(self, initialized_queue):
        """查询任务状态。"""
        mock_job = MagicMock()
        mock_job.status = AsyncMock(return_value="complete")

        with patch("arq.jobs.Job", return_value=mock_job):
            result = await initialized_queue.job_status("job-123")

        assert result == {"job_id": "job-123", "status": "complete"}

    @pytest.mark.asyncio
    async def test_job_result(self, initialized_queue):
        """获取任务结果。"""
        mock_job = MagicMock()
        mock_job.result = AsyncMock(return_value="done")

        with patch("arq.jobs.Job", return_value=mock_job):
            result = await initialized_queue.job_result("job-123", timeout=5.0)

        assert result == "done"
        mock_job.result.assert_called_once_with(timeout=5.0)

    @pytest.mark.asyncio
    async def test_abort_job_success(self, initialized_queue):
        """中止任务成功。"""
        mock_job = MagicMock()
        mock_job.abort = AsyncMock(return_value=True)

        with patch("arq.jobs.Job", return_value=mock_job):
            result = await initialized_queue.abort_job("job-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_abort_job_failed(self, initialized_queue):
        """中止任务失败（不存在或已完成）。"""
        mock_job = MagicMock()
        mock_job.abort = AsyncMock(return_value=False)

        with patch("arq.jobs.Job", return_value=mock_job):
            result = await initialized_queue.abort_job("job-123")

        assert result is False
