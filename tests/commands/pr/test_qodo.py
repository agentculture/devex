from pathlib import Path

from devex.commands.pr.scripts import _qodo

_FIXTURE = Path(__file__).parent / "fixtures" / "gh" / "qodo_summary_comment.html"


def _qodo_comment() -> dict:
    return {
        "type": "top-level",
        "id": 7,
        "author": "qodo-code-review[bot]",
        "html_url": "https://github.com/owner/repo/pull/24#issuecomment-7",
        "body": _FIXTURE.read_text(encoding="utf-8"),
    }


def test_parse_returns_none_when_no_qodo():
    comments = [{"type": "top-level", "author": "alice", "body": "looks good!"}]
    assert _qodo.parse(comments) is None


def test_parse_counts_and_total():
    result = _qodo.parse([_qodo_comment()])
    assert result is not None
    assert result["counts"] == {"bugs": 2, "rule_violations": 1, "requirement_gaps": 0}
    assert result["total"] == 3


def test_parse_findings_title_path_line_link():
    result = _qodo.parse([_qodo_comment()])
    findings = result["findings"]
    first = findings[0]
    assert first["title"] == "1. Orphan honesty rendered"
    assert first["path"] == "src/devex/core/render.py"
    assert first["line"] == "42-55"
    assert first["link"].startswith("https://github.com/")


def test_finding_without_permalink_still_listed():
    result = _qodo.parse([_qodo_comment()])
    titles = [f["title"] for f in result["findings"]]
    no_link = next(f for f in result["findings"] if "no permalink" in f["title"])
    assert no_link["path"] is None
    assert no_link["line"] is None
    # All three findings surface, including the permalink-less one.
    assert len(titles) == 3


def test_url_prefers_comment_html_url():
    result = _qodo.parse([_qodo_comment()])
    assert result["url"] == "https://github.com/owner/repo/pull/24#issuecomment-7"


def test_never_raises_on_garbage():
    result = _qodo.parse(
        [
            {
                "type": "top-level",
                "author": "qodo-code-review[bot]",
                "body": "Code Review by Qodo <details><summary>broken",
            }
        ]
    )
    assert isinstance(result, dict)
    assert result["total"] == 0


def test_found_comment_not_masked_when_subparser_raises(monkeypatch):
    """A parsing failure must not collapse a present Qodo comment to None
    (which the template would render as "_No Qodo review found._").  Counts
    still parse, so the collapsed-findings warning can still fire."""

    def boom(_body):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(_qodo, "parse_findings", boom)
    result = _qodo.parse([_qodo_comment()])
    assert result is not None
    assert result["findings"] == []
    assert result["counts"]["bugs"] == 2  # counts survive a findings failure
    assert result["total"] == 3
