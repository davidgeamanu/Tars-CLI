import os

from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from . import actions
from .commands import PULL_STRATEGY, Problem, Run, interpret, new_file_hints
from .theme import console, PRIMARY, DIM, OK, ERR
from .git import RepoState, detect_repo
from .display import make_help_panel, show_status
from .cookbook import show_cookbook_menu, show_cookbook_section, show_cookbook_all

_GOODBYE = "[bold cyan]Goodbye. Stay on the right side of the event horizon.[/bold cyan]"


def show_help() -> None:
    console.print(make_help_panel(PULL_STRATEGY))
    console.print(
        r"  [dim]Config: [white]~/.tarsrc[/white] — \[theme] colors, "
        r"\[behavior] options, \[ai] suggestions (enabled, model)[/dim]"
    )


def _prompt(st: RepoState | None) -> str:
    branch = f" ({st.branch})" if (st and not st.error and st.branch) else ""
    return f"tars{branch} > "


def run_steps(steps: list[actions.Step], cwd: str | None) -> None:
    """Run *steps* with stdio inherited so output streams live to the terminal."""
    result = actions.run(steps, cwd, capture=False)
    if result.err:
        console.print(f"[{ERR}]{escape(result.err)}[/{ERR}]")
    elif not result.ok and not result.found_differences:
        console.print(f"[{ERR}]Exit code {result.code}[/{ERR}]")


def run_passthrough(cmd: list[str], cwd: str | None) -> None:
    run_steps([actions.Step(cmd, "")], cwd)


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
            console.print(_GOODBYE)
            break

        intent = interpret(raw, st)
        if intent is None:
            continue
        cwd = st.repo_root if (st and not st.error) else os.getcwd()

        if isinstance(intent, Problem):
            console.print(f"[{ERR}]{escape(intent.message)}[/{ERR}]")

        elif isinstance(intent, Run):
            run_steps(intent.steps, cwd)
            for path, step in new_file_hints(intent.new_files, cwd):
                console.print(
                    f"[{DIM}]{escape(path)} is untracked, so git diff has nothing to compare it with. "
                    f"To see it as a diff, type:[/{DIM}]"
                )
                console.print(f"  [bold white]{escape(step.shown())}[/bold white]")
            if intent.after != "none":
                st = detect_repo(os.getcwd())
            if intent.after == "status":
                show_status(st)

        elif intent.name == "quit":
            console.print(_GOODBYE)
            break
        elif intent.name == "clear":
            console.clear()
        elif intent.name == "help":
            show_help()
        elif intent.name in ("status", "files"):
            st = detect_repo(os.getcwd())
            show_status(st, show_files=intent.name == "files")
        elif intent.name == "suggest":
            suggest_and_commit(cwd)
            st = detect_repo(os.getcwd())
            show_status(st)
        elif intent.name == "cookbook":
            if intent.arg is None:
                show_cookbook_menu()
            elif intent.arg == "all":
                show_cookbook_all()
            else:
                show_cookbook_section(intent.arg)
