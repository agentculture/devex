from devex.core.backend import Backend
from devex.core.capabilities import (
    ISSUE_URL,
    CapabilityMatrix,
    is_supported,
    unsupported_notice,
)


def test_is_supported_true(tmp_path):
    yaml_path = tmp_path / "claude-code.yaml"
    yaml_path.write_text("hooks: true\nmcp: true\n")
    matrix = CapabilityMatrix.load({Backend.CLAUDE_CODE: yaml_path})
    assert is_supported(matrix, Backend.CLAUDE_CODE, "hooks")


def test_is_supported_false(tmp_path):
    yaml_path = tmp_path / "acp.yaml"
    yaml_path.write_text("hooks: false\nmcp: true\n")
    matrix = CapabilityMatrix.load({Backend.ACP: yaml_path})
    assert not is_supported(matrix, Backend.ACP, "hooks")


def test_unsupported_notice_renders_markdown(tmp_path):
    yaml_path = tmp_path / "acp.yaml"
    yaml_path.write_text(
        "hooks: false\n"
        "hooks_alternative: |\n"
        "  Wrap your agent invocation in a shell script that logs events manually.\n"
    )
    matrix = CapabilityMatrix.load({Backend.ACP: yaml_path})
    notice = unsupported_notice(matrix, Backend.ACP, "hooks")
    assert "not supported on acp" in notice.lower()
    assert "Wrap your agent invocation" in notice
    assert ISSUE_URL in notice
