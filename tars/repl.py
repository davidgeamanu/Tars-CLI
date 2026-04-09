import os
import shlex
import subprocess

from rich.panel import Panel
from rich.table import Table

from .theme import console, PRIMARY, DIM, ERR
from .git import RepoState, detect_repo
from .display import show_status
from .cookbook import show_cookbook_menu, show_cookbook_section, show_cookbook_all


def show_help() -> None:
    t = Table(show_header=False, box=None, pad_edge=False, padding=(0, 3))
    t.add_column(style="bold white", no_wrap=True)   # command
    t.add_column(style="cyan",       no_wrap=True)   # shorthand / args
    t.add_column(style=DIM)                           # description

    t.add_row("status",        "s",          "Refresh repo status + suggestions")
    t.add_row("log",           "l",          "git log --oneline --decorate --graph -n 25")
    t.add_row("diff",          "[args]",     "git diff with optional extra arguments")
    t.add_row("fetch",         "f",          "git fetch --all --prune")
    t.add_row("pull",          "[args]",     "git pull --ff-only (default)")
    t.add_row("push",          "[args]",     "git push")
    t.add_row("cookbook",      "cb",         "Browse numbered cookbook menu")
    t.add_row("cookbook <N>",  "",           "Show section N directly")
    t.add_row("cookbook all",  "",           "Show all sections")
    t.add_row("<number>",      "",           "Shortcut for cookbook <number>")
    t.add_row("git",           "<args>",     "Pass any git command through directly")
    t.add_row("clear",         "",           "Clear the screen")
    t.add_row("help",          "?",          "Show this help")
    t.add_row("quit",          "q / exit",   "Exit TARS")

    console.print(Panel(t, title="Commands", border_style=PRIMARY))


def _prompt(st: RepoState | None) -> str:
    branch = f" ({st.branch})" if (st and not st.error and st.branch) else ""
    return f"tars{branch} > "


def run_passthrough(cmd: list[str], cwd: str | None) -> None:
    """Run *cmd* with stdio inherited so output streams live to the terminal."""
    try:
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode != 0:
            console.print(f"[{ERR}]Exit code {result.returncode}[/{ERR}]")
    except FileNotFoundError:
        console.print(f"[{ERR}]Command not found: {cmd[0]!r}[/{ERR}]")


def repl(st: RepoState) -> None:
    while True:
        try:
            raw = input(_prompt(st)).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            console.print("[bold cyan]Goodbye. Stay on the right side of the event horizon.[/bold cyan]")
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            console.print(f"[{ERR}]Parse error: {e}[/{ERR}]")
            continue

        if not parts:
            continue

        cmd, *args = parts
        cwd = st.repo_root if (st and not st.error) else os.getcwd()

        # quit
        if cmd in ("quit", "q", "exit"):
            console.print("[bold cyan]Goodbye. Stay on the right side of the event horizon.[/bold cyan]")
            break

        # clear
        elif cmd == "clear":
            console.clear()

        # help
        elif cmd in ("help", "?"):
            show_help()

        # status
        elif cmd in ("status", "s"):
            st = detect_repo(os.getcwd())
            show_status(st)

        # log
        elif cmd in ("log", "l"):
            run_passthrough(
                ["git", "log", "--oneline", "--decorate", "--graph", "-n", "25"] + args,
                cwd=cwd,
            )

        # diff
        elif cmd == "diff":
            run_passthrough(["git", "diff"] + args, cwd=cwd)

        # fetch
        elif cmd in ("fetch", "f"):
            run_passthrough(["git", "fetch", "--all", "--prune"] + args, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # pull
        elif cmd == "pull":
            pull_args = args if args else ["--ff-only"]
            run_passthrough(["git", "pull"] + pull_args, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # push
        elif cmd == "push":
            run_passthrough(["git", "push"] + args, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # cookbook
        elif cmd in ("cookbook", "cb"):
            if not args:
                show_cookbook_menu()
            elif args[0] == "all":
                show_cookbook_all()
            else:
                try:
                    show_cookbook_section(int(args[0]))
                except ValueError:
                    console.print(f"[{ERR}]Usage: cookbook <number> | cookbook all[/{ERR}]")

        # bare number -> cookbook shortcut
        elif cmd.isdigit():
            show_cookbook_section(int(cmd))

        # git passthrough
        elif cmd == "git":
            run_passthrough(["git"] + args, cwd=cwd)
            st = detect_repo(os.getcwd())

        # unknown
        else:
            console.print(
                f"[{ERR}]Unknown command: {cmd!r}[/{ERR}]  "
                "Type [bold]help[/bold] or [bold]?[/bold] for a list."
            )
