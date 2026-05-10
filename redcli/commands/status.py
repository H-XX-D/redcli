"""`redcli status` — show stats for a post URL."""

from __future__ import annotations

import re

import click

from .. import auth
from .. import output as out

_SUBMISSION_ID_RE = re.compile(r"/comments/([a-z0-9]+)")


def _extract_submission_id(url_or_id: str) -> str:
    """Accept full URLs (https://reddit.com/r/x/comments/abc/title/) or bare IDs."""
    m = _SUBMISSION_ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    # Strip "t3_" prefix if present (Reddit's "thing" prefix for submissions)
    return url_or_id.removeprefix("t3_")


@click.command("status")
@click.argument("post_url_or_id")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def status(post_url_or_id: str, as_json: bool) -> None:
    """Show vote/comment stats for a post.

    Accepts a full post URL or a bare ID:
      redcli status https://reddit.com/r/SideProject/comments/abc123/...
      redcli status abc123
    """
    sid = _extract_submission_id(post_url_or_id)
    reddit = auth.get_authed_reddit()
    s = reddit.submission(id=sid)

    # PRAW lazy-loads — touching attributes triggers the fetch
    data = {
        "id": s.id,
        "title": s.title,
        "sub": s.subreddit.display_name,
        "author": s.author.name if s.author else "[deleted]",
        "ups": s.ups,
        "score": s.score,
        "upvote_ratio": s.upvote_ratio,
        "num_comments": s.num_comments,
        "age": out.fmt_age(s.created_utc),
        "url": f"https://reddit.com{s.permalink}",
        "stickied": s.stickied,
        "locked": s.locked,
        "nsfw": s.over_18,
        "removed": getattr(s, "removed_by_category", None) is not None,
    }
    out.emit(data, json=as_json)
