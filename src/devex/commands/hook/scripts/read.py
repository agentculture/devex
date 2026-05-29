from importlib.resources import files
from importlib.resources.abc import Traversable

from devex.commands.hook.scripts._footer import render_footer
from devex.commands.hook.scripts.next_step import hook_read_next_step
from devex.core import journal as _journal
from devex.core.backend import Backend
from devex.core.hook_io import load_events
from devex.core.paths import data_dir, ensure_init
from devex.core.render import render_string

KNOWN_STREAMS = ["post-tool-use", "user-prompt", "stop", "sessions"]


def _assets_root() -> Traversable:
    # Anchor on the `commands` package (which has __init__.py) and navigate in.
    # Avoids relying on namespace-package semantics for `assets/`, which is a
    # data directory, not a package. Matches overview.py / learn.py pattern.
    return files("devex.commands").joinpath("hook", "assets")


def _summarize(events):
    return [
        {
            "ts": e.get("ts", ""),
            "details": ", ".join(f"{k}={v}" for k, v in e.items() if k not in ("ts", "event")),
        }
        for e in events
    ]


def run(backend: Backend) -> tuple[str, int, str]:
    ensure_init()
    streams = []

    # Flat streams: data/<name>.json
    for name in KNOWN_STREAMS:
        events = load_events(name)
        streams.append({"name": name, "events": _summarize(events)})

    # Nested streams: data/<subdir>/<name>.jsonl
    root = data_dir()
    if root.exists():
        for subdir in sorted(p for p in root.iterdir() if p.is_dir()):
            for jsonl_file in sorted(subdir.glob("*.jsonl")):
                stream_name = f"{subdir.name}/{jsonl_file.stem}"
                events = _journal.load_events(stream_name)
                streams.append({"name": stream_name, "events": _summarize(events)})

    has_events = any(s["events"] for s in streams)
    rule_key, footer_ctx = hook_read_next_step(has_events=has_events)
    # Inject backend so hints can reference {{ backend }} for command examples.
    footer_ctx = {"backend": backend.value, **footer_ctx}
    footer = render_footer(rule_key, backend, footer_ctx)

    template_text = _assets_root().joinpath("table.md.j2").read_text(encoding="utf-8")
    out = render_string(
        template_text,
        {"backend": backend.value, "source": str(root), "streams": streams, "footer": footer},
    )
    return (out, 0, "")
