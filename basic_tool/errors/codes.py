"""预定义通用错误码。

CommonErrors 包含 15 个覆盖常见 Web 服务场景的错误码定义。
所有条目在模块导入时自动注册到全局注册表。
"""

from basic_tool.errors.registry import ErrorEntry, ErrorRegistry


class CommonErrors(ErrorRegistry):
    """通用错误码集合。

    涵盖参数验证、认证授权、资源操作、限流和系统级错误的 15 个标准错误码。
    """

    # === 参数错误 (400) ===
    PARAM_MISSING = ErrorEntry("PARAM_MISSING", "缺少必填参数: {param}", 400)
    PARAM_INVALID = ErrorEntry("PARAM_INVALID", "参数无效: {param}", 400)
    PARAM_TYPE_ERROR = ErrorEntry("PARAM_TYPE_ERROR", "参数类型错误: {param} 应为 {expected_type}", 400)

    # === 认证错误 (401) ===
    TOKEN_EXPIRED = ErrorEntry("TOKEN_EXPIRED", "令牌已过期", 401)
    TOKEN_INVALID = ErrorEntry("TOKEN_INVALID", "令牌无效", 401)
    CREDENTIALS_ERROR = ErrorEntry("CREDENTIALS_ERROR", "用户名或密码错误", 401)

    # === 授权错误 (403) ===
    PERMISSION_DENIED = ErrorEntry("PERMISSION_DENIED", "权限不足: 需要 {required_permission}", 403)
    ACCESS_FORBIDDEN = ErrorEntry("ACCESS_FORBIDDEN", "禁止访问: {resource}", 403)

    # === 资源错误 ===
    RESOURCE_NOT_FOUND = ErrorEntry("RESOURCE_NOT_FOUND", "{resource}不存在", 404)
    RESOURCE_ALREADY_EXISTS = ErrorEntry("RESOURCE_ALREADY_EXISTS", "{resource}已存在", 409)
    VERSION_CONFLICT = ErrorEntry("VERSION_CONFLICT", "版本冲突: {resource} 已被修改", 409)

    # === 限流 (429) ===
    RATE_LIMITED = ErrorEntry("RATE_LIMITED", "请求过于频繁，请稍后重试", 429)

    # === 系统错误 ===
    INTERNAL_ERROR = ErrorEntry("INTERNAL_ERROR", "内部服务器错误", 500)
    SERVICE_UNAVAILABLE = ErrorEntry("SERVICE_UNAVAILABLE", "服务暂不可用", 503)
    UPSTREAM_TIMEOUT = ErrorEntry("UPSTREAM_TIMEOUT", "上游服务超时", 504)
