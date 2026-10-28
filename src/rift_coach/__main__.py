"""Entry point: `python -m rift_coach` (or `rift-coach` after `pip install -e .`)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .config import ConfigError, load_config
from .ddragon import DataDragon

console = Console()


def find_claude_cli() -> str | None:
    """Claude Code CLI bundled with claude-agent-sdk, or one on PATH."""
    try:
        import claude_agent_sdk

        bundled = Path(claude_agent_sdk.__file__).parent / "_bundled"
        for name in ("claude.exe", "claude"):
            if (bundled / name).exists():
                return str(bundled / name)
    except ImportError:
        pass
    return shutil.which("claude")


def run_cli(*args: str) -> int:
    cli = find_claude_cli()
    if cli is None:
        console.print("[red]Claude CLI not found. Run `pip install -e .` again.[/red]")
        return 1
    return subprocess.call([cli, *args])


async def check(cfg) -> None:
    from .llm import make_backend

    console.print(f"[dim]Asking Claude via {cfg.claude.backend} backend...[/dim]")
    answer = await make_backend(cfg).structured(
        system="Answer briefly.",
        prompt=f"Say hello in {cfg.claude.language} and name one League of Legends midlaner.",
        name="hello",
        schema={
            "type": "object",
            "properties": {"greeting": {"type": "string"}, "champion": {"type": "string"}},
            "required": ["greeting", "champion"],
        },
    )
    console.print(f"[green]OK:[/green] {answer['greeting']} ({answer['champion']})")


def print_pools(cfg, data) -> None:
    from .roles import load_viable

    p = cfg.player
    roles = ["top", "jungle", "middle", "bottom", "utility"]
    if p.pick_scope == "viable":
        viable = load_viable(list(data.champions.values()))
        console.print("Pick scope: [bold]viable[/bold] (best pick for the lobby role; "
                      "comfort picks win close calls)")
        for role in roles:
            comfort = ", ".join(p.pool_for(role)) or "-"
            count = len(viable.get(role, []))
            console.print(f"  {role:<8} {count:>3} champions, comfort: {comfort}")
    else:
        console.print("Pick scope: [bold]pool[/bold] (only your pools)")
        for role in roles:
            console.print(f"  {role:<8} {', '.join(p.pool_for(role)) or '- (no suggestion)'}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="rift-coach")
    parser.add_argument(
        "command", nargs="?", default="run", choices=["run", "login", "status", "check"],
        help="run (default) | login: sign in with your Claude plan (subscription backend, "
             "personal use only) | "
             "status: show sign-in | check: one test question to Claude",
    )
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    if args.command == "login":
        sys.exit(run_cli("auth", "login"))
    if args.command == "status":
        sys.exit(run_cli("auth", "status"))

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if args.command == "check":
        try:
            asyncio.run(check(cfg))
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Check failed: {exc}[/red]")
            sys.exit(1)
        return

    console.print("[dim]Loading Data Dragon...[/dim]")
    data = DataDragon().load()
    console.print(f"Patch [bold]{data.version}[/bold]")
    print_pools(cfg, data)

    # Imported here so unit tests don't need a running client or lcu_driver internals.
    from lcu_driver import Connector

    from .coach import Coach

    coach = Coach(cfg, data)
    # Python 3.14+: asyncio.get_event_loop() no longer creates a loop, and lcu-driver
    # still relies on it. Create one explicitly and hand it over.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    connector = Connector(loop=loop)

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

    console.print("[dim]Waiting for League Client (log in and stay in the client)... "
                  "Ctrl+C to quit.[/dim]")
    connector.start()


if __name__ == "__main__":
    main()
