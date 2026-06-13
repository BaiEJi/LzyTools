"""Jinja2 邮件模板渲染。

从指定目录加载 HTML 模板，渲染后生成 HTML 正文和纯文本 fallback。
"""
from __future__ import annotations

import re
from pathlib import Path

from loguru import logger

from basic_tool.email.exceptions import TemplateError

# jinja2 为可选依赖
try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
    _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False


def _html_to_plain(html: str) -> str:
    """将 HTML 转换为纯文本（简易实现）。

    去除 HTML 标签，折叠空白，保留文本内容。

    Args:
        html: HTML 字符串。

    Returns:
        纯文本字符串。
    """
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class TemplateRenderer:
    """Jinja2 邮件模板渲染器。

    从 template_dir 加载模板文件，渲染后返回 HTML 和纯文本。

    Args:
        template_dir: 模板文件目录路径。

    Raises:
        ImportError: jinja2 未安装时抛出。

    Examples:
        renderer = TemplateRenderer("/app/templates/email")
        html, plain = renderer.render("welcome.html", name="Alice")
    """

    def __init__(self, template_dir: str) -> None:
        """初始化模板渲染器。

        Args:
            template_dir: 模板文件目录路径。

        Raises:
            ImportError: jinja2 未安装时。
            TemplateError: 模板目录不存在时。
        """
        if not _HAS_JINJA2:
            raise ImportError(
                "jinja2 is required for template rendering. "
                "Install it with: pip install jinja2"
            )
        self._dir = Path(template_dir)
        if not self._dir.is_dir():
            raise TemplateError(f"Template directory not found: {template_dir}")
        self._env = Environment(
            loader=FileSystemLoader(str(self._dir)),
            autoescape=False,
        )

    def render(self, template_name: str, **context: object) -> tuple[str, str]:
        """渲染模板，返回 (html, plaintext)。

        Args:
            template_name: 模板文件名（相对于 template_dir）。
            **context: 模板变量。

        Returns:
            (html正文, 纯文本fallback) 元组。

        Raises:
            TemplateError: 模板不存在或渲染失败。
        """
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound:
            raise TemplateError(f"Template not found: {template_name}")
        except TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error in {template_name}: {e}") from e

        try:
            html = template.render(**context)
        except Exception as e:
            raise TemplateError(f"Template render error: {e}") from e

        plain = _html_to_plain(html)
        logger.debug("template rendered | name={} html_len={}", template_name, len(html))
        return html, plain
