"""`reddi history` — list your own recent submissions."""

from __future__ import annotations

import click

from .. import auth
from .. import output as out


@click.command("history")
@click.option("--limit", default=25, show_default=True, help="Max submissions to fetch.")
@click.option(
    "--sort",
    type=click.Choice(("new", "top", "hot", "controversial")),
    default="new",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def history(limit: int, sort: str, as_json: bool) -> None:
    """List your own recent submissions with current vote/comment/removed status.

    \b
    Examples:
      reddi history                         # last 25 submissions
      reddi history --limit 100 --sort top  # your top-scoring posts
      reddi history --json | jq '.[] | select(.removed) | .url'
                                            # find your removed posts
    """
    reddit = auth.get_authed_reddit()
    me = reddit.user.me()
    if me is None:
        out.err("Could not fetch user — token may be invalid. Try `reddi auth login`.")
        raise SystemExit(1)

    listing = {
        "new": me.submissions.new,
        "top": me.submissions.top,
        "hot": me.submissions.hot,
        "controversial": me.submissions.controversial,
    }[sort]

    rows = []
    for s in listing(limit=limit):
        rows.append(
            {
                "id": s.id,
                "sub": s.subreddit.display_name,
                "title": s.title[:60],
                "score": s.score,
                "comments": s.num_comments,
                "age": out.fmt_age(s.created_utc),
                "removed": getattr(s, "removed_by_category", None) is not None,
                "locked": s.locked,
                "url": f"https://reddit.com{s.permalink}",
            }
        )

    out.emit(
        rows,
        json=as_json,
        table_columns=["sub", "title", "score", "comments", "age", "removed", "locked"],
    )
