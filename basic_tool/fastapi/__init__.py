"""FastAPI 应用 SDK。

基于 FastAPI 的后端服务封装，提供一行代码创建具备完整中间件栈、
鉴权、健康检查和 SDK 模块生命周期管理的 Web 服务。

使用示例::

    from basic_tool.fastapi import create_app, FastApiConfig, AuthConfig, CorsConfig
    from basic_tool.redis import Cache, RedisConfig

    # 1. 配置
    config = FastApiConfig(
        title="用户服务",
        version="1.0.0",
        cors=CorsConfig(allow_origins=["https://app.example.com"]),
        auth=AuthConfig(secret_key="my-secret-key"),
    )

    # 2. SDK 模块
    cache = Cache(RedisConfig())

    # 3. 用户加载器
    async def load_user(user_id: str):
        return await db.get_user(user_id)

    # 4. 创建应用
    app = create_app(
        config,
        cache=cache,
        user_loader=load_user,
        routers=[items_router, users_router],
    )

    # 5. 运行
    # uvicorn main:app --host 0.0.0.0 --port 8000
"""

from basic_tool.errors import AppError
from basic_tool.fastapi.app import create_app
from basic_tool.fastapi.auth import ApiKeyAuth, JWTAuth
from basic_tool.fastapi.config import AuthConfig, CorsConfig, FastApiConfig
from basic_tool.fastapi.middleware import RequestLoggingMiddleware, setup_error_handlers
from basic_tool.logger.config import LogConfig

__all__ = [
    "create_app",
    "FastApiConfig",
    "CorsConfig",
    "AuthConfig",
    "LogConfig",
    "JWTAuth",
    "ApiKeyAuth",
    "AppError",
    "RequestLoggingMiddleware",
]
