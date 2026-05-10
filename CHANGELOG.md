# Changelog

All notable changes to `reddi` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and `reddi` adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-05-10

The "efficiency amplifier" release. Five new commands designed around the insight that reddi's value isn't "another Reddit CLI" — it's making the Reddit launch/monitor loop substantially faster than the browser.

### Added

- **`reddi completion <bash|zsh|fish>`** — emit shell completion scripts. After install, `reddi <TAB>` completes commands and `reddi auth <TAB>` completes subcommands. Click 8 native; supports bash, zsh, and fish.
- **`reddi launch <config.json>`** — declarative multi-stage launch orchestration. Describe a launch as JSON (sequence of stages with delays, optional post-launch watch period with shell-command hooks for state changes), and reddi runs the whole sequence. Supports `--dry-run` for plan validation, JSON-lines log file, and `on_removal` / `on_locked` shell-command hooks. The big v1.x feature.
- **`reddi history`** — list your own recent submissions with current vote/comment/removed/locked state. Supports `--sort new|top|hot|controversial` and `--limit`. Pipe to `jq` to filter (e.g., find your removed posts: `reddi history --json | jq '.[] | select(.removed)'`).
- **`reddi inbox watch`** — live-stream new inbox items as they arrive (PRAW long-poll inbox stream). Supports `--mark-read` and `--on-arrival "shell command"` for terminal bell, notifications, or webhooks. Useful during a launch when you want comment replies to surface in real time.
- **`reddi watch --on-removal` / `--on-locked`** — fire a shell command exactly once when a watched post transitions to removed or locked. The post URL is passed via `$REDDI_POST_URL`. Lets you pipe to `osascript`, `notify-send`, Slack webhooks, etc.

### Changed

- User-Agent string bumped to `reddi/1.1 (https://github.com/H-XX-D/reddi)`.
- README rewritten to lead with the efficiency angle. The pitch is no longer "modern Reddit CLI" but "turns the launch loop from 90 minutes of tab-switching into 20 minutes of terminal commands."

### v1.x stability contract

All v1.0 flag shapes and JSON keys remain stable. v1.1 only adds new commands and new flags on existing commands — no breaking changes.

## [1.0.0] — 2026-05-10

### Added

- **`reddi inbox list`** — list unread (default) or all inbox items: comment replies, mentions, private messages.
- **`reddi inbox mark-read`** — mark items read by `--id` (repeatable) or `--all`.
- **`reddi comment <url-or-id>`** — post a top-level comment on a submission, or reply to a specific comment. Auto-detects which based on URL shape. Supports `--body`, `--body-file`, and `--body -` (stdin). `--dry-run` is supported.
- **`reddi search <query>`** — search posts across all of Reddit or within a sub. Supports `--sort`, `--time`, `--limit`, `--syntax`. Lucene-style queries (`title:foo`, `selftext:bar`, `AND`/`OR`) are the default.
- **`reddi subs list`** — list subscribed subreddits, sorted by subscriber count.
- **`reddi subs info <name>`** — sub metadata: subscribers, active users, type, created date, submission types allowed.
- **`reddi subs subscribe <name>` / `unsubscribe <name>`** — add/remove subscription.
- **`reddi crosspost <url-or-id> --to <sub>`** — crosspost an existing submission to another sub. Supports `--title` override, `--flair-id`, `--flair-text`, NSFW/spoiler overrides, and `--dry-run`.
- **`reddi flairs <sub>`** — list available flair templates for a sub. Use the `--link` (default) / `--user` toggle to switch between post-flair and user-flair templates. The listed `id` is what `reddi post --flair-id` expects.

### Changed

- Bumped to **production/stable** classifier — the v1.0 surface is the stable contract; we won't break these flags or shapes in the 1.x line.
- README rewritten to lead with use case ("the launch/monitor workflow") rather than feature list.
- Top-level `--help` now showcases the launch loop: post → watch → inbox → comment → crosspost.

### Stable contract (v1.0 promise)

These commands and their flag shapes are stable for the entire 1.x line:

```text
reddi auth (login|status|logout)
reddi me
reddi post
reddi status <url-or-id>
reddi watch <url-or-id>
reddi inbox (list|mark-read)
reddi comment <url-or-id>
reddi search <query>
reddi subs (list|info|subscribe|unsubscribe)
reddi crosspost <url-or-id> --to <sub>
reddi flairs <sub>
```

`--json` is supported on every command that returns data, and the JSON shape will not change incompatibly within 1.x.

## [0.1.0] — 2026-05-10

Initial release.

### Added

- `reddi auth (login|status|logout)` — browser-based OAuth via local callback on port 16180 (chosen to avoid the heavy collisions on 8080/3000/5000).
- `reddi me` — show authenticated account info.
- `reddi post` — submit text or link posts; `--dry-run` for lint-before-submit.
- `reddi status <url-or-id>` — vote/comment/removed-state for a post.
- `reddi watch <url-or-id>` — live-updating dashboard for monitoring a launch.

[1.1.0]: https://github.com/H-XX-D/reddi/releases/tag/v1.1.0
[1.0.0]: https://github.com/H-XX-D/reddi/releases/tag/v1.0.0
[0.1.0]: https://github.com/H-XX-D/reddi/releases/tag/v0.1.0
