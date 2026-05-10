"""`redcli auth` command group."""

from __future__ import annotations

import click

from .. import auth
from .. import output as out


@click.group("auth")
def auth_group() -> None:
    """Manage Reddit authentication."""


@auth_group.command("login")
@click.option(
    "--client-id",
    envvar="REDDIT_CLIENT_ID",
    help="Reddit installed-app client ID. Register at https://www.reddit.com/prefs/apps",
)
@click.option(
    "--port",
    default=16180,
    show_default=True,
    help="OAuth callback port. Default 16180 avoids the common 8080/3000/5000 collisions.",
)
@click.option("--scope", "scopes", multiple=True, help="Override default scopes (repeatable).")
def login(client_id: str | None, port: int, scopes: tuple[str, ...]) -> None:
    """Authenticate with Reddit via browser-based OAuth.

    \b
    First-time setup:
      1. Go to https://www.reddit.com/prefs/apps
      2. Click "create another app..."
      3. Choose type: "installed app"
      4. Set redirect uri to: http://localhost:16180/
         (16180 is φ × 10000 — chosen to avoid 8080's collision-heavy
          territory. Use --port to pick a different one.)
      5. Copy the client ID (the string under the app name)
      6. Run: redcli auth login --client-id YOUR_CLIENT_ID

    The client ID is not a secret. The OAuth flow happens entirely in your
    browser. redcli stores only a refresh token at ~/.config/redcli/credentials.json
    """
    if not client_id:
        out.err(
            "No client ID provided. Pass --client-id, set REDDIT_CLIENT_ID, "
            "or see `redcli auth login --help` for setup instructions."
        )
        raise SystemExit(2)

    scope_list = list(scopes) if scopes else None
    try:
        creds = auth.login(client_id=client_id, scopes=scope_list, port=port)
    except RuntimeError as e:
        out.err(str(e))
        raise SystemExit(1) from e

    out.console.print(
        f"\n[green]✓[/green] Logged in as [bold]{creds.username}[/bold]"
        f"\n  scopes: {', '.join(creds.scopes)}"
        f"\n  credentials saved to {auth.CREDENTIALS_PATH}"
    )


@auth_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def status(as_json: bool) -> None:
    """Show current auth state."""
    creds = auth.load_credentials()
    if creds is None:
        out.console.print("[yellow]not authenticated[/yellow] — run `redcli auth login`")
        raise SystemExit(1)
    out.emit(
        {
            "username": creds.username,
            "client_id": creds.client_id,
            "scopes": ", ".join(creds.scopes),
            "credentials_path": str(auth.CREDENTIALS_PATH),
        },
        json=as_json,
    )


@auth_group.command("logout")
@click.confirmation_option(prompt="Remove stored credentials?")
def logout() -> None:
    """Remove stored credentials."""
    auth.clear_credentials()
    out.console.print("[green]✓[/green] credentials removed")
