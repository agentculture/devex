from agent_experience.commands.pr.scripts import _deploy


def test_preview_url_none_when_no_comments():
    assert _deploy.preview_url([]) is None


def test_preview_url_none_when_no_pages_dev():
    comments = [{"type": "top-level", "author": "alice", "body": "looks good, ship it"}]
    assert _deploy.preview_url(comments) is None


def test_preview_url_extracted_from_markdown_link():
    body = (
        "| Cloudflare Pages | Deploying |\n"
        "| Latest commit | abc1234 |\n"
        "| Preview URL | [Visit Preview](https://abc1234.devex.pages.dev) |\n"
    )
    comments = [{"type": "top-level", "author": "cloudflare-pages[bot]", "body": body}]
    assert _deploy.preview_url(comments) == "https://abc1234.devex.pages.dev"


def test_preview_url_stops_at_paren_and_keeps_path():
    body = "Deployed to (https://branch.my-proj.pages.dev/path/to/page) — check it out!"
    comments = [{"type": "top-level", "author": "bot", "body": body}]
    assert _deploy.preview_url(comments) == "https://branch.my-proj.pages.dev/path/to/page"


def test_preview_url_returns_first_match_across_comments():
    comments = [
        {"type": "top-level", "author": "x", "body": "no link here"},
        {"type": "top-level", "author": "y", "body": "first https://one.proj.pages.dev here"},
        {"type": "top-level", "author": "z", "body": "second https://two.proj.pages.dev here"},
    ]
    assert _deploy.preview_url(comments) == "https://one.proj.pages.dev"


def test_preview_url_tolerates_missing_body():
    comments = [{"type": "inline", "author": "x"}, {"type": "top-level", "body": None}]
    assert _deploy.preview_url(comments) is None
