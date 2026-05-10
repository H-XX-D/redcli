"""`reddi watch` — live-update post stats with optional state-transition hooks."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime

import click
from rich.live import Live
from rich.table import Table

from .. import auth
from .. import output as out
from .status import _extract_submission_id


@click.command("watch")
@click.argument("post_url_or_id")
@click.option(
    "--interval",
    default=60,
    show_default=True,
    type=int,
    help="Refresh interval in seconds (min 30, Reddit rate limits).",
)
@click.option(
    "--once",
    is_flag=True,
    help="Refresh once and exit (useful for cron / scripted polling).",
)
@click.option(
    "--on-removal",
    default=None,
    help=(
        "Shell command to fire when the post is removed (mod or AutoMod). "
        "$REDDI_POST_URL is set in the env. "
        "Example: --on-removal 'tput bel'"
    ),
)
@click.option(
    "--on-locked",
    default=None,
    help="Shell command to fire when the post becomes locked.",
)
def watch(
    post_url_or_id: str,
    interval: int,
    once: bool,
    on_removal: str | None,
    on_locked: str | None,
) -> None:
    """Live-update vote/comment stats for a post.

    \b
    Useful during a launch — pin to a second monitor and watch the post grow
    (or not) in real time. Press Ctrl-C to stop.

    \b
    The --on-removal / --on-locked hooks fire a shell command exactly once
    when the post transitions into that state. The post URL is available
    in $REDDI_POST_URL when the hook runs.

    \b
    Examples:
      reddi watch <url>
      reddi watch <url> --interval 120
      reddi watch <url> --on-removal 'osascript -e "display notification \\"removed\\""'
      reddi watch <url> --on-locked  'curl -X POST $SLACK_WEBHOOK -d ...'
    """
    if interval < 30 and not once:
        out.warn("interval < 30s may hit Reddit rate limits; clamped to 30s")
        interval = 30

    sid = _extract_submission_id(post_url_or_id)
    reddit = auth.get_authed_reddit()

    last_state = {"removed": False, "locked": False, "url": None}

    def snapshot() -> Table:
        s = reddit.submission(id=sid)
        # Force a refresh on every poll
        s._fetched = False  # type: ignore[attr-defined]  # PRAW internal
        s._fetch()  # type: ignore[attr-defined]

        url = f"https://reddit.com{s.permalink}"
        is_removed = getattr(s, "removed_by_category", None) is not None
        is_locked = bool(s.locked)

        # Fire transition hooks (exactly once on transition)
        if is_removed and not last_state["removed"] and on_removal:
            out.console.print("[red]![/red] post removed — firing on_removal hook")
            subprocess.run(on_removal, shell=True, env={"REDDI_POST_URL": url})  # noqa: S602
        if is_locked and not last_state["locked"] and on_locked:
            out.console.print("[yellow]![/yellow] post locked — firing on_locked hook")
            subprocess.run(on_locked, shell=True, env={"REDDI_POST_URL": url})  # noqa: S602
        last_state["removed"] = is_removed
        last_state["locked"] = is_locked
        last_state["url"] = url

        t = Table(show_header=False, box=None)
        t.add_column(style="bold cyan")
        t.add_column()
        t.add_row("post", s.title[:80])
        t.add_row("sub", f"r/{s.subreddit.display_name}")
        t.add_row("score", f"[bold]{s.score}[/bold] ({int(s.upvote_ratio * 100)}% upvoted)")
        t.add_row("comments", str(s.num_comments))
        t.add_row("age", out.fmt_age(s.created_utc))
        t.add_row("status", _state_str(s))
        t.add_row("checked", datetime.now().strftime("%H:%M:%S"))
        return t

    if once:
        out.console.print(snapshot())
        return

    with Live(snapshot(), console=out.console, refresh_per_second=1) as live:
        try:
            while True:
                time.sleep(interval)
                live.update(snapshot())
        except KeyboardInterrupt:
            out.console.print("\n[dim]stopped[/dim]")


def _state_str(s) -> str:  # noqa: ANN001
    flags = []
    if getattr(s, "removed_by_category", None) is not None:
        flags.append("[red]removed[/red]")
    if s.locked:
        flags.append("[yellow]locked[/yellow]")
    if s.stickied:
        flags.append("[cyan]stickied[/cyan]")
    return " ".join(flags) if flags else "[green]live[/green]"
