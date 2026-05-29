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


def test_preview_url_rejects_extra_authority_label():
    """A crafted host that continues past .pages.dev is not on pages.dev."""
    comments = [{"type": "top-level", "body": "see https://x.pages.dev.evil.com/login"}]
    assert _deploy.preview_url(comments) is None


def test_preview_url_rejects_userinfo_spoof():
    comments = [{"type": "top-level", "body": "see https://x.pages.dev@evil.com/login"}]
    assert _deploy.preview_url(comments) is None


def test_preview_url_rejects_lookalike_tld():
    comments = [{"type": "top-level", "body": "totally legit https://abc.pages.devil.com here"}]
    assert _deploy.preview_url(comments) is None


def test_preview_url_keeps_bare_host_and_port_safe():
    comments = [{"type": "top-level", "body": "deployed: https://abc.proj.pages.dev"}]
    assert _deploy.preview_url(comments) == "https://abc.proj.pages.dev"
