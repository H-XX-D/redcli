"""OAuth flow + credentials storage.

Reddit's "installed app" type is the right shape for a CLI: no client_secret
needed, supports the full scope set, works for any user (not just the app
registrant). We use the standard authorization-code flow with a one-shot local
HTTP callback server, the same pattern `gh auth login` uses for GitHub.

Credentials live at ~/.config/reddi/credentials.json with mode 0600.
"""

from __future__ import annotations

import http.server
import json
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path

import praw

# Default scopes — broad enough to cover post/comment/read/inbox without being
# greedy. Users can re-auth with custom scopes via `reddi auth login --scopes`.
DEFAULT_SCOPES = [
    "identity",
    "submit",
    "read",
    "save",
    "subscribe",
    "edit",
    "history",
    "vote",
    "privatemessages",
    "mysubreddits",
]

USER_AGENT = "reddi/1.1 (https://github.com/H-XX-D/reddi)"
CONFIG_DIR = Path(os.environ.get("REDDI_CONFIG_DIR", Path.home() / ".config" / "reddi"))
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


@dataclass
class Credentials:
    """Persisted credentials. client_id is the Reddit app ID; refresh_token
    lets us get fresh access tokens without re-authorizing."""

    client_id: str
    refresh_token: str
    username: str
    scopes: list[str]


# ---------- credentials persistence ----------

def load_credentials() -> Credentials | None:
    if not CREDENTIALS_PATH.exists():
        return None
    with CREDENTIALS_PATH.open("r") as f:
        data = json.load(f)
    return Credentials(**data)


def save_credentials(creds: Credentials) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # mode 0600 — only the owner can read. Belt-and-suspenders against accidental
    # exposure (e.g. a misconfigured backup or a shared dotfiles repo).
    with CREDENTIALS_PATH.open("w") as f:
        json.dump(asdict(creds), f, indent=2)
    os.chmod(CREDENTIALS_PATH, 0o600)


def clear_credentials() -> None:
    if CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()


# ---------- PRAW client construction ----------

def get_authed_reddit() -> praw.Reddit:
    """Return an authenticated PRAW Reddit instance, or exit with a helpful
    message if the user hasn't logged in yet."""
    creds = load_credentials()
    if creds is None:
        print(
            "reddi is not authenticated. Run `reddi auth login` first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return praw.Reddit(
        client_id=creds.client_id,
        client_secret=None,  # installed-app type
        refresh_token=creds.refresh_token,
        user_agent=USER_AGENT,
    )


# ---------- OAuth login flow ----------

class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """One-shot HTTP handler that captures the OAuth code from the redirect."""

    captured: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _OAuthCallbackHandler.captured["code"] = params["code"][0]
            _OAuthCallbackHandler.captured["state"] = params.get("state", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:system-ui;padding:40px;'>"
                b"<h2>reddi authentication complete</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            _OAuthCallbackHandler.captured["error"] = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>Authorization failed</h2><p>{params['error'][0]}"
                f"</p></body></html>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Silence the default request logging — the user just sees "approve in browser, done"
        pass


def login(client_id: str, scopes: list[str] | None = None, port: int = 16180) -> Credentials:
    """Run the OAuth dance and return persisted Credentials.

    The user must have created an "installed app" at https://www.reddit.com/prefs/apps
    with redirect_uri = http://localhost:{port}/. We default port=16180 (the first
    five digits of the golden ratio) — it's unregistered, well clear of common
    dev-tool collisions on 8080/3000/5000, and below the OS ephemeral-port range
    so it won't get randomly bumped by outbound TCP connections.
    """
    scopes = scopes or DEFAULT_SCOPES
    state = secrets.token_urlsafe(16)
    redirect_uri = f"http://localhost:{port}/"

    # Build a not-yet-authenticated PRAW client just to get the auth URL
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=None,
        redirect_uri=redirect_uri,
        user_agent=USER_AGENT,
    )
    auth_url = reddit.auth.url(scopes=scopes, state=state, duration="permanent")

    # Spin up the one-shot callback server
    _OAuthCallbackHandler.captured = {}
    server = http.server.HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("\nOpening browser to authorize reddi...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for the callback
    try:
        while not _OAuthCallbackHandler.captured:
            threading.Event().wait(0.1)
    finally:
        server.shutdown()

    captured = _OAuthCallbackHandler.captured
    if "error" in captured:
        raise RuntimeError(f"Reddit denied authorization: {captured['error']}")
    if captured.get("state") != state:
        raise RuntimeError("OAuth state mismatch — possible CSRF; aborting.")
    if "code" not in captured:
        raise RuntimeError("No authorization code received.")

    # Exchange code for refresh token
    refresh_token = reddit.auth.authorize(captured["code"])
    if not refresh_token:
        raise RuntimeError("Reddit returned no refresh token; auth failed.")

    # Fetch the username so the user gets a confirmation
    me = reddit.user.me()
    username = me.name if me else "<unknown>"

    creds = Credentials(
        client_id=client_id,
        refresh_token=refresh_token,
        username=username,
        scopes=scopes,
    )
    save_credentials(creds)
    return creds
