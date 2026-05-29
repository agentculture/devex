"""Parse Qodo (``qodo-code-review[bot]``) "Code Review by Qodo" comments.

Qodo posts its code review as a single top-level issue comment whose body is
HTML containing collapsed ``<details>`` blocks — one per finding, each itself
holding nested ``<details>`` for Description / Code / Evidence / Agent prompt.
``devex pr read`` would otherwise render this comment truncated to 200 chars,
hiding the findings (and any real bug) entirely.

This module extracts the headline counts and, where possible, each finding's
title + ``file:line`` + permalink so the briefing can surface them the way it
surfaces inline review threads.  It is deliberately defensive: malformed or
partial HTML yields whatever is parseable and the public ``parse`` never raises.

Stdlib only (``re`` + ``html``) — the project ships no HTML-parsing dependency.
"""

from __future__ import annotations

import html
import re
from typing import Any

_QODO_MARKER = "Code Review by Qodo"

# Headline counts: <code>🐞 Bugs (3)</code>  <code>📘 Rule violations (1)</code>
# <code>📎 Requirement gaps (0)</code>.  Emoji-agnostic; matches label + integer.
_COUNT_RE = re.compile(
    r"<code>[^<]*?(Bugs|Rule violations|Requirement gaps)\s*\((\d+)\)",
    re.IGNORECASE,
)

_COUNT_KEYS = {
    "bugs": "bugs",
    "rule violations": "rule_violations",
    "requirement gaps": "requirement_gaps",
}

# Each finding is introduced by a <summary> whose (tag-stripped) text starts
# with an ordinal, e.g. "1. Orphan honesty rendered ...".  Nested Description /
# Code / Evidence / Agent-prompt summaries do not start with a digit, so they
# are not mistaken for findings — which sidesteps the nested-<details> problem.
_SUMMARY_RE = re.compile(r"<summary\b[^>]*>(.*?)</summary>", re.IGNORECASE | re.DOTALL)
_FINDING_TITLE_RE = re.compile(r"^\d+[.)]\s")

# Qodo's "Code" location, a markdown link with a bracketed line range:
#   [devague/render/spec_md.py[R44-49]](https://github.com/.../files#diff-…R44-R49)
_CODE_LINK_RE = re.compile(
    r"\[([^\[\]\n]+?)\[([RLrl]?\d+(?:-[RLrl]?\d+)?)\]\]\((https?://[^)\s]+)\)"
)

# Fallback: a bare GitHub blob permalink (used in the Evidence section):
#   https://github.com/owner/repo/blob/<sha>/<path>#L42-L55  (trailing / tolerated)
_PERMALINK_RE = re.compile(
    r"https://github\.com/\S+?/blob/[0-9a-fA-F]+/"
    r"(?P<path>[^#\s\"'<>)\]]+?)/?"
    r"(?:#L(?P<start>\d+)(?:-L(?P<end>\d+))?)?(?=[\s\"'<>)\]]|$)"
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_tags(fragment: str) -> str:
    text = _TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _find_qodo_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the "Code Review by Qodo" summary comment, or None."""
    for c in comments:
        if _QODO_MARKER in (c.get("body") or ""):
            return c
    return None


def parse_counts(body: str) -> dict[str, int]:
    counts = {"bugs": 0, "rule_violations": 0, "requirement_gaps": 0}
    for label, n in _COUNT_RE.findall(body):
        key = _COUNT_KEYS.get(label.lower())
        if key:
            counts[key] = int(n)
    return counts


def _extract_location(span: str) -> tuple[str | None, str | None, str | None]:
    """Return (path, line, link) for the first location in a finding span."""
    m = _CODE_LINK_RE.search(span)
    if m:
        path = m.group(1).strip()
        line = re.sub(r"[RLrl]", "", m.group(2))
        return path, line, m.group(3)
    m = _PERMALINK_RE.search(span)
    if m:
        path = m.group("path").rstrip("/")
        start, end = m.group("start"), m.group("end")
        line = None
        if start:
            line = f"{start}-{end}" if end else start
        return path, line, m.group(0)
    return None, None, None


def parse_findings(body: str) -> list[dict[str, Any]]:
    summaries = list(_SUMMARY_RE.finditer(body))
    title_idxs = [
        i for i, m in enumerate(summaries) if _FINDING_TITLE_RE.match(_strip_tags(m.group(1)))
    ]
    findings: list[dict[str, Any]] = []
    for n, idx in enumerate(title_idxs):
        # Title = the summary text up to the first <code> status/type badge.
        head = summaries[idx].group(1).split("<code>")[0]
        title = _strip_tags(head)
        span_start = summaries[idx].end()
        span_end = summaries[title_idxs[n + 1]].start() if n + 1 < len(title_idxs) else len(body)
        path, line, link = _extract_location(body[span_start:span_end])
        if not title and not path:
            continue
        findings.append({"title": title, "path": path, "line": line, "link": link})
    return findings


def parse(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return ``{counts, total, findings, url}`` for the Qodo summary comment,
    or ``None`` *only* when no such comment is present.

    Once a Qodo comment is found this always returns a dict (with safe
    defaults), so a parsing hiccup degrades to "0 findings" / the collapsed
    warning rather than the misleading ``_No Qodo review found._``.  ``counts``
    and ``findings`` are parsed independently so a partial failure still
    surfaces whatever was recoverable.  Never raises.
    """
    comment = _find_qodo_comment(comments)
    if comment is None:
        return None
    body = comment.get("body") or ""
    try:
        counts = parse_counts(body)
    except Exception:  # pragma: no cover - defensive
        counts = {"bugs": 0, "rule_violations": 0, "requirement_gaps": 0}
    try:
        findings = parse_findings(body)
    except Exception:  # pragma: no cover - defensive
        findings = []
    total = counts["bugs"] + counts["rule_violations"] + counts["requirement_gaps"]
    url = comment.get("html_url") or next((f["link"] for f in findings if f.get("link")), None)
    return {"counts": counts, "total": total, "findings": findings, "url": url}
