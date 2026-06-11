"""JWTAuth 和 ApiKeyAuth 鉴权测试。"""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI, Security
from fastapi.security import APIKeyHeader
from fastapi.testclient import TestClient
from jose import jwt

from basic_tool.fastapi.auth import ApiKeyAuth, JWTAuth, TokenResponse
from basic_tool.fastapi.config import AuthConfig


def _make_auth_config(**kwargs) -> AuthConfig:
    """创建测试用 AuthConfig。"""
    defaults = {"secret_key": "test-secret-key", "algorithm": "HS256"}
    defaults.update(kwargs)
    return AuthConfig(**defaults)


def _make_user_loader(user_map: dict | None = None):
    """创建测试用 user_loader。"""
    users = user_map or {"user-1": {"id": "user-1", "name": "Test User"}}

    async def loader(user_id: str):
        return users.get(user_id)

    return loader


class TestJWTAuthTokenCreation:
    """JWT token 创建测试。"""

    def test_create_token(self):
        """create_token 返回有效的 JWT。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"sub": "user-1"})
        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "user-1"
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """自定义过期时间。"""
        config = _make_auth_config(token_expire_minutes=60)
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"sub": "user-1"}, expires_delta=timedelta(hours=2))
        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "user-1"

    def test_create_token_with_scopes(self):
        """token 包含 scopes。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"sub": "user-1", "scopes": ["read", "write"]})
        payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
        assert payload["scopes"] == ["read", "write"]


class TestJWTAuthGetUser:
    """JWT get_current_user 依赖项测试。"""

    def test_valid_token_returns_user(self):
        """有效 token 返回用户对象。"""
        config = _make_auth_config()
        user = {"id": "user-1", "name": "Test User"}
        auth = JWTAuth(config, user_loader=_make_user_loader({"user-1": user}))

        token = auth.create_token({"sub": "user-1"})

        app = FastAPI()

        @app.get("/me")
        async def me(current_user=Depends(auth.get_current_user)):
            return current_user

        client = TestClient(app)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == user

    def test_invalid_token_returns_401(self):
        """无效 token 返回 401。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        app = FastAPI()

        @app.get("/me")
        async def me(current_user=Depends(auth.get_current_user)):
            return current_user

        client = TestClient(app)
        resp = client.get("/me", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_missing_user_returns_401(self):
        """用户不存在返回 401。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader({}))

        token = auth.create_token({"sub": "nonexistent"})

        app = FastAPI()

        @app.get("/me")
        async def me(current_user=Depends(auth.get_current_user)):
            return current_user

        client = TestClient(app)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_no_sub_in_token_returns_401(self):
        """token 缺少 sub 字段返回 401。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"role": "admin"})

        app = FastAPI()

        @app.get("/me")
        async def me(current_user=Depends(auth.get_current_user)):
            return current_user

        client = TestClient(app)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestJWTAuthScopes:
    """JWT require_scopes 测试。"""

    def test_matching_scope_passes(self):
        """scope 匹配时通过。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"sub": "user-1", "scopes": ["read", "write"]})

        app = FastAPI()

        @app.get("/data", dependencies=[Depends(auth.require_scopes("read"))])
        async def data():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/data", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_missing_scope_returns_403(self):
        """scope 不匹配返回 403。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        token = auth.create_token({"sub": "user-1", "scopes": ["read"]})

        app = FastAPI()

        @app.get("/admin", dependencies=[Depends(auth.require_scopes("admin"))])
        async def admin():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestJWTAuthTokenRouter:
    """JWT create_token_router 测试。"""

    def test_token_endpoint_success(self):
        """登录成功返回 token。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        async def login_handler(username: str, password: str):
            if username == "admin" and password == "secret":
                return {"sub": "admin", "scopes": ["read", "write"]}
            return None

        app = FastAPI()
        app.include_router(auth.create_token_router(login_handler=login_handler))

        client = TestClient(app)
        resp = client.post(
            "/token",
            data={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_endpoint_failure(self):
        """登录失败返回 401。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        async def login_handler(username: str, password: str):
            return None

        app = FastAPI()
        app.include_router(auth.create_token_router(login_handler=login_handler))

        client = TestClient(app)
        resp = client.post(
            "/token",
            data={"username": "wrong", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_no_login_handler_no_endpoint(self):
        """不提供 login_handler 则不创建端点。"""
        config = _make_auth_config()
        auth = JWTAuth(config, user_loader=_make_user_loader())

        router = auth.create_token_router()
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        resp = client.post("/token")
        assert resp.status_code == 404  # 端点不存在


class TestApiKeyAuth:
    """ApiKeyAuth 测试。"""

    def test_valid_api_key(self):
        """有效 API Key 返回客户端信息。"""
        config = _make_auth_config(api_keys={
            "key-1": {"scopes": ["read"], "client": "A"},
        })
        auth = ApiKeyAuth(config)

        app = FastAPI()

        @app.get("/data")
        async def data(info: dict = Security(auth.verify)):
            return info

        client = TestClient(app)
        resp = client.get("/data", headers={"X-API-Key": "key-1"})
        assert resp.status_code == 200
        assert resp.json() == {"scopes": ["read"], "client": "A"}

    def test_invalid_api_key(self):
        """无效 API Key 返回 403。"""
        config = _make_auth_config(api_keys={
            "key-1": {"scopes": ["read"], "client": "A"},
        })
        auth = ApiKeyAuth(config)

        app = FastAPI()

        @app.get("/data")
        async def data(info: dict = Security(auth.verify)):
            return info

        client = TestClient(app)
        resp = client.get("/data", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 403

    def test_missing_api_key(self):
        """缺少 API Key 返回 403。"""
        config = _make_auth_config(api_keys={
            "key-1": {"scopes": ["read"], "client": "A"},
        })
        auth = ApiKeyAuth(config)

        app = FastAPI()

        @app.get("/data")
        async def data(info: dict = Security(auth.verify)):
            return info

        client = TestClient(app)
        resp = client.get("/data")
        assert resp.status_code == 403
