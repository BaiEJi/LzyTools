"""TemplateRenderer 单元测试。"""
import pytest

from basic_tool.email.exceptions import TemplateError
from basic_tool.email.template import TemplateRenderer, _html_to_plain


def test_render_with_template_variables(tmp_path):
    """测试 render() 正确替换模板变量。

    创建包含 {{ name }} 的模板，渲染时传入 name="World"，
    验证返回的 HTML 中包含 "Hello World"。
    """
    template_file = tmp_path / "hello.html"
    template_file.write_text("Hello {{ name }}!")

    renderer = TemplateRenderer(str(tmp_path))
    html, plain = renderer.render("hello.html", name="World")

    assert "Hello World" in html
    assert "Hello World" in plain


def test_render_nonexistent_template_raises(tmp_path):
    """测试 render() 对不存在的模板抛出 TemplateError。"""
    renderer = TemplateRenderer(str(tmp_path))

    with pytest.raises(TemplateError, match="Template not found"):
        renderer.render("missing.html")


def test_render_plain_text_fallback(tmp_path):
    """测试 render() 返回的纯文本 fallback 正确去除 HTML 标签。

    创建包含 <h1> 标签的模板，验证纯文本中不含 <h1> 但包含正文内容。
    """
    template_file = tmp_path / "tagged.html"
    template_file.write_text("<h1>Hello {{ name }}</h1>")

    renderer = TemplateRenderer(str(tmp_path))
    html, plain = renderer.render("tagged.html", name="World")

    assert "<h1>" in html
    assert "<h1>" not in plain
    assert "Hello World" in plain


def test_html_to_plain():
    """测试 _html_to_plain() 正确转换 HTML 为纯文本。

    验证 <br>、<br/>、<br /> 均转为换行符，HTML 标签被移除。
    """
    assert _html_to_plain("line1<br>line2") == "line1\nline2"
    assert _html_to_plain("line1<br/>line2") == "line1\nline2"
    assert _html_to_plain("line1<br />line2") == "line1\nline2"
    assert "<b>" not in _html_to_plain("<b>bold</b> text")
    assert "bold" in _html_to_plain("<b>bold</b> text")
