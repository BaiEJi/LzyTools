"""errors 模块测试公共 fixtures。"""

import pytest
from basic_tool.errors.registry import clear_registry


@pytest.fixture(autouse=True)
def _clear_error_registry():
    """每个测试前清空全局注册表，防止测试间污染。

    注意：CommonErrors 在 import 时注册，clear 后需在测试中重新 import。
    """
    clear_registry()
    yield
    clear_registry()
