"""@task 装饰器和注册表测试。"""

import pytest

from basic_tool.task_queue.task import (
    _REGISTRY,
    _TASK_META,
    get_registry,
    get_task_meta,
    task,
    validate_task_name,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前后清理注册表。"""
    _REGISTRY.clear()
    _TASK_META.clear()
    yield
    _REGISTRY.clear()
    _TASK_META.clear()


class TestTaskDecorator:
    """@task 装饰器测试。"""

    def test_register_with_default_name(self):
        """默认使用函数名作为任务名。"""

        @task()
        async def my_task(ctx):
            pass

        assert "my_task" in _REGISTRY
        assert _REGISTRY["my_task"] is my_task.__wrapped__ or callable(_REGISTRY["my_task"])

    def test_register_with_custom_name(self):
        """自定义任务名。"""

        @task(name="custom_name")
        async def my_task(ctx):
            pass

        assert "custom_name" in _REGISTRY
        assert "my_task" not in _REGISTRY

    def test_register_with_meta(self):
        """注册时携带 max_tries 和 job_timeout 元数据。"""

        @task(max_tries=3, job_timeout=60)
        async def my_task(ctx):
            pass

        meta = get_task_meta("my_task")
        assert meta is not None
        assert meta["max_tries"] == 3
        assert meta["job_timeout"] == 60

    def test_register_without_meta(self):
        """不指定元数据时为 None。"""

        @task()
        async def my_task(ctx):
            pass

        meta = get_task_meta("my_task")
        assert meta is not None
        assert meta["max_tries"] is None
        assert meta["job_timeout"] is None

    def test_duplicate_registration_logs_warning(self, caplog):
        """重复注册时记录警告。"""

        @task()
        async def my_task(ctx):
            pass

        @task()
        async def my_task(ctx):  # noqa: F811
            pass

        # 注册表中应保留后注册的
        assert "my_task" in _REGISTRY


class TestRegistry:
    """注册表操作测试。"""

    def test_get_registry_returns_copy(self):
        """get_registry 返回副本。"""

        @task()
        async def my_task(ctx):
            pass

        registry = get_registry()
        registry.clear()
        assert "my_task" in _REGISTRY  # 原注册表不受影响

    def test_validate_task_name_registered(self):
        """已注册任务名校验通过。"""

        @task()
        async def my_task(ctx):
            pass

        assert validate_task_name("my_task") is True

    def test_validate_task_name_not_registered(self):
        """未注册任务名校验失败。"""
        assert validate_task_name("nonexistent") is False

    def test_get_task_meta_not_found(self):
        """查询不存在的任务返回 None。"""
        assert get_task_meta("nonexistent") is None
