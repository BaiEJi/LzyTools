"""HTTP 客户端配置。

使用 Pydantic 模型统一管理 httpx 客户端、重试、熔断器的所有配置参数。
"""

from pydantic import BaseModel, ConfigDict

from basic_tool.metrics.collector import MetricsCollector


class RetryConfig(BaseModel):
    """重试配置。

    Attributes:
        max_retries: 最大重试次数。
        backoff_factor: 退避因子，延迟 = backoff_factor * 2^attempt。
        retryable_status_codes: 可重试的 HTTP 状态码集合。
    """

    max_retries: int = 3
    backoff_factor: float = 1.0
    retryable_status_codes: frozenset[int] = frozenset({429, 502, 503, 504})


class CircuitBreakerConfig(BaseModel):
    """熔断器配置。

    Attributes:
        failure_threshold: 触发熔断的连续失败次数。
        recovery_timeout: 熔断恢复等待秒数。
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0


class HttpConfig(BaseModel):
    """HTTP 客户端配置。

    Attributes:
        base_url: 基础 URL，所有相对请求路径会拼接此前缀。
        timeout: 请求超时秒数。
        connect_timeout: 连接超时秒数。
        read_timeout: 读取超时秒数。
        max_connections: 连接池最大连接数。
        max_keepalive: 连接池最大保活连接数。
        headers: 默认请求头。
        follow_redirects: 是否自动跟随重定向。
        http2: 是否启用 HTTP/2。
        retry: 重试配置，None 表示不重试。
        circuit_breaker: 熔断器配置，None 表示不启用。
        log_requests: 是否记录请求日志。
        log_request_body: 是否记录请求体（可能含敏感数据）。
        log_response_body: 是否记录响应体。
        max_body_log_size: 日志中响应体最大字符数。
        propagate_context: 是否自动将当前请求上下文的传播头
            （X-Trace-Id 等）注入出站 HTTP 请求，不覆盖用户已设置的头。
        metrics: 可选的 MetricsCollector，提供时记录出站请求的 counter
            （http_client_requests_total）和 histogram
            （http_client_request_duration_seconds）。None 表示不采集，
            零开销。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url: str = ""
    timeout: float = 30.0
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    max_connections: int = 100
    max_keepalive: int = 20
    headers: dict[str, str] = {}
    follow_redirects: bool = False
    http2: bool = False
    retry: RetryConfig | None = None
    circuit_breaker: CircuitBreakerConfig | None = None
    log_requests: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    max_body_log_size: int = 500
    propagate_context: bool = True
    metrics: MetricsCollector | None = None
