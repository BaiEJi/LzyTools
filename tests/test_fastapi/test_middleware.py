"""中间件和异常处理器测试。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from basic_tool.fastapi.middleware import AppError, RequestLoggingMiddleware, setup_error_handlers


class TestAppError:
    """AppError 异常测试。"""

    def test_app_error_attributes(self):
        """AppError 正确存储 status_code 和 detail。"""
        err = AppError(404, "Not found")
        assert err.status_code == 404
        assert err.detail == "Not found"

    def test_app_error_is_exception(self):
        """AppError 是 Exception 子类。"""
        err = AppError(400, "Bad request")
        assert isinstance(err, Exception)
        assert str(err) == "Bad request"


class TestRequestLoggingMiddleware:
    """请求日志中间件测试。"""

    def test_request_id_in_response(self):
        """响应头包含 X-Request-ID。"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        # uuid hex 长度 32
        assert len(resp.headers["X-Request-ID"]) == 32

    def test_request_id_unique_per_request(self):
        """每个请求的 request_id 不同。"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        resp1 = client.get("/test")
        resp2 = client.get("/test")
        assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]


class TestSetupErrorHandlers:
    """全局异常处理器测试。"""

    def test_app_error_handler(self):
        """AppError 返回对应状态码和 detail。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/error")
        async def error_endpoint():
            raise AppError(422, "Invalid input")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/error")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "Invalid input"

    def test_validation_error_handler(self):
        """请求验证失败返回 422。"""
        from pydantic import BaseModel

        app = FastAPI()
        setup_error_handlers(app)

        class Item(BaseModel):
            name: str
            price: float

        @app.post("/items")
        async def create_item(item: Item):
            return item

        client = TestClient(app, raise_server_exceptions=False)
        # 缺少必填字段
        resp = client.post("/items", json={"name": "test"})
        assert resp.status_code == 422
        data = resp.json()
        assert "errors" in data

    def test_generic_exception_handler(self):
        """未捕获异常返回 500。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/crash")
        async def crash():
            raise RuntimeError("Something broke")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/crash")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"

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
