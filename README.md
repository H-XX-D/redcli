# redcli

A modern command-line client for Reddit. Submit posts, monitor stats, browse, all from your shell.

```text
status: alpha
license: MIT
runtime: python 3.9+
ergonomics: gh-style
```

The polished Reddit clients (Apollo, Reddit is Fun, `rtv`, `tuir`) mostly died after Reddit's 2023 API pricing change. `redcli` is a small, focused, MIT-licensed CLI for the slice of Reddit usage that survives nicely on the API: submitting posts, monitoring them, and reading from the shell.

## Install

```sh
pipx install redcli
```

Or from source:

```sh
git clone https://github.com/H-XX-D/redcli
cd redcli
pipx install .
```

## First-time setup

Reddit requires an "installed app" registration before you can authenticate. This is one-time, takes about a minute, and is free.

1. Go to <https://www.reddit.com/prefs/apps>
2. Click **"create another app..."** at the bottom
3. Choose type: **"installed app"**
4. Name: anything (e.g. `redcli-yourusername`)
5. Redirect URI: `http://localhost:16180/`
   *(16180 is the first five digits of the golden ratio — picked deliberately to avoid the heavy collision traffic on the more common 8080/3000/5000. Use `--port` to override if you have something on 16180.)*
6. Click **"create app"**
7. Copy the client ID — it's the short string under your app's name (NOT the longer "secret" field)

Then:

```sh
redcli auth login --client-id YOUR_CLIENT_ID
```

A browser window opens, you approve the scopes, and `redcli` saves a refresh token to `~/.config/redcli/credentials.json` (mode 0600). You won't need to log in again until you run `redcli auth logout`.

## Commands

```text
redcli auth login          authenticate via browser OAuth
redcli auth status         show current auth state
redcli auth logout         remove stored credentials

redcli me                  show your account info
redcli post                submit a text or link post
redcli status <url>        show vote/comment stats for a post
redcli watch <url>         live-update post stats (Ctrl-C to stop)
```

Every command takes `--json` to emit machine-readable output for scripting.

## Examples

Submit a Markdown post:

```sh
redcli post --sub SideProject --title "I built X" --body-file post.md
```

Submit a link post:

```sh
redcli post --sub MacApps \
  --title "[ThreadSaver] Export AI chat threads as Markdown" \
  --url https://github.com/H-XX-D/threadsaver
```

Dry-run before posting (recommended for first-time use):

```sh
redcli post --sub test --title "smoke test" --body "hello" --dry-run
```

Monitor a post during a launch:

```sh
redcli watch https://reddit.com/r/SideProject/comments/abc123/...
```

Quick one-shot check (good for cron):

```sh
redcli status https://reddit.com/r/SideProject/comments/abc123/... --json
```

## Why redcli exists

After the 2023 API event there's a real gap: no `gh`-equivalent for Reddit. PRAW is excellent as a library but doesn't give you a CLI. The popular TUIs (`rtv`, `tuir`) were focused on browsing, not on submission/monitoring workflows. Marketers and indie devs who launch on Reddit have been stitching together bash scripts and `praw` snippets.

redcli's scope is intentionally narrow: the subset of Reddit you'd use from a shell during a tool launch or from cron for monitoring. It is not trying to replace your browser for casual reading.

## Scopes requested

By default, `redcli auth login` requests:

- `identity` — read your username (for `redcli me` and the login confirmation)
- `submit` — create posts
- `read` — read posts and comments
- `save`, `subscribe`, `vote`, `edit`, `history` — common interactive actions
- `privatemessages` — for the (forthcoming) `redcli inbox` command
- `mysubreddits` — list your subscribed subs

You can override with `--scope identity --scope submit` (repeatable).

## Roadmap

- v0.2: `inbox`, `comment`, `search`, `subs` commands
- v0.3: `crosspost`, `flairs`, `mod` (for sub mods)
- v0.4: TUI mode (`redcli tui`) for browsing
- v1.0: Possible Go rewrite for single-binary distribution

## Contributing

PRs welcome. Run tests with:

```sh
pip install -e ".[dev]"
pytest
```

## License

MIT — see `LICENSE`.
