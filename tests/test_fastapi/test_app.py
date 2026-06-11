"""create_app 工厂函数测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from basic_tool.fastapi.app import create_app
from basic_tool.fastapi.config import AuthConfig, CorsConfig, FastApiConfig
from basic_tool.logger.config import LogConfig


def _default_config(**kwargs) -> FastApiConfig:
    """创建默认测试配置。"""
    defaults = {"title": "Test", "version": "0.1.0"}
    defaults.update(kwargs)
    return FastApiConfig(**defaults)


class TestCreateApp:
    """create_app 基础测试。"""

    def test_create_app_basic(self):
        """基本创建。"""
        config = _default_config()
        app = create_app(config)

        assert isinstance(app, FastAPI)
        assert app.title == "Test"
        assert app.version == "0.1.0"

    def test_create_app_with_debug(self):
        """调试模式。"""
        config = _default_config(debug=True)
        app = create_app(config)
        assert app.debug is True

    def test_create_app_with_routers(self):
        """注册用户路由。"""
        router = APIRouter()

        @router.get("/items")
        async def items():
            return [{"id": 1}]

        config = _default_config()
        app = create_app(config, routers=[router])

        client = TestClient(app)
        resp = client.get("/items")
        assert resp.status_code == 200
        assert resp.json() == [{"id": 1}]


class TestCreateAppHealth:
    """健康检查端点测试。"""

    def test_health_endpoint_exists(self):
        """默认 /health 端点存在。"""
        config = _default_config()
        app = create_app(config)

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_health_ready_endpoint(self):
        """默认 /health/ready 端点存在。"""
        config = _default_config()
        app = create_app(config)

        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 200

    def test_custom_health_prefix(self):
        """自定义健康检查前缀。"""
        config = _default_config(health_prefix="/alive")
        app = create_app(config)

        client = TestClient(app)
        resp = client.get("/alive")
        assert resp.status_code == 200


class TestCreateAppCors:
    """CORS 配置测试。"""

    def test_cors_headers(self):
        """CORS 响应头存在。"""
        cors = CorsConfig(allow_origins=["https://example.com"])
        config = _default_config(cors=cors)
        app = create_app(config)

        @app.get("/test")
        async def test():
            return {"ok": True}

        client = TestClient(app)
        resp = client.options(
            "/test",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORSMiddleware 应该返回 200
        assert resp.status_code == 200


class TestCreateAppAuth:
    """鉴权集成测试。"""

    def test_jwt_auth_enabled(self):
        """启用 JWT 鉴权。"""
        auth_config = AuthConfig(secret_key="test-key")
        config = _default_config(auth=auth_config)

        async def load_user(user_id: str):
            return {"id": user_id}

        app = create_app(config, user_loader=load_user)
        assert hasattr(app.state, "jwt_auth")

    def test_jwt_auth_with_login_endpoint(self):
        """JWT 鉴权 + 登录端点。"""
        auth_config = AuthConfig(secret_key="test-key")
        config = _default_config(auth=auth_config)

        async def load_user(user_id: str):
            return {"id": user_id}

        async def login(username: str, password: str):
            if username == "admin" and password == "secret":
                return {"sub": "admin", "scopes": []}
            return None

        app = create_app(
            config,
            user_loader=load_user,
            login_handler=login,
        )

        client = TestClient(app)
        resp = client.post(
            "/token",
            data={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_api_key_auth_enabled(self):
        """启用 API Key 鉴权。"""
        auth_config = AuthConfig(
            secret_key="test-key",
            api_keys={"key-1": {"scopes": ["read"]}},
        )
        config = _default_config(auth=auth_config)
        app = create_app(config)
        assert hasattr(app.state, "api_key_auth")

    def test_no_auth(self):
        """不启用鉴权。"""
        config = _default_config()
        app = create_app(config)
        assert not hasattr(app.state, "jwt_auth")
        assert not hasattr(app.state, "api_key_auth")


class TestCreateAppMiddleware:
    """中间件配置测试。"""

    def test_request_logging_enabled(self):
        """启用请求日志。"""
        config = _default_config(enable_request_logging=True)
        app = create_app(config)

        @app.get("/test")
        async def test():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers

    def test_request_logging_disabled(self):
        """禁用请求日志。"""
        config = _default_config(enable_request_logging=False)
        app = create_app(config)

        @app.get("/test")
        async def test():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Request-ID" not in resp.headers


class TestCreateAppLifespan:
    """Lifespan 生命周期测试。"""

    def test_lifespan_init_cache(self):
        """lifespan 自动初始化 cache。"""
        mock_cache = AsyncMock()
        mock_cache.init = AsyncMock()
        mock_cache.close = AsyncMock()
        # 为 health check 提供 check 方法
        mock_cache.check = AsyncMock(return_value={"status": "ok"})

        config = _default_config()

        with TestClient(create_app(config, cache=mock_cache)) as client:
            mock_cache.init.assert_called_once()

        mock_cache.close.assert_called_once()

    def test_lifespan_init_http_client(self):
        """lifespan 自动初始化 http_client。"""
        mock_http = AsyncMock()
        mock_http.init = AsyncMock()
        mock_http.close = AsyncMock()

        config = _default_config()

        with TestClient(create_app(config, http_client=mock_http)) as client:
            mock_http.init.assert_called_once()

        mock_http.close.assert_called_once()

    def test_lifespan_init_task_queue(self):
        """lifespan 自动初始化 task_queue。"""
        mock_queue = AsyncMock()
        mock_queue.init = AsyncMock()
        mock_queue.close = AsyncMock()

        config = _default_config()

        with TestClient(create_app(config, task_queue=mock_queue)) as client:
            mock_queue.init.assert_called_once()

        mock_queue.close.assert_called_once()

    def test_lifespan_init_multiple_services(self):
        """同时初始化多个服务。"""
        mock_cache = AsyncMock()
        mock_cache.init = AsyncMock()
        mock_cache.close = AsyncMock()

        mock_http = AsyncMock()
        mock_http.init = AsyncMock()
        mock_http.close = AsyncMock()

        config = _default_config()

        with TestClient(create_app(config, cache=mock_cache, http_client=mock_http)) as client:
            mock_cache.init.assert_called_once()
            mock_http.init.assert_called_once()

        mock_cache.close.assert_called_once()
        mock_http.close.assert_called_once()

    def test_services_stored_on_app_state(self):
        """服务存储在 app.state 上。"""
        mock_cache = AsyncMock()
        mock_cache.init = AsyncMock()
        mock_cache.close = AsyncMock()

        config = _default_config()
        app = create_app(config, cache=mock_cache)

        with TestClient(app) as client:
            assert app.state.cache is mock_cache


class TestCreateAppLogger:
    """日志配置集成测试。"""

    def test_log_config_triggers_setup(self):
        """传入 log 配置时自动调用 setup()。"""
        log_config = LogConfig(level="DEBUG")
        config = _default_config(log=log_config)

        app = create_app(config)
        assert isinstance(app, FastAPI)

    def test_no_log_config_skips_setup(self):
        """不传 log 配置时不调用 setup()。"""
        config = _default_config()
        app = create_app(config)
        assert isinstance(app, FastAPI)
