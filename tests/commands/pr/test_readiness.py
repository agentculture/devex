from devex.commands.pr.scripts import _readiness
from devex.core import github


def test_thread_tally_counts_total_resolved_unresolved(monkeypatch):
    monkeypatch.setattr(
        github,
        "pr_review_threads",
        lambda pr: [
            {"id": "T1", "isResolved": False},
            {"id": "T2", "isResolved": False},
            {"id": "T3", "isResolved": True},
        ],
    )
    assert _readiness.thread_tally(42) == (3, 1, 2)


def test_thread_tally_zero_on_empty(monkeypatch):
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    assert _readiness.thread_tally(42) == (0, 0, 0)


def test_thread_tally_zero_on_query_failure(monkeypatch):
    def _boom(pr):
        raise RuntimeError("gh failed")

    monkeypatch.setattr(github, "pr_review_threads", _boom)
    assert _readiness.thread_tally(42) == (0, 0, 0)


def test_threads_unresolved_delegates_to_tally(monkeypatch):
    monkeypatch.setattr(
        github,
        "pr_review_threads",
        lambda pr: [{"id": "T1", "isResolved": False}, {"id": "T2", "isResolved": True}],
    )
    assert _readiness.threads_unresolved(42) == 1
