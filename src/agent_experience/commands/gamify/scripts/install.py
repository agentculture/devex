import json
from datetime import datetime, timezone
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from agent_experience.core.backend import Backend
from agent_experience.core.config import load as load_config
from agent_experience.core.config import save as save_config
from agent_experience.core.paths import ensure_init


def _fragments_file() -> Traversable:
    return files("agent_experience.commands.gamify").joinpath("assets", "hooks", "claude-code.json")


def _fragments_for(backend: Backend) -> list[dict]:
    if backend != Backend.CLAUDE_CODE:
        return []
    data = json.loads(_fragments_file().read_text(encoding="utf-8"))
    return data["fragments"]


def _hooks_file_for(backend: Backend, project_dir: Path) -> Path | None:
    if backend == Backend.CLAUDE_CODE:
        return project_dir / ".claude" / "hooks.json"
    return None


def _refuse(path: Path, reason: str) -> ValueError:
    return ValueError(
        f"{path} {reason}; refusing to overwrite. " "Fix or remove the file before re-running."
    )


def _load_hooks_file(path: Path) -> dict:
    # Malformed or unexpectedly-shaped files are NEVER silently overwritten —
    # the caller gets a ValueError, surfaces it as exit 2, and the user's file
    # stays on disk untouched.
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise _refuse(path, f"is not valid JSON ({e})") from e
    if not isinstance(data, dict):
        raise _refuse(path, "is not a JSON object at the top level")
    for entries in data.values():
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise _refuse(path, "is not a mapping of event → list of hook objects")
    return data


def _write_hooks_file(path: Path, data: dict) -> None:
    # Sonar pythonsecurity:S2083: `path` derives from
    # Path.cwd()/".claude/hooks.json"; the backend is enum-validated by
    # parse_backend() before reaching here. Full rationale lives in
    # sonar-project.properties. The suppression tag below is the
    # load-bearing one under SonarCloud Automatic Analysis.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")  # NOSONAR


def _merge_fragments(hooks: dict, fragments: list[dict]) -> tuple[list[str], int]:
    """Append each fragment's {id, hook} under its event if the id isn't already
    there. Returns (all_fragment_ids_in_insertion_order, added_count)."""
    written_ids: list[str] = []
    added = 0
    for frag in fragments:
        event = frag["event"]
        entry = {"id": frag["id"], "hook": frag["hook"]}
        hooks.setdefault(event, [])
        if not any(e.get("id") == frag["id"] for e in hooks[event]):
            hooks[event].append(entry)
            added += 1
        written_ids.append(frag["id"])
    return written_ids, added


def _remove_ids_from_hooks(hooks: dict, ids_to_remove: set[str]) -> int:
    """Filter entries matching ids_to_remove out of each event. Event keys whose
    arrays become empty as a result of removal are deleted. Pre-existing empty
    event arrays are left intact. Returns total entries removed."""
    removed = 0
    for event in list(hooks.keys()):
        original = hooks[event]
        filtered = [e for e in original if e.get("id") not in ids_to_remove]
        event_removed = len(original) - len(filtered)
        if event_removed == 0:
            continue
        removed += event_removed
        if filtered:
            hooks[event] = filtered
        else:
            del hooks[event]
    return removed


def install(backend: Backend) -> tuple[str, int, str]:
    ensure_init()
    project_dir = Path.cwd()
    hooks_file = _hooks_file_for(backend, project_dir)
    if hooks_file is None:
        return (_unsupported_notice(backend), 0, "")

    fragments = _fragments_for(backend)
    if not fragments:
        return (_unsupported_notice(backend), 0, "")

    try:
        hooks = _load_hooks_file(hooks_file)
    except ValueError as e:
        return ("", 2, f"agex: error: {e}")

    written_ids, added_count = _merge_fragments(hooks, fragments)
    if added_count:
        _write_hooks_file(hooks_file, hooks)

    cfg = load_config()
    previous = cfg.installed.get("gamify", {})
    if previous.get("hook_fragment_ids") != written_ids:
        cfg.installed["gamify"] = {
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "hook_fragment_ids": written_ids,
        }
        save_config(cfg)

    rel = hooks_file.relative_to(project_dir)
    if added_count:
        status_line = (
            f"- Added {added_count} hook fragment(s); "
            f"ensured {len(written_ids)} present in `{rel}`."
        )
    else:
        status_line = (
            f"- Ensured {len(written_ids)} hook fragment(s) already present "
            f"in `{rel}` (no changes)."
        )
    lines = [
        f"# Gamify installed — {backend.value}",
        "",
        status_line,
        "- Fragment IDs: " + ", ".join(f"`{i}`" for i in written_ids),
        "",
        f"Next: run `agex learn gamify --agent {backend.value}` to set up the levelup skill.",
        "",
    ]
    return ("\n".join(lines), 0, "")


def uninstall(backend: Backend) -> tuple[str, int, str]:
    ensure_init()
    project_dir = Path.cwd()
    hooks_file = _hooks_file_for(backend, project_dir)
    if hooks_file is None:
        return (_unsupported_notice(backend), 0, "")

    cfg = load_config()
    installed = cfg.installed.get("gamify", {})
    ids_to_remove = set(installed.get("hook_fragment_ids", []))
    if not ids_to_remove:
        return (f"# Gamify uninstalled — nothing to remove on {backend.value}.\n", 0, "")

    rel = hooks_file.relative_to(project_dir)
    # If the user already removed the hooks file, just drop the config record.
    # Don't re-create the file with an empty object.
    if not hooks_file.exists():
        cfg.installed.pop("gamify", None)
        save_config(cfg)
        return (
            f"# Gamify uninstalled — `{rel}` was already gone; " "cleared config record.\n",
            0,
            "",
        )

    try:
        hooks = _load_hooks_file(hooks_file)
    except ValueError as e:
        return ("", 2, f"agex: error: {e}")

    removed_count = _remove_ids_from_hooks(hooks, ids_to_remove)
    if removed_count:
        _write_hooks_file(hooks_file, hooks)

    cfg.installed.pop("gamify", None)
    save_config(cfg)

    return (
        f"# Gamify uninstalled — removed {removed_count} fragment(s) from `{rel}`.\n",
        0,
        "",
    )


def _unsupported_notice(backend: Backend) -> str:
    return (
        f"## `gamify` is not supported on {backend.value}\n\n"
        f"Hooks are required to track usage events, and {backend.value} does not expose "
        f"a hook interface agex can write to.\n\n"
        "Want this supported? Open an issue: <https://github.com/agentculture/devex/issues>\n"
    )
