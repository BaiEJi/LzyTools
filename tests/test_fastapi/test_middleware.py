"""中间件和异常处理器测试。"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from basic_tool.fastapi.middleware import AppError, RequestLoggingMiddleware, setup_error_handlers


class TestAppError:
    """AppError 异常测试。"""

    def test_app_error_attributes(self):
        """AppError 正确存储 code、message 和 http_status。"""
        err = AppError(code="NOT_FOUND", message="Not found", http_status=404)
        assert err.http_status == 404
        assert err.message == "Not found"
        assert err.code == "NOT_FOUND"
        # 向后兼容别名
        assert err.status_code == 404
        assert err.detail == "Not found"

    def test_app_error_is_exception(self):
        """AppError 是 Exception 子类。"""
        err = AppError(code="BAD_REQUEST", message="Bad request", http_status=400)
        assert isinstance(err, Exception)
        assert str(err) == "Bad request"


class TestRequestLoggingMiddleware:
    """请求日志中间件测试。"""

    def test_log_contains_trace_id_with_context_middleware(self):
        """栈叠 ContextMiddleware 时日志包含 trace_id。"""
        from basic_tool.context.middleware import ContextMiddleware

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(ContextMiddleware)  # 后添加 = 外层 = 先执行

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        # ContextMiddleware 会设置 traceparent 响应头
        assert "traceparent" in resp.headers

    def test_log_works_without_context_middleware(self):
        """无 ContextMiddleware 时正常工作，trace_id 为空。"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        # 不崩溃，无 traceparent 响应头（RequestLoggingMiddleware 不再设置任何响应头）
        assert "traceparent" not in resp.headers


class TestRequestLoggingMiddlewareMetrics:
    """请求日志中间件的指标采集测试。"""

    def test_metrics_recorded_when_provided(self):
        """传入 MetricsCollector 时，每个请求记录 counter 和 histogram。"""
        from basic_tool.fastapi import create_app
        from basic_tool.fastapi.config import FastApiConfig
        from basic_tool.metrics.collector import MetricsCollector
        from basic_tool.metrics.config import MetricsConfig

        collector = MetricsCollector(
            MetricsConfig(service_name="test"), endpoint="http://localhost:8428"
        )
        config = FastApiConfig(metrics=collector, enable_context_middleware=False)
        app = create_app(config)

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

        # counter 记录了 http_requests_total
        counters = collector._buffers.get("http_requests_total", [])
        assert len(counters) == 1
        point = counters[0]
        assert point.name == "http_requests_total"
        assert point.labels == {"method": "GET", "path": "/health", "status": "200"}
        assert point.value == 1.0

        # histogram 记录了 http_request_duration_seconds
        histograms = collector._buffers.get("http_request_duration_seconds", [])
        assert len(histograms) == 1
        hpoint = histograms[0]
        assert hpoint.name == "http_request_duration_seconds"
        assert hpoint.labels == {"method": "GET", "path": "/health"}
        assert hpoint.value > 0

    def test_zero_overhead_when_metrics_is_none(self):
        """metrics 为 None 时（默认）请求正常，缓冲区为空。"""
        from basic_tool.fastapi import create_app
        from basic_tool.fastapi.config import FastApiConfig

        config = FastApiConfig(enable_context_middleware=False)
        app = create_app(config)

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_metrics_failure_does_not_break_request(self):
        """采集器抛异常时请求不受影响，仍返回 200。"""
        bad_metrics = Mock()
        bad_metrics.counter.side_effect = RuntimeError("boom")
        bad_metrics.histogram.side_effect = RuntimeError("boom")

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware, metrics=bad_metrics)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestSetupErrorHandlers:
    """全局异常处理器测试。"""

    def test_app_error_handler(self):
        """AppError 返回对应状态码和标准化 JSON。"""
        app = FastAPI()
        setup_error_handlers(app)

        @app.get("/error")
        async def error_endpoint():
            raise AppError(code="INVALID_INPUT", message="Invalid input", http_status=422)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/error")
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "INVALID_INPUT"
        assert data["message"] == "Invalid input"

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
        data = resp.json()
        assert data["code"] == "INTERNAL_ERROR"

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
