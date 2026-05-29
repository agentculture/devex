from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from devex.core.prog import prog_name

# We render markdown for agent / CLI consumption — never HTML in a browser.
# select_autoescape([], default_for_string=False) makes the intent explicit:
# escape nothing, for any extension AND for from_string templates (without
# the explicit `default_for_string=False`, Jinja silently auto-escapes
# string templates, which corrupts markdown — apostrophes turn into
# `&#39;`, `<` into `&lt;`, etc.).
_ENV = Environment(
    loader=FileSystemLoader("."),
    autoescape=select_autoescape([], default_for_string=False),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


# Sonar pythonsecurity:S5496 is suppressed inline on the render call
# below and also documented in sonar-project.properties. Rationale:
# render_string() renders Jinja templates that are always package-shipped
# (never user-controlled), and the output is markdown consumed by LLMs /
# the terminal — never rendered in an HTML context. Auto-escape is
# disabled deliberately (see select_autoescape([]) above). SonarCloud
# Automatic Analysis ignores the project-properties suppression, so the
# inline tag is the load-bearing one; both stay so a manual CLI scan also
# sees the suppression.
def render_string(template: str, context: dict[str, Any]) -> str:
    # `prog` is the one intentional global template variable: the command the
    # CLI was invoked as (`agex` or `devex`). Injecting it here keeps every
    # rendered template/footer able to say `{{ prog }} pr ...` without each
    # command threading it through its own context dict. An explicit context
    # value of the same name still wins (the `**context` spread comes last).
    ctx = {"prog": prog_name(), **context}
    return _ENV.from_string(template).render(**ctx)  # NOSONAR


def render_file(path: Path, context: dict[str, Any]) -> str:
    return render_string(path.read_text(), context)
