"""FastApiConfig 配置类测试。"""

from basic_tool.fastapi.config import AuthConfig, CorsConfig, FastApiConfig
from basic_tool.logger.config import LogConfig


class TestCorsConfig:
    """CorsConfig 配置测试。"""

    def test_default_values(self):
        """默认值正确。"""
        config = CorsConfig()
        assert config.allow_origins == ["*"]
        assert config.allow_credentials is False
        assert config.allow_methods == ["*"]
        assert config.allow_headers == ["*"]
        assert config.expose_headers == []
        assert config.max_age == 600

    def test_custom_values(self):
        """自定义值生效。"""
        config = CorsConfig(
            allow_origins=["https://example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            max_age=300,
        )
        assert config.allow_origins == ["https://example.com"]
        assert config.allow_credentials is True
        assert config.allow_methods == ["GET", "POST"]
        assert config.max_age == 300


class TestAuthConfig:
    """AuthConfig 配置测试。"""

    def test_required_fields(self):
        """secret_key 是必填字段。"""
        config = AuthConfig(secret_key="test-key")
        assert config.secret_key == "test-key"

    def test_default_values(self):
        """默认值正确。"""
        config = AuthConfig(secret_key="test-key")
        assert config.algorithm == "HS256"
        assert config.token_expire_minutes == 30
        assert config.api_keys == {}
        assert config.token_url == "/auth/token"

    def test_api_keys_config(self):
        """API Key 映射配置。"""
        api_keys = {
            "key-1": {"scopes": ["read", "write"], "client": "A"},
            "key-2": {"scopes": ["read"], "client": "B"},
        }
        config = AuthConfig(secret_key="test-key", api_keys=api_keys)
        assert config.api_keys == api_keys


class TestFastApiConfig:
    """FastApiConfig 配置测试。"""

    def test_default_values(self):
        """默认值正确。"""
        config = FastApiConfig()
        assert config.title == "API"
        assert config.version == "0.1.0"
        assert config.debug is False
        assert isinstance(config.cors, CorsConfig)
        assert config.auth is None
        assert config.health_prefix == "/health"
        assert config.enable_request_logging is True
        assert config.enable_error_handlers is True

    def test_with_auth(self):
        """包含鉴权配置。"""
        auth = AuthConfig(secret_key="test-key")
        config = FastApiConfig(auth=auth)
        assert config.auth is not None
        assert config.auth.secret_key == "test-key"

    def test_custom_cors(self):
        """自定义 CORS 配置。"""
        cors = CorsConfig(allow_origins=["https://example.com"])
        config = FastApiConfig(cors=cors)
        assert config.cors.allow_origins == ["https://example.com"]

    def test_default_log_is_none(self):
        """默认不配置日志。"""
        config = FastApiConfig()
        assert config.log is None

    def test_with_log_config(self):
        """包含日志配置。"""
        log = LogConfig(level="DEBUG", json_output=True)
        config = FastApiConfig(log=log)
        assert config.log is not None
        assert config.log.level == "DEBUG"
        assert config.log.json_output is True


class TestContextMiddlewareConfig:
    """Context 中间件配置测试。"""

    def test_context_middleware_default_enabled(self):
        """默认启用 context middleware。"""
        config = FastApiConfig(title="test")
        assert config.enable_context_middleware is True

    def test_context_middleware_can_disable(self):
        """可以禁用 context middleware。"""
        config = FastApiConfig(title="test", enable_context_middleware=False)
        assert config.enable_context_middleware is False
