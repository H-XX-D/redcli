"""Smoke tests — these don't hit the Reddit API, just verify the CLI loads."""

from __future__ import annotations

from click.testing import CliRunner

from redcli import __version__
from redcli.cli import cli
from redcli.commands.status import _extract_submission_id


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_loads() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # Every top-level command should appear in the help output
    for cmd in ("auth", "post", "status", "watch", "me"):
        assert cmd in result.output


def test_post_dry_run_no_auth() -> None:
    """--dry-run should not require auth — it's pure local logic."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["post", "--sub", "test", "--title", "smoke", "--body", "hi", "--dry-run", "--json"],
    )
    assert result.exit_code == 0
    assert '"sub": "test"' in result.output
    assert '"title": "smoke"' in result.output


def test_extract_submission_id_url() -> None:
    sid = _extract_submission_id("https://reddit.com/r/SideProject/comments/abc123/some-title/")
    assert sid == "abc123"


def test_extract_submission_id_bare() -> None:
    assert _extract_submission_id("abc123") == "abc123"
    assert _extract_submission_id("t3_abc123") == "abc123"


def test_post_url_and_body_mutually_exclusive() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["post", "--sub", "test", "--title", "x", "--url", "https://example.com", "--body", "hi"],
    )
    assert result.exit_code == 2
    haystack = (result.output + (result.stderr or "")).lower()
    assert "mutually exclusive" in haystack


def test_sub_strips_r_prefix() -> None:
    """`--sub r/SideProject` and `--sub SideProject` behave identically in dry-run."""
    runner = CliRunner()
    common = ["post", "--title", "t", "--body", "b", "--dry-run", "--json"]
    r1 = runner.invoke(cli, [*common, "--sub", "r/test"])
    r2 = runner.invoke(cli, [*common, "--sub", "test"])
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert '"sub": "test"' in r1.output
    assert '"sub": "test"' in r2.output
