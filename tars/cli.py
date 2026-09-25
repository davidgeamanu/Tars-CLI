# UTF-8 reconfiguration must happen before any Rich imports (Console uses stdout)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import argparse
import os

from rich.rule import Rule

from . import __version__
from .theme import console, DIM
from .git import detect_repo
from .display import show_banner, show_status
from .repl import repl


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tars",
        description="A git assistant that keeps you oriented in any repository.",
    )
    parser.add_argument("folder", nargs="?",
                        help="folder to open (default: the current folder)")
    parser.add_argument("--version", action="version", version=f"tars {__version__}")
    args = parser.parse_args()
    if args.folder and not os.path.isdir(args.folder):
        parser.error(f"not a folder: {args.folder}")
    return args


def main() -> None:
    args = _parse_args()
    if args.folder:
        os.chdir(args.folder)

    console.clear()
    show_banner()

    console.print(f"  [dim]cwd[/dim]  [white]{os.getcwd()}[/white]")
    console.print()

    with console.status("[dim]Checking repository…[/dim]", spinner="dots"):
        st = detect_repo(os.getcwd())

    show_status(st)

    console.print()
    console.print(Rule(style="dim"))
    console.print(
        "  [dim]Type [bold white]help[/bold white] for commands  "
        "[bold white]cookbook[/bold white] for git recipes  "
        "[bold white]q[/bold white] to quit[/dim]"
    )
    console.print(Rule(style="dim"))
    console.print()

    repl(st)


if __name__ == "__main__":
    main()
