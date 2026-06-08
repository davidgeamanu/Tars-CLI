from rich.align import Align
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import get_int
from .theme import console, PRIMARY, DIM, OK, WARN, ERR
from .git import RepoState

MAX_FILES = get_int("behavior", "max_files", 15)

# banner

BANNER = r"""
████████╗ █████╗ ██████╗ ███████╗
╚══██╔══╝██╔══██╗██╔══██╗██╔════╝
   ██║   ███████║██████╔╝███████╗
   ██║   ██╔══██║██╔══██╗╚════██║
   ██║   ██║  ██║██║  ██║███████║
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
""".strip("\n")


def show_banner() -> None:
    console.print()
    console.print(Align.center(Text(BANNER, style=f"bold {PRIMARY}")))
    console.print(Align.center(Text(
        "Humor: 75%  •  Honesty: 90%  •  Git: 100%",
        style=DIM,
    )))
    console.print()


# status panels

def make_repo_panel(st: RepoState) -> Panel:
    if st.error:
        body = Text()
        body.append("Git not initialized\n\n", style=f"bold {ERR}")
        body.append(st.error + "\n\n", style=ERR)
        body.append("Run  ", style=DIM)
        body.append("git init", style="bold white")
        body.append("  to start a repository here.", style=DIM)
        return Panel(body, title="Repository", border_style=ERR)

    status_text  = "DIRTY" if st.dirty else "CLEAN"
    status_style = f"bold {WARN}" if st.dirty else f"bold {OK}"

    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style=DIM)
    t.add_column()

    t.add_row("Root",      st.repo_root or "?")
    t.add_row("Branch",    Text(st.branch or "?", style="bold cyan"))
    t.add_row("Status",    Text(status_text, style=status_style))
    t.add_row("Staged",    str(st.staged))
    t.add_row("Unstaged",  str(st.unstaged))
    t.add_row("Untracked", str(st.untracked))

    if st.remote_url:
        t.add_row("Remote", Text(st.remote_url, style=f"cyan link {st.remote_url}"))
    else:
        t.add_row("Remote", "—")

    if st.upstream:
        ab = (
            f"ahead {st.ahead}, behind {st.behind}"
            if st.ahead is not None
            else "unknown"
        )
        t.add_row("Upstream", st.upstream)
        t.add_row("Sync",     ab)

    if st.last_commit:
        t.add_row("Last", st.last_commit)

    return Panel(t, title="Repository", border_style=PRIMARY)


def make_suggestions_panel(st: RepoState) -> Panel | None:
    """Return a suggestions panel, or None if there is nothing to suggest."""
    if st.error:
        return None

    items = []

    if st.untracked:
        items.append(("git add .",               "stage all untracked files"))
    if st.unstaged:
        items.append(("git add -p",              "interactively stage changes"))
    if st.staged:
        items.append(('git commit -m "..."',     "commit staged changes"))

    if st.upstream:
        ahead  = st.ahead  or 0
        behind = st.behind or 0
        if behind > 0 and ahead == 0:
            items.append(("git pull --ff-only",                 "fast-forward from remote"))
        elif ahead > 0 and behind == 0:
            items.append(("git push",                           "push local commits"))
        elif ahead > 0 and behind > 0:
            items.append(("git pull --rebase  then  git push",  "diverged — rebase, then push"))

    if not items:
        return None

    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column(style=f"bold {PRIMARY}", no_wrap=True)
    t.add_column(style=DIM)
    for cmd, desc in items:
        t.add_row("  " + cmd, desc)

    return Panel(t, title="Suggestions", border_style=PRIMARY)


def make_files_panel(st: RepoState) -> Panel | None:
    """Return a full-width panel listing changed files by category, or None if clean."""
    if st.error or not st.dirty:
        return None

    body = Text()
    first = True

    def add_section(label: str, files: list[str], icon: str, style: str) -> None:
        nonlocal first
        if not files:
            return
        if not first:
            body.append("\n")
        first = False
        body.append(f"{label}\n", style=f"bold {DIM}")
        for f in files[:MAX_FILES]:
            body.append(f"  {icon} {f}\n", style=style)
        if len(files) > MAX_FILES:
            body.append(f"  … and {len(files) - MAX_FILES} more\n", style=DIM)

    add_section("Staged",    st.staged_files,    "+", f"bold {OK}")
    add_section("Unstaged",  st.unstaged_files,  "~", WARN)
    add_section("Untracked", st.untracked_files, "?", DIM)

    return Panel(body, title="Changes", border_style=PRIMARY)


def show_status(st: RepoState, show_files: bool = False) -> None:
    repo_panel = make_repo_panel(st)
    sugg_panel = make_suggestions_panel(st)

    if sugg_panel:
        console.print(Columns([repo_panel, sugg_panel], equal=True, expand=True))
    else:
        console.print(repo_panel)

    if show_files:
        files_panel = make_files_panel(st)
        if files_panel:
            console.print(files_panel)
