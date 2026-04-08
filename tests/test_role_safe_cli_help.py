from __future__ import annotations

from pathlib import Path

from crisp.cli import v29 as role_safe_cli


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_role_safe_cli_help_includes_examples_and_comparison_guidance() -> None:
    parser = role_safe_cli.build_parser()
    help_text = parser.format_help()

    assert "Role-safe wrapper for v2.9.5 integrated runs." in help_text
    assert "comparison_type guidance:" in help_text
    assert "cross-regime = cross-config/regime label only; never interpret it as an algorithm comparison" in help_text
    for example in role_safe_cli.HELP_EXAMPLE_LINES.values():
        assert example in help_text


def test_readme_keeps_role_safe_examples_in_sync_with_cli_help() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "## crisp-v29 Operator Guide" in readme
    assert "comparison_type semantics" in readme
    for example in role_safe_cli.HELP_EXAMPLE_LINES.values():
        assert example in readme
