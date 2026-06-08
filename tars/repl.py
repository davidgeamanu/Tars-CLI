import os
import shlex
import subprocess

from rich.panel import Panel
from rich.table import Table

from .config import get, get_int
from .theme import console, PRIMARY, DIM, ERR
from .git import RepoState, detect_repo
from .display import show_status
from .cookbook import show_cookbook_menu, show_cookbook_section, show_cookbook_all

LOG_COUNT     = get_int("behavior", "log_count",      25)
PULL_STRATEGY = get("behavior",     "pull_strategy",  "ff-only")

_LOG_FORMAT = "%C(yellow)%h%Creset %C(auto)%d%Creset %s %C(dim white)(%cr) <%an>%Creset"


def show_help() -> None:
    t = Table(show_header=False, box=None, pad_edge=False, padding=(0, 3))
    t.add_column(style="bold white", no_wrap=True)   # command
    t.add_column(style="cyan",       no_wrap=True)   # shorthand / args
    t.add_column(style=DIM)                           # description

    t.add_row("status",        "s",            "Refresh repo status")
    t.add_row("files",         "",             "Show changed / untracked file list")
    t.add_row("log",           "l [args]",     "Git log with graph and color")
    t.add_row("diff",          "[args]",       "Git diff with color")
    t.add_row("stage",         "[files]",      "git add (defaults to . for all)")
    t.add_row("unstage",       "<files>",      "git restore --staged <files>")
    t.add_row("stash",         "[msg]",        "Stash working changes with optional message")
    t.add_row("stash list",    "",             "List all stashes")
    t.add_row("stash drop",    "[n]",          "Drop stash entry (default: latest)")
    t.add_row("pop",           "",             "Pop latest stash")
    t.add_row("suggest",       "sg",           "AI commit message suggestions (enable in ~/.tarsrc [ai])")
    t.add_row("fetch",         "f",            "git fetch --all --prune")
    t.add_row("pull",          "[args]",       f"git pull (default: --{PULL_STRATEGY})")
    t.add_row("push",          "[args]",       "git push")
    t.add_row("cookbook",      "cb [n]",       "Browse numbered cookbook menu")
    t.add_row("cookbook all",  "",             "Show all cookbook sections")
    t.add_row("<number>",      "",             "Shortcut for cookbook <number>")
    t.add_row("git",           "<args>",       "Pass any git command through directly")
    t.add_row("clear",         "",             "Clear the screen")
    t.add_row("help",          "?",            "Show this help")
    t.add_row("quit",          "q / exit",     "Exit TARS")

    console.print(Panel(t, title="Commands", border_style=PRIMARY))
    console.print(
        "  [dim]Config:[/dim] [white]~/.tarsrc[/white]  "
        r"[dim]- set [white]\[theme][/white] colors, [white]\[behavior][/white] "
        r"options, or [white]\[ai][/white] model (default: claude-opus-4-8)[/dim]"
    )


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

        # files — explicit file list
        elif cmd == "files":
            st = detect_repo(os.getcwd())
            show_status(st, show_files=True)

        # log
        elif cmd in ("log", "l"):
            run_passthrough(
                ["git", "log", "--graph", "--color=always",
                 f"--pretty=format:{_LOG_FORMAT}", "-n", str(LOG_COUNT)] + args,
                cwd=cwd,
            )
            console.print()  # trailing newline after graph output

        # diff
        elif cmd == "diff":
            run_passthrough(["git", "diff", "--color=always"] + args, cwd=cwd)

        # stage
        elif cmd == "stage":
            targets = args if args else ["."]
            run_passthrough(["git", "add"] + targets, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # unstage
        elif cmd == "unstage":
            if not args:
                console.print(f"[{ERR}]Usage: unstage <file> … (or unstage . to unstage all)[/{ERR}]")
            else:
                run_passthrough(["git", "restore", "--staged"] + args, cwd=cwd)
                st = detect_repo(os.getcwd())
                show_status(st)

        # suggest — AI commit message
        elif cmd in ("suggest", "sg"):
            from .ai import suggest_commit
            suggest_commit(cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # stash
        elif cmd == "stash":
            if not args:
                run_passthrough(["git", "stash", "push"], cwd=cwd)
                st = detect_repo(os.getcwd())
                show_status(st)
            elif args[0] == "list":
                run_passthrough(["git", "stash", "list", "--color=always"], cwd=cwd)
            elif args[0] == "drop":
                drop_args = [f"stash@{{{args[1]}}}"] if len(args) > 1 else []
                run_passthrough(["git", "stash", "drop"] + drop_args, cwd=cwd)
            else:
                run_passthrough(["git", "stash", "push", "-m", " ".join(args)], cwd=cwd)
                st = detect_repo(os.getcwd())
                show_status(st)

        # pop
        elif cmd == "pop":
            run_passthrough(["git", "stash", "pop"] + args, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # fetch
        elif cmd in ("fetch", "f"):
            run_passthrough(["git", "fetch", "--all", "--prune"] + args, cwd=cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # pull
        elif cmd == "pull":
            pull_args = args if args else [f"--{PULL_STRATEGY}"]
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
