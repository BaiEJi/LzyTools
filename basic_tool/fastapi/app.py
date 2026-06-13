"""FastAPI 应用工厂。

提供 create_app() 一行代码创建具备完整中间件栈、鉴权、健康检查、
SDK 模块生命周期管理的 FastAPI 应用实例。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from basic_tool.errors import setup_error_handlers
from basic_tool.fastapi.auth import ApiKeyAuth, JWTAuth
from basic_tool.fastapi.config import FastApiConfig
from basic_tool.fastapi.health import create_health_router
from basic_tool.fastapi.middleware import RequestLoggingMiddleware
from basic_tool.logger import setup as setup_logger


def _build_lifespan(
    cache: Any | None = None,
    http_client: Any | None = None,
    task_queue: Any | None = None,
    extra_lifespan: Callable[..., AsyncIterator] | None = None,
) -> Callable[..., AsyncIterator]:
    """构建 lifespan 上下文管理器。

    自动 init/close 所有传入的 SDK 模块，存储到 app.state。

    Args:
        cache: Redis Cache 实例。
        http_client: HttpClient 实例。
        task_queue: TaskQueue 实例。
        extra_lifespan: 额外的 lifespan 上下文管理器。

    Returns:
        lifespan 上下文管理器函数。
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """应用生命周期管理。"""
        # === STARTUP ===
        if cache is not None:
            await cache.init()
            app.state.cache = cache
            logger.info("lifespan: Cache 已初始化")

        if http_client is not None:
            await http_client.init()
            app.state.http_client = http_client
            logger.info("lifespan: HttpClient 已初始化")

        if task_queue is not None:
            await task_queue.init()
            app.state.task_queue = task_queue
            logger.info("lifespan: TaskQueue 已初始化")

        if extra_lifespan is not None:
            # 链式执行额外的 lifespan
            async with extra_lifespan(app):
                yield
        else:
            yield

        # === SHUTDOWN ===
        if task_queue is not None:
            await task_queue.close()
            logger.info("lifespan: TaskQueue 已关闭")

        if http_client is not None:
            await http_client.close()
            logger.info("lifespan: HttpClient 已关闭")

        if cache is not None:
            await cache.close()
            logger.info("lifespan: Cache 已关闭")

    return lifespan


def create_app(
    config: FastApiConfig,
    *,
    cache: Any | None = None,
    http_client: Any | None = None,
    task_queue: Any | None = None,
    user_loader: Callable[[str], Awaitable[Any]] | None = None,
    login_handler: Callable[[str, str], Awaitable[dict | None]] | None = None,
    routers: list[APIRouter] | None = None,
    extra_lifespan: Callable[..., AsyncIterator] | None = None,
) -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    一行代码启动一个具备完整中间件栈、鉴权、健康检查的后端服务。

    Args:
        config: 应用配置。
        cache: Redis Cache 实例，自动在 lifespan 中 init/close。
        http_client: HttpClient 实例，自动在 lifespan 中 init/close。
        task_queue: TaskQueue 实例，自动在 lifespan 中 init/close。
        user_loader: JWT 用户加载回调，传入则启用 JWT 鉴权。
                     签名: async def user_loader(user_id: str) -> Any
        login_handler: 登录处理函数，传入则注册 /auth/token 端点。
                       签名: async def login(username: str, password: str) -> dict | None
        routers: 用户自定义路由列表，按顺序注册。
        extra_lifespan: 额外的 lifespan 上下文管理器。

    Returns:
        配置完成的 FastAPI 实例。

    Example::

        config = FastApiConfig(title="My Service", auth=AuthConfig(secret_key="..."))
        cache = Cache(RedisConfig())

        async def load_user(user_id: str):
            return await db.get_user(user_id)

        app = create_app(
            config,
            cache=cache,
            user_loader=load_user,
            routers=[items_router, users_router],
        )
        # uvicorn basic_tool.fastapi.app:create_app --factory
    """
    # === 日志配置 ===
    if config.log is not None:
        setup_logger(config.log)

    lifespan = _build_lifespan(
        cache=cache,
        http_client=http_client,
        task_queue=task_queue,
        extra_lifespan=extra_lifespan,
    )

    app = FastAPI(
        title=config.title,
        version=config.version,
        debug=config.debug,
        lifespan=lifespan,
    )

    # === CORS ===
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors.allow_origins,
        allow_credentials=config.cors.allow_credentials,
        allow_methods=config.cors.allow_methods,
        allow_headers=config.cors.allow_headers,
        expose_headers=config.cors.expose_headers,
        max_age=config.cors.max_age,
    )

    # === 中间件 ===
    if config.enable_request_logging:
        app.add_middleware(RequestLoggingMiddleware)

    if config.enable_error_handlers:
        setup_error_handlers(app)

    # === 健康检查 ===
    health_checks: dict[str, Any] = {}
    if cache is not None:
        health_checks["redis"] = cache
    if http_client is not None:
        health_checks["http_client"] = http_client
    if task_queue is not None:
        health_checks["task_queue"] = task_queue

    health_router = create_health_router(
        prefix=config.health_prefix,
        **health_checks,
    )
    app.include_router(health_router)

    # === 鉴权 ===
    if config.auth is not None and user_loader is not None:
        jwt_auth = JWTAuth(config.auth, user_loader=user_loader)
        app.state.jwt_auth = jwt_auth

        # 注册登录端点
        if login_handler is not None:
            auth_router = jwt_auth.create_token_router(login_handler=login_handler)
            app.include_router(auth_router, tags=["auth"])

        logger.info("JWT 鉴权已启用 | token_url={}", config.auth.token_url)

    if config.auth is not None and config.auth.api_keys:
        api_key_auth = ApiKeyAuth(config.auth)
        app.state.api_key_auth = api_key_auth
        logger.info("API Key 鉴权已启用 | keys={}", len(config.auth.api_keys))

    # === 用户路由 ===
    if routers:
        for router in routers:
            app.include_router(router)

    logger.info(
        "FastAPI 应用创建完成 | title={} version={} debug={}",
        config.title,
        config.version,
        config.debug,
    )

    return app
