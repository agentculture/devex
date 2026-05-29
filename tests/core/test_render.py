import pytest

from devex.core.render import render_file, render_string


def test_render_string_injects_context():
    out = render_string("Hello, {{ name }}!", {"name": "agex"})
    assert out == "Hello, agex!"


def test_render_string_strict_undefined():
    with pytest.raises(Exception) as exc:
        render_string("Hello, {{ missing }}!", {})
    assert "missing" in str(exc.value)


def test_render_file_reads_and_renders(tmp_path):
    tmpl = tmp_path / "t.md.j2"
    tmpl.write_text("# {{ title }}")
    out = render_file(tmpl, {"title": "agex"})
    assert out == "# agex"


def test_render_string_does_not_html_escape():
    # Regression: select_autoescape([]) without default_for_string=False
    # silently HTML-escapes from_string templates, corrupting markdown
    # (apostrophes -> &#39;, < -> &lt;, etc.).
    out = render_string("{{ x }}", {"x": "it's a <test> & 100% real"})
    assert out == "it's a <test> & 100% real"
