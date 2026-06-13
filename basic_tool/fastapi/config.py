"""FastAPI 应用配置。

使用 Pydantic 模型统一管理 FastAPI 应用、CORS、鉴权、日志的所有配置参数。
"""

from pydantic import BaseModel

from basic_tool.logger.config import LogConfig
from basic_tool.metrics.collector import MetricsCollector


class CorsConfig(BaseModel):
    """CORS 跨域配置。

    Attributes:
        allow_origins: 允许的来源列表。生产环境应指定具体域名。
        allow_credentials: 是否允许携带凭证。与 allow_origins=["*"] 冲突。
        allow_methods: 允许的 HTTP 方法列表。
        allow_headers: 允许的请求头列表。
        expose_headers: 暴露给前端的响应头列表。
        max_age: 预检请求缓存秒数。
    """

    allow_origins: list[str] = ["*"]
    allow_credentials: bool = False
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    expose_headers: list[str] = []
    max_age: int = 600


class AuthConfig(BaseModel):
    """鉴权配置。

    Attributes:
        secret_key: JWT 签名密钥，生产环境应使用环境变量注入。
        algorithm: JWT 签名算法。
        token_expire_minutes: Token 过期时间（分钟）。
        api_keys: API Key 映射，key 为 API Key 值，value 为客户端信息 dict。
        token_url: OAuth2 token 端点路径。
    """

    secret_key: str
    algorithm: str = "HS256"
    token_expire_minutes: int = 30
    api_keys: dict[str, dict] = {}
    token_url: str = "/auth/token"


class FastApiConfig(BaseModel):
    """FastAPI 应用配置。

    Attributes:
        title: 应用标题，显示在 OpenAPI 文档中。
        version: 应用版本号。
        debug: 是否启用调试模式。
        cors: CORS 跨域配置。
        auth: 鉴权配置，None 表示不启用鉴权。
        log: 日志配置，传入则在 create_app 时自动调用 setup() 配置 loguru。
             None 表示不自动配置日志（使用 loguru 默认行为）。
        metrics: 指标采集器，传入则在请求日志中间件中记录
                 ``http_requests_total`` (counter) 和
                 ``http_request_duration_seconds`` (histogram)。None 表示不采集（零开销）。
                 采集器的生命周期（init/close）由调用方负责。
        health_prefix: 健康检查端点路径前缀。
        enable_request_logging: 是否启用请求日志中间件。
        enable_error_handlers: 是否启用全局异常处理器。
        enable_context_middleware: 是否启用请求上下文中间件（W3C Trace Context）。
    """

    model_config = {"arbitrary_types_allowed": True}

    title: str = "API"
    version: str = "0.1.0"
    debug: bool = False
    cors: CorsConfig = CorsConfig()
    auth: AuthConfig | None = None
    log: LogConfig | None = None
    metrics: MetricsCollector | None = None
    health_prefix: str = "/health"
    enable_request_logging: bool = True
    enable_error_handlers: bool = True
    enable_context_middleware: bool = True
