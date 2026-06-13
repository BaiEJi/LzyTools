"""错误码注册表。

提供 ErrorEntry（可调用错误定义）和 ErrorRegistry（错误码集合），
以及全局注册表的冲突检测、查询和清理功能。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_global_registry: dict[str, ErrorEntry] = {}


@dataclass(frozen=True)
class ErrorEntry:
    """错误码定义条目，注册到全局注册表并可调用生成 AppError。

    创建实例时自动注册到全局注册表，重复注册会抛出 ValueError。

    Attributes:
        code: 错误码。
        message_template: 消息模板，支持 str.format 风格的占位符。
        http_status: HTTP 状态码，默认 400。
    """

    code: str
    message_template: str
    http_status: int = 400

    def __post_init__(self) -> None:
        """注册到全局注册表，检测重复。"""
        if self.code in _global_registry:
            raise ValueError(
                f"Duplicate error code: {self.code} "
                f"(already registered: {_global_registry[self.code]})"
            )
        _global_registry[self.code] = self

    def __call__(self, **kwargs: Any) -> AppError:
        """渲染消息模板并生成 AppError。

        Args:
            **kwargs: 模板参数，同时存入 AppError.context。

        Returns:
            填充了消息和上下文的 AppError 实例。
        """
        message = self.message_template.format(**kwargs)
        return AppError(
            code=self.code,
            message=message,
            http_status=self.http_status,
            context=kwargs,
        )

    def __repr__(self) -> str:
        """返回调试友好的表示。"""
        return f"ErrorEntry(code={self.code!r}, message_template={self.message_template!r}, http_status={self.http_status})"


class ErrorRegistry:
    """错误码集合基类。

    子类以类属性形式定义 ErrorEntry 实例，通过 entries() 和 codes() 查询。
    """

    @classmethod
    def entries(cls) -> dict[str, ErrorEntry]:
        """返回类中定义的所有 ErrorEntry。

        Returns:
            以属性名为 key、ErrorEntry 为 value 的字典。
        """
        result: dict[str, ErrorEntry] = {}
        for name in dir(cls):
            if name.startswith("_"):
                continue
            value = getattr(cls, name)
            if isinstance(value, ErrorEntry):
                result[name] = value
        return result

    @classmethod
    def codes(cls) -> list[str]:
        """返回类中定义的所有错误码属性名。

        Returns:
            错误码属性名列表。
        """
        return list(cls.entries().keys())


def check_conflicts() -> None:
    """扫描全局注册表检测重复错误码。

    Raises:
        ValueError: 发现重复注册时抛出。
    """
    # _global_registry already detects duplicates at registration time (__post_init__)
    # This function provides an explicit verification entry point.
    seen: dict[str, ErrorEntry] = {}
    for code, entry in _global_registry.items():
        if code in seen:
            raise ValueError(
                f"Duplicate error code detected: {code} "
                f"(entries: {seen[code]} vs {entry})"
            )
        seen[code] = entry


def get_all_entries() -> dict[str, ErrorEntry]:
    """返回全局注册表的副本。

    Returns:
        全局注册表字典的浅拷贝。
    """
    return dict(_global_registry)


def clear_registry() -> None:
    """清空全局注册表（仅用于测试隔离）。"""
    _global_registry.clear()


# Delayed import to avoid circular dependency
from basic_tool.errors.app_error import AppError  # noqa: E402
