# UTF-8 reconfiguration must happen before any Rich imports (Console uses stdout)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import os

from rich.rule import Rule

from .theme import console, DIM
from .git import detect_repo
from .display import show_banner, show_status
from .repl import repl


def main() -> None:
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
