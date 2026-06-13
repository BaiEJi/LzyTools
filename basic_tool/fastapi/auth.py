"""JWT 和 API Key 鉴权依赖提供器。

提供可配置的 JWT 鉴权和 API Key 鉴权，通过 FastAPI 依赖注入系统
集成到路由中。SDK 只负责 Token 管道，用户存储由业务层通过回调提供。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from basic_tool.context.ctx import ctx
from basic_tool.fastapi.config import AuthConfig


class TokenResponse(BaseModel):
    """Token 响应模型。

    Attributes:
        access_token: JWT access token。
        token_type: Token 类型，固定为 "bearer"。
    """

    access_token: str
    token_type: str = "bearer"


class JWTAuth:
    """JWT 鉴权依赖提供器。

    通过 user_loader 回调桥接业务层的用户存储，
    提供 get_current_user 依赖项和 require_scopes 权限检查。

    使用示例::

        async def load_user(user_id: str) -> User | None:
            return await db.get_user(user_id)

        jwt_auth = JWTAuth(config.auth, user_loader=load_user)

        # 注册登录端点
        app.include_router(jwt_auth.create_token_router(login_handler=my_login))

        # 路由中使用
        @app.get("/protected")
        async def protected(user = Depends(jwt_auth.get_current_user)):
            return {"user": user}
    """

    def __init__(
        self,
        config: AuthConfig,
        user_loader: Callable[[str], Awaitable[Any]],
    ) -> None:
        """初始化 JWTAuth。

        Args:
            config: 鉴权配置。
            user_loader: 异步回调，接收 token 中的 sub 字段，返回用户对象。
                         返回 None 表示用户不存在。
        """
        self._config = config
        self._user_loader = user_loader
        self._oauth2_scheme = OAuth2PasswordBearer(tokenUrl=config.token_url)

    def create_token(
        self,
        data: dict,
        expires_delta: timedelta | None = None,
    ) -> str:
        """创建 JWT token。

        Args:
            data: token payload，至少包含 {"sub": user_id}。
            expires_delta: 过期时间，默认使用 config.token_expire_minutes。

        Returns:
            编码后的 JWT 字符串。
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self._config.token_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            self._config.secret_key,
            algorithm=self._config.algorithm,
        )

    async def get_current_user(
        self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="")),
    ) -> Any:
        """FastAPI 依赖项：从请求中提取并验证用户。

        自动解码 JWT，调用 user_loader 加载用户。
        用户不存在或 token 无效时抛出 401。

        认证成功后，将 token 中的 sub（user_id）注入请求上下文
        （ctx.set("user_id", ...)），使后续日志、业务逻辑可通过
        ctx.get("user_id") 获取当前用户 ID。认证失败时不注入。

        Args:
            token: 从 Authorization: Bearer 头提取的 JWT token。

        Returns:
            user_loader 返回的用户对象。

        Raises:
            HTTPException 401: token 无效或用户不存在。
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                self._config.secret_key,
                algorithms=[self._config.algorithm],
            )
            user_id: str | None = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await self._user_loader(user_id)
        if user is None:
            raise credentials_exception
        ctx.set("user_id", user_id)
        return user

    def require_scopes(self, *scopes: str) -> Callable:
        """依赖工厂：要求 token 包含指定 scope。

        Args:
            scopes: 允许的 scope 列表。

        Returns:
            FastAPI 依赖函数，scope 不匹配时抛出 403。

        使用示例::

            @router.get("/admin", dependencies=[Depends(jwt_auth.require_scopes("admin"))])
            async def admin_endpoint(): ...
        """

        async def _check_scopes(
            token: str = Depends(self._oauth2_scheme),
        ) -> None:
            try:
                payload = jwt.decode(
                    token,
                    self._config.secret_key,
                    algorithms=[self._config.algorithm],
                )
                token_scopes = payload.get("scopes", [])
                if not any(s in token_scopes for s in scopes):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient scopes, required: {list(scopes)}",
                    )
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                )

        return _check_scopes

    def create_token_router(
        self,
        login_handler: Callable[[str, str], Awaitable[dict | None]] | None = None,
    ) -> APIRouter:
        """创建包含 /token 端点的路由器。

        Args:
            login_handler: 登录处理函数。
                           签名: async def login(username: str, password: str) -> dict | None
                           返回 {"sub": user_id, "scopes": [...]} 或 None（认证失败）。
                           不提供则不创建登录端点。

        Returns:
            APIRouter。
        """
        router = APIRouter()

        if login_handler is not None:

            @router.post("/token", response_model=TokenResponse)
            async def login(
                form_data: OAuth2PasswordRequestForm = Depends(),
            ) -> TokenResponse:
                """OAuth2 登录端点。"""
                result = await login_handler(form_data.username, form_data.password)
                if result is None:
                    logger.warning("登录失败 | username={}", form_data.username)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect username or password",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                token = self.create_token(
                    data={"sub": result["sub"], "scopes": result.get("scopes", [])},
                )
                logger.info("登录成功 | username={}", form_data.username)
                return TokenResponse(access_token=token)

        return router


class ApiKeyAuth:
    """API Key 鉴权依赖提供器。

    基于配置的 key 映射做 header 验证。

    使用示例::

        api_key_auth = ApiKeyAuth(config.auth)

        # 路由级别
        @router.get("/data", dependencies=[Depends(api_key_auth.verify)])
        async def get_data(): ...

        # 获取客户端信息
        @router.get("/info")
        async def info(client_info: dict = Depends(api_key_auth.verify)):
            return client_info
    """

    def __init__(
        self,
        config: AuthConfig,
        header_name: str = "X-API-Key",
    ) -> None:
        """初始化 ApiKeyAuth。

        Args:
            config: 鉴权配置，使用 config.api_keys 作为 key 映射。
            header_name: API Key 的 HTTP 头名称。
        """
        self._config = config
        self._header_name = header_name
        self._api_key_header = APIKeyHeader(name=header_name, auto_error=False)

    async def verify(
        self,
        api_key: str | None = Security(APIKeyHeader(name="X-API-Key", auto_error=False)),
    ) -> dict:
        """FastAPI 依赖项：验证 API Key。

        Args:
            api_key: 从请求头提取的 API Key。

        Returns:
            config.api_keys 中对应的 value dict。

        Raises:
            HTTPException 403: Key 无效或缺失。
        """
        if not api_key or api_key not in self._config.api_keys:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing API Key",
            )
        return self._config.api_keys[api_key]

    def require_scopes(self, *scopes: str) -> Callable:
        """依赖工厂：要求 API Key 包含指定 scope。

        Args:
            scopes: 允许的 scope 列表。

        Returns:
            FastAPI 依赖函数，scope 不匹配时抛出 403。

        使用示例::

            @router.get("/admin", dependencies=[Depends(api_key_auth.require_scopes("admin"))])
            async def admin_endpoint(): ...
        """

        async def _check_scopes(
            client_info: dict = Security(
                APIKeyHeader(name="X-API-Key", auto_error=False)
            ),
        ) -> None:
            if not client_info or client_info not in self._config.api_keys:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or missing API Key",
                )
            key_scopes = self._config.api_keys.get(client_info, {}).get("scopes", [])
            if not any(s in key_scopes for s in scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient scopes, required: {list(scopes)}",
                )

        return _check_scopes
