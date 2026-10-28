"""Entry point: `python -m rift_coach` (or `rift-coach` after `pip install -e .`)."""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

from .config import ConfigError, load_config
from .ddragon import DataDragon

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(prog="rift-coach")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    console.print("[dim]Loading Data Dragon...[/dim]")
    data = DataDragon().load()
    console.print(f"Patch [bold]{data.version}[/bold], pool: {', '.join(cfg.player.champion_pool)}")

    # Imported here so unit tests don't need a running client or lcu_driver internals.
    from lcu_driver import Connector

    from .coach import Coach

    coach = Coach(cfg, data)
    connector = Connector()

    @connector.ready
    async def on_ready(connection):
        console.print("[green]Connected to League Client. Waiting for champ select...[/green]")

    @connector.ws.register("/lol-champ-select/v1/session", event_types=("CREATE", "UPDATE"))
    async def on_session(connection, event):
        await coach.on_session(connection, event.data)

    @connector.ws.register("/lol-champ-select/v1/session", event_types=("DELETE",))
    async def on_session_end(connection, event):
        coach.reset()
        console.print("[dim]Champ select ended.[/dim]")

    @connector.close
    async def on_close(connection):
        console.print("[yellow]League Client closed.[/yellow]")

    connector.start()


if __name__ == "__main__":
    main()
