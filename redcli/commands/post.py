"""`redcli post` — submit a post to a subreddit."""

from __future__ import annotations

from pathlib import Path

import click

from .. import auth
from .. import output as out


@click.command("post")
@click.option("--sub", required=True, help="Target subreddit (without the r/ prefix).")
@click.option("--title", required=True, help="Post title.")
@click.option(
    "--body",
    "body_text",
    help="Post body text. Use --body-file for longer content.",
)
@click.option(
    "--body-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read post body from a Markdown file.",
)
@click.option("--url", help="If set, submit as a link post instead of a text post.")
@click.option("--flair-id", help="Flair template ID (use `redcli flairs <sub>` to list).")
@click.option("--flair-text", help="Flair text override (if the sub allows free-form flair).")
@click.option(
    "--nsfw/--no-nsfw",
    default=False,
    help="Mark as NSFW.",
)
@click.option(
    "--spoiler/--no-spoiler",
    default=False,
    help="Mark as spoiler.",
)
@click.option(
    "--send-replies/--no-send-replies",
    default=True,
    help="Receive inbox replies for this post.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be posted without submitting.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON of the result.")
def post(
    sub: str,
    title: str,
    body_text: str | None,
    body_file: Path | None,
    url: str | None,
    flair_id: str | None,
    flair_text: str | None,
    nsfw: bool,
    spoiler: bool,
    send_replies: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Submit a post to a subreddit.

    \b
    Examples:
      redcli post --sub SideProject --title "I built X" --body-file post.md
      redcli post --sub MacApps --title "[X] does Y" --url https://example.com
      redcli post --sub test --title "smoke" --body "hello" --dry-run
    """
    if url and (body_text or body_file):
        out.err("--url is mutually exclusive with --body / --body-file")
        raise SystemExit(2)
    if body_text and body_file:
        out.err("--body and --body-file are mutually exclusive")
        raise SystemExit(2)

    body: str | None = None
    if body_file:
        body = body_file.read_text()
    elif body_text:
        body = body_text

    sub = sub.removeprefix("r/").removeprefix("/r/")

    if dry_run:
        out.emit(
            {
                "kind": "link" if url else "self",
                "sub": sub,
                "title": title,
                "body_chars": len(body) if body else 0,
                "url": url,
                "flair_id": flair_id,
                "flair_text": flair_text,
                "nsfw": nsfw,
                "spoiler": spoiler,
                "send_replies": send_replies,
            },
            json=as_json,
        )
        out.info("(dry run — not submitted)")
        return

    reddit = auth.get_authed_reddit()
    sr = reddit.subreddit(sub)

    submit_kwargs: dict = {
        "title": title,
        "flair_id": flair_id,
        "flair_text": flair_text,
        "nsfw": nsfw,
        "spoiler": spoiler,
        "send_replies": send_replies,
    }
    if url:
        submission = sr.submit(url=url, **submit_kwargs)
    else:
        submission = sr.submit(selftext=body or "", **submit_kwargs)

    out.emit(
        {
            "id": submission.id,
            "url": f"https://reddit.com{submission.permalink}",
            "shortlink": submission.shortlink,
            "sub": sub,
            "title": title,
        },
        json=as_json,
    )
