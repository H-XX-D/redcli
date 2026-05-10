"""`reddi completion` — emit shell completion scripts."""

from __future__ import annotations

import click
from click.shell_completion import get_completion_class

from .. import output as out

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@click.command("completion")
@click.argument("shell", type=click.Choice(SUPPORTED_SHELLS))
def completion(shell: str) -> None:
    """Emit a shell completion script for SHELL (bash, zsh, fish).

    \b
    To enable for the current shell session:
      eval "$(reddi completion bash)"     # bash
      eval "$(reddi completion zsh)"      # zsh
      reddi completion fish | source       # fish

    \b
    To install permanently:
      bash:  reddi completion bash >> ~/.bashrc
      zsh:   reddi completion zsh  >> ~/.zshrc
      fish:  reddi completion fish > ~/.config/fish/completions/reddi.fish

    After install, `reddi <TAB>` will complete commands and `reddi p<TAB>`
    will autocomplete to `reddi post`. Subcommand and flag completion works
    too: `reddi auth <TAB>` lists `login status logout`.
    """
    # Late import to avoid circular dependency (cli imports this module)
    from ..cli import cli

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        out.err(f"Unknown shell: {shell}")
        raise SystemExit(2)

    comp = comp_cls(cli, {}, "reddi", "_REDDI_COMPLETE")
    click.echo(comp.source())
