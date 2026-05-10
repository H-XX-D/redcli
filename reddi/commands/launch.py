"""`reddi launch` — declarative multi-stage launch orchestration.

A launch is described as JSON:

    {
      "name": "ThreadSaver launch",
      "stages": [
        {"sub": "SideProject",  "title": "...", "body_file": "post.md", "delay_seconds": 0},
        {"sub": "MacApps",      "title": "...", "body_file": "post-mac.md", "delay_seconds": 7200}
      ],
      "watch_after": true,
      "watch_duration_seconds": 86400,
      "watch_interval_seconds": 300,
      "on_removal": "osascript -e 'display notification \"post removed\"'",
      "on_locked":  null
    }

Paths in `body_file` are resolved relative to the config file's directory.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import click

from .. import auth
from .. import output as out


@click.command("launch")
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate the config and show the plan without submitting anything.",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Append launch events to this file (JSON-lines). Default: <config>.log",
)
@click.option("--json", "as_json", is_flag=True, help="Emit final summary as JSON.")
def launch(config_path: Path, dry_run: bool, log_file: Path | None, as_json: bool) -> None:
    """Run a multi-stage launch from a JSON config.

    \b
    The config describes a sequence of stages (one post per stage), optional
    delays between them, and an optional post-launch watch period that fires
    shell commands when posts are removed or locked.

    \b
    Example:
      reddi launch ~/launches/threadsaver/config.json
      reddi launch config.json --dry-run        # validate, no submission
    """
    config = _load_config(config_path)
    plan = _build_plan(config, base_dir=config_path.parent)

    if dry_run:
        out.console.print(f"[bold]Launch plan: {config.get('name', '(unnamed)')}[/bold]\n")
        for i, stage in enumerate(plan, 1):
            out.console.print(
                f"  [{i}] +{stage['delay_seconds']}s  "
                f"r/{stage['sub']}  {stage['title'][:60]}  "
                f"(body: {stage['body_chars']} chars)"
            )
        if config.get("watch_after"):
            d = config.get("watch_duration_seconds", 86400)
            i = config.get("watch_interval_seconds", 300)
            out.console.print(
                f"\n  watch all for {d}s at {i}s intervals "
                f"(on_removal={bool(config.get('on_removal'))}, "
                f"on_locked={bool(config.get('on_locked'))})"
            )
        out.info("(dry run — nothing submitted)")
        return

    log_path = log_file or config_path.with_suffix(config_path.suffix + ".log")
    reddit = auth.get_authed_reddit()
    launched: list[dict] = []
    start = time.monotonic()

    _log(log_path, {"event": "launch_start", "name": config.get("name", "")})
    out.console.print(f"[bold]Launching: {config.get('name', '(unnamed)')}[/bold]")
    out.console.print(f"[dim]log: {log_path}[/dim]\n")

    try:
        for i, stage in enumerate(plan, 1):
            elapsed = time.monotonic() - start
            wait = max(0, stage["delay_seconds"] - elapsed)
            if wait > 0:
                out.info(f"stage {i}: sleeping {int(wait)}s before posting to r/{stage['sub']}")
                time.sleep(wait)

            out.console.print(f"[cyan]→[/cyan] stage {i}: posting to r/{stage['sub']}")
            sr = reddit.subreddit(stage["sub"])
            submission = sr.submit(
                title=stage["title"],
                selftext=stage["body"],
                flair_id=stage.get("flair_id"),
                flair_text=stage.get("flair_text"),
                nsfw=stage.get("nsfw", False),
                spoiler=stage.get("spoiler", False),
                send_replies=stage.get("send_replies", True),
            )
            entry = {
                "stage": i,
                "sub": stage["sub"],
                "id": submission.id,
                "url": f"https://reddit.com{submission.permalink}",
            }
            launched.append(entry)
            _log(log_path, {"event": "posted", **entry})
            out.console.print(f"  [green]✓[/green] {entry['url']}")

        if config.get("watch_after"):
            _watch_phase(reddit, launched, config, log_path)

    except KeyboardInterrupt:
        _log(log_path, {"event": "interrupted", "launched": launched})
        out.console.print("\n[yellow]launch interrupted by user[/yellow]")

    _log(log_path, {"event": "launch_end", "launched": launched})
    out.emit({"name": config.get("name", ""), "launched": launched}, json=as_json)


# ---------- helpers ----------

def _load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        out.err(f"Config is not valid JSON: {e}")
        raise SystemExit(2) from e


def _build_plan(config: dict, base_dir: Path) -> list[dict]:
    """Validate stages and resolve body_file paths against the config dir."""
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        out.err("config.stages must be a non-empty list")
        raise SystemExit(2)

    plan = []
    for i, stage in enumerate(stages, 1):
        if "sub" not in stage or "title" not in stage:
            out.err(f"stage {i} is missing required field 'sub' or 'title'")
            raise SystemExit(2)
        if "body" not in stage and "body_file" not in stage:
            out.err(f"stage {i} needs either 'body' or 'body_file'")
            raise SystemExit(2)

        if "body_file" in stage:
            body_path = (base_dir / stage["body_file"]).resolve()
            if not body_path.exists():
                out.err(f"stage {i}: body_file not found: {body_path}")
                raise SystemExit(2)
            body = body_path.read_text()
        else:
            body = stage["body"]

        plan.append(
            {
                "sub": stage["sub"].removeprefix("r/").removeprefix("/r/"),
                "title": stage["title"],
                "body": body,
                "body_chars": len(body),
                "delay_seconds": int(stage.get("delay_seconds", 0)),
                "flair_id": stage.get("flair_id"),
                "flair_text": stage.get("flair_text"),
                "nsfw": stage.get("nsfw", False),
                "spoiler": stage.get("spoiler", False),
                "send_replies": stage.get("send_replies", True),
            }
        )
    return plan


def _watch_phase(reddit, launched: list[dict], config: dict, log_path: Path) -> None:  # noqa: ANN001
    duration = int(config.get("watch_duration_seconds", 86400))
    interval = int(config.get("watch_interval_seconds", 300))
    on_removal = config.get("on_removal")
    on_locked = config.get("on_locked")

    out.console.print(
        f"\n[bold]Watching {len(launched)} post(s) for {duration}s @ {interval}s intervals[/bold]"
    )

    end_at = time.monotonic() + duration
    last_state: dict[str, dict] = {e["id"]: {} for e in launched}

    while time.monotonic() < end_at:
        for entry in launched:
            try:
                s = reddit.submission(id=entry["id"])
                s._fetched = False  # type: ignore[attr-defined]
                s._fetch()  # type: ignore[attr-defined]

                is_removed = getattr(s, "removed_by_category", None) is not None
                is_locked = bool(s.locked)
                prev = last_state[entry["id"]]

                if is_removed and not prev.get("removed") and on_removal:
                    _log(log_path, {"event": "removed", **entry})
                    out.console.print(
                        f"  [red]![/red] r/{entry['sub']} removed — firing on_removal"
                    )
                    subprocess.run(on_removal, shell=True)  # noqa: S602

                if is_locked and not prev.get("locked") and on_locked:
                    _log(log_path, {"event": "locked", **entry})
                    out.console.print(
                        f"  [yellow]![/yellow] r/{entry['sub']} locked — firing on_locked"
                    )
                    subprocess.run(on_locked, shell=True)  # noqa: S602

                last_state[entry["id"]] = {"removed": is_removed, "locked": is_locked}
            except Exception as e:  # noqa: BLE001
                out.warn(f"watch poll error for {entry['id']}: {e}")
        time.sleep(interval)


def _log(path: Path, payload: dict) -> None:
    payload["t"] = datetime.utcnow().isoformat() + "Z"
    with path.open("a") as f:
        f.write(json.dumps(payload) + "\n")
