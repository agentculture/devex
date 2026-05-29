"""Deploy-preview URL extraction for the `pr` namespace.

Pure parse of the already-fetched comments list — no network call.  The
Cloudflare Pages GitHub integration posts a deploy-preview link as a markdown
table cell, e.g. ``[Visit Preview](https://<hash>.<project>.pages.dev)``; this
lifts the first such URL into the briefing header.
"""

from __future__ import annotations

import re
from typing import Any

# Matches a Cloudflare Pages preview URL.  ``.pages.dev`` must terminate the host
# authority — the negative lookahead rejects an authority that continues with
# another label or userinfo (e.g. ``x.pages.dev.evil.com`` / ``x.pages.dev@evil``),
# which would otherwise let a crafted comment inject a misleading link.  Only a
# ``/?#``-led path/query/fragment may follow; the path stops at whitespace or the
# closing ``)`` / ``]`` of a markdown link.
_PAGES_RE = re.compile(
    r"https://[a-z0-9][a-z0-9.-]*\.pages\.dev(?![a-z0-9.\-@])(?:[/?#][^\s)\]]*)?",
    re.IGNORECASE,
)


def preview_url(comments: list[dict[str, Any]]) -> str | None:
    """First Cloudflare Pages ``*.pages.dev`` URL found in any comment body.

    Returns ``None`` when no comment carries a preview link, so the briefing
    silently skips the section on non-Cloudflare repos.
    """
    for c in comments:
        match = _PAGES_RE.search(c.get("body") or "")
        if match:
            return match.group(0)
    return None
