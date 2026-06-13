"""FastAPI 异常处理器测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from basic_tool.errors.app_error import AppError
from basic_tool.errors.codes import CommonErrors
from basic_tool.errors.handler import setup_error_handlers


class TestSetupErrorHandlers:
    """setup_error_handlers 测试。"""

    def test_setup_without_error(self):
        """setup_error_handlers 注册不报错。"""
        app = FastAPI()
        setup_error_handlers(app)

    def test_app_error_handler(self):
        """AppError 返回对应状态码和标准化 JSON。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/error")
        async def error_endpoint():
            raise AppError(code="TEST_ERR", message="test error", http_status=400)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/error")
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "TEST_ERR"
        assert data["message"] == "test error"
        assert "context" not in data

    def test_validation_error_handler(self):
        """RequestValidationError 返回 422 和 PARAM_INVALID 格式。"""
        app = FastAPI()
        setup_error_handlers(app)

        class Item(BaseModel):
            name: str
            price: float

        @app.post("/items")
        async def create_item(item: Item):
            return item

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/items", json={"name": "test"})
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "PARAM_INVALID"
        assert "errors" in data

    def test_global_exception_handler(self):
        """未捕获异常返回 500 和 INTERNAL_ERROR 格式。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/crash")
        async def crash():
            raise RuntimeError("Something broke")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/crash")
        assert resp.status_code == 500
        data = resp.json()
        assert data["code"] == "INTERNAL_ERROR"
        assert "Something broke" not in data.get("message", "")

    def test_normal_request_unaffected(self):
        """正常请求不受异常处理器影响。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/ok")
        async def ok():
            return {"status": "ok"}

        client = TestClient(app)
        resp = client.get("/ok")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_app_error_with_context(self):
        """include_context=True 时响应包含 context。"""
        from basic_tool.errors.config import ErrorConfig

        app = FastAPI()
        setup_error_handlers(app, config=ErrorConfig(include_context=True))

        @app.get("/error")
        async def error_endpoint():
            raise AppError(code="CTX", message="with context", http_status=400, context={"key": "val"})

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/error")
        data = resp.json()
        assert "context" in data
        assert data["context"] == {"key": "val"}
