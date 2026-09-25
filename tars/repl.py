import os
import shlex

from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import actions
from .config import get, get_int
from .theme import console, PRIMARY, DIM, OK, ERR
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
    t.add_row("unstage",       "<files>",      "Unstage files, keeping your edits")
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
        r"  [dim]Config: [white]~/.tarsrc[/white] — \[theme] colors, "
        r"\[behavior] options, \[ai] suggestions (enabled, model)[/dim]"
    )


def _prompt(st: RepoState | None) -> str:
    branch = f" ({st.branch})" if (st and not st.error and st.branch) else ""
    return f"tars{branch} > "


def _found_differences(result: actions.Result) -> bool:
    # git diff exits with 1 when it finds differences (always, with --no-index); not an error
    return result.code == 1 and result.failed is not None and result.failed.argv[:2] == ["git", "diff"]


def run_steps(steps: list[actions.Step], cwd: str | None) -> None:
    """Run *steps* with stdio inherited so output streams live to the terminal."""
    result = actions.run(steps, cwd, capture=False)
    if result.err:
        console.print(f"[{ERR}]{escape(result.err)}[/{ERR}]")
    elif not result.ok and not _found_differences(result):
        console.print(f"[{ERR}]Exit code {result.code}[/{ERR}]")


def run_passthrough(cmd: list[str], cwd: str | None) -> None:
    run_steps([actions.Step(cmd, "")], cwd)


def _hint_new_files(paths: list[str], cwd: str) -> None:
    """git diff shows nothing for an untracked file, so say why and show the command that does."""
    st = detect_repo(cwd)
    if st.error:
        return
    for path in paths:
        if st.is_untracked(path) and os.path.isfile(os.path.join(cwd, path)):
            console.print(
                f"[{DIM}]{escape(path)} is untracked, so git diff has nothing to compare it with. "
                f"To see it as a diff, type:[/{DIM}]"
            )
            console.print(f"  [bold white]{escape(actions.show_new_file(path).shown())}[/bold white]")


def suggest_and_commit(cwd: str) -> None:
    """Show AI commit messages and commit with the one you pick."""
    from .ai import SuggestError, commit_suggestions

    try:
        with console.status(f"[{DIM}]Asking Claude for suggestions…[/{DIM}]", spinner="dots"):
            suggestions = commit_suggestions(cwd)
    except SuggestError as e:
        console.print(str(e))
        return

    body = Text()
    for i, s in enumerate(suggestions, 1):
        body.append(f"  {i}. ", style=f"bold {PRIMARY}")
        body.append(s + "\n")
    console.print(Panel(body, title="Suggested Commit Messages", border_style=PRIMARY))

    try:
        choice = input(
            f"  Pick 1-{len(suggestions)} to commit, or Enter to skip: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return

    if not choice:
        return

    idx = int(choice) - 1 if choice.isdigit() else -1
    if not 0 <= idx < len(suggestions):
        console.print(f"[{ERR}]Invalid choice.[/{ERR}]")
        return

    msg = suggestions[idx]
    if actions.run(actions.commit(msg), cwd, capture=False).ok:
        console.print(f"[{OK}]Committed:[/{OK}] {escape(msg)}")


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
            if args:
                _hint_new_files(args, cwd)

        # stage
        elif cmd == "stage":
            run_steps(actions.stage(args), cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # unstage
        elif cmd == "unstage":
            if not args:
                console.print(f"[{ERR}]Usage: unstage <file> … (or unstage . to unstage all)[/{ERR}]")
            else:
                run_steps(actions.unstage(st, args), cwd)
                st = detect_repo(os.getcwd())
                show_status(st)

        # suggest — AI commit message
        elif cmd in ("suggest", "sg"):
            suggest_and_commit(cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # stash
        elif cmd == "stash":
            if not args:
                run_steps(actions.stash_push(), cwd)
                st = detect_repo(os.getcwd())
                show_status(st)
            elif args[0] == "list":
                run_passthrough(["git", "stash", "list", "--color=always"], cwd=cwd)
            elif args[0] == "drop":
                run_steps(actions.stash_drop(args[1] if len(args) > 1 else None), cwd)
            else:
                run_steps(actions.stash_push(" ".join(args)), cwd)
                st = detect_repo(os.getcwd())
                show_status(st)

        # pop
        elif cmd == "pop":
            run_steps(actions.stash_pop(args), cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # fetch
        elif cmd in ("fetch", "f"):
            run_steps(actions.fetch(args), cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # pull
        elif cmd == "pull":
            run_steps(actions.pull(args, PULL_STRATEGY), cwd)
            st = detect_repo(os.getcwd())
            show_status(st)

        # push
        elif cmd == "push":
            run_steps(actions.push(args), cwd)
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
