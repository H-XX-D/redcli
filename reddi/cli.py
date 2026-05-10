"""reddi entry point.

The command surface intentionally mirrors `gh`'s ergonomics: top-level verbs
for actions (post, comment, status, watch, search, crosspost, flairs), with
grouped subcommands for state management (auth, inbox, subs).
"""

from __future__ import annotations

import click

from . import __version__
from .commands.auth_cmd import auth_group
from .commands.comment import comment as comment_cmd
from .commands.completion import completion as completion_cmd
from .commands.crosspost import crosspost as crosspost_cmd
from .commands.flairs import flairs as flairs_cmd
from .commands.history import history as history_cmd
from .commands.inbox import inbox_group
from .commands.launch import launch as launch_cmd
from .commands.me import me as me_cmd
from .commands.post import post as post_cmd
from .commands.search import search as search_cmd
from .commands.status import status as status_cmd
from .commands.subs import subs_group
from .commands.watch import watch as watch_cmd


@click.group()
@click.version_option(version=__version__, prog_name="reddi")
def cli() -> None:
    """A modern command-line client for Reddit.

    Built for the launch/monitor workflow: write a post, watch how it's doing,
    reply to comments, and crosspost to the next sub — all from your shell.

    First-time setup:

      \b
      1. Register an "installed app" at https://www.reddit.com/prefs/apps
         (redirect URI: http://localhost:16180/)
      2. reddi auth login --client-id YOUR_CLIENT_ID
      3. reddi me  # confirm it works

    Common workflows:

      \b
      reddi post --sub SideProject --title "I built X" --body-file post.md
      reddi watch  <post-url>
      reddi inbox list
      reddi comment <comment-url> --body "thanks for trying it!"
      reddi crosspost <post-url> --to MacApps --title "[X] does Y"
    """


cli.add_command(auth_group)
cli.add_command(comment_cmd)
cli.add_command(completion_cmd)
cli.add_command(crosspost_cmd)
cli.add_command(flairs_cmd)
cli.add_command(history_cmd)
cli.add_command(inbox_group)
cli.add_command(launch_cmd)
cli.add_command(me_cmd)
cli.add_command(post_cmd)
cli.add_command(search_cmd)
cli.add_command(status_cmd)
cli.add_command(subs_group)
cli.add_command(watch_cmd)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
