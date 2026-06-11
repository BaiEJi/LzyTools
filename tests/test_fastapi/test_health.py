"""健康检查端点测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from basic_tool.fastapi.health import create_health_router


class TestHealthLiveness:
    """存活探针测试。"""

    def test_liveness_returns_healthy(self):
        """存活探针始终返回 200。"""
        app = FastAPI()
        app.include_router(create_health_router())

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    def test_custom_prefix(self):
        """自定义前缀。"""
        app = FastAPI()
        app.include_router(create_health_router(prefix="/alive"))

        client = TestClient(app)
        resp = client.get("/alive")
        assert resp.status_code == 200


class TestHealthReadiness:
    """就绪探针测试。"""

    def test_readiness_no_services(self):
        """无服务检查时返回 ready。"""
        app = FastAPI()
        app.include_router(create_health_router())

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"] == {}

    def test_readiness_with_healthy_service(self):
        """服务健康时返回 ready。"""
        mock_service = MagicMock()
        mock_service.check = AsyncMock(return_value={"status": "ok"})

        app = FastAPI()
        app.include_router(create_health_router(cache=mock_service))

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["cache"] == "ok"

    def test_readiness_with_unhealthy_service(self):
        """服务异常时返回 503。"""
        mock_service = MagicMock()
        mock_service.check = AsyncMock(return_value={"status": "error"})

        app = FastAPI()
        app.include_router(create_health_router(redis=mock_service))

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["checks"]["redis"] == "error"

    def test_readiness_service_exception(self):
        """服务抛异常时返回 503。"""
        mock_service = MagicMock()
        mock_service.check = AsyncMock(side_effect=ConnectionError("Connection refused"))

        app = FastAPI()
        app.include_router(create_health_router(db=mock_service))

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["checks"]["db"] == "error"

    def test_readiness_mixed_services(self):
        """部分服务健康、部分异常时返回 503。"""
        healthy = MagicMock()
        healthy.check = AsyncMock(return_value={"status": "ok"})

        unhealthy = MagicMock()
        unhealthy.check = AsyncMock(side_effect=Exception("fail"))

        app = FastAPI()
        app.include_router(create_health_router(cache=healthy, db=unhealthy))

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["checks"]["cache"] == "ok"
        assert data["checks"]["db"] == "error"

    def test_readiness_with_ping_service(self):
        """有 client 属性且支持 ping 的服务。"""
        mock_ping = AsyncMock()
        mock_client = MagicMock()
        mock_client.ping = mock_ping

        mock_service = MagicMock()
        mock_service.client = mock_client
        # 没有 check 方法
        del mock_service.check

        app = FastAPI()
        app.include_router(create_health_router(cache=mock_service))

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["checks"]["cache"] == "ok"
