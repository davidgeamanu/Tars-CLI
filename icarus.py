#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ICARUS — Smart Git Assistant  (Rich REPL edition)

Install:
  pip install -e .          # registers the `icarus` command globally

Run directly (without install):
  python icarus.py
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Ensure stdout/stderr use UTF-8 (required for box-drawing characters on Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console(legacy_windows=False)

# ── colour palette ─────────────────────────────────────────────────────────────
PRIMARY = "cyan"
DIM     = "dim"
OK      = "green"
WARN    = "yellow"
ERR     = "red"


# ── git helpers ────────────────────────────────────────────────────────────────

def run(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a subprocess, return (exit_code, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]!r} not found in PATH"


@dataclass
class RepoState:
    path:        str
    repo_root:   Optional[str] = None
    branch:      Optional[str] = None
    dirty:       bool          = False
    staged:      int           = 0
    unstaged:    int           = 0
    untracked:   int           = 0
    has_origin:  bool          = False
    upstream:    Optional[str] = None
    ahead:       Optional[int] = None
    behind:      Optional[int] = None
    last_commit: Optional[str] = None
    error:       Optional[str] = None


def detect_repo(path: str) -> RepoState:
    """Inspect the git repo at *path* and return a populated RepoState."""
    st = RepoState(path=path)

    code, out, _ = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
    if code != 0 or out != "true":
        st.error = "Not inside a Git repository."
        return st

    code, root, err = run(["git", "rev-parse", "--show-toplevel"], cwd=path)
    if code != 0:
        st.error = err or "Failed to find repo root."
        return st
    st.repo_root = root

    code, br, _ = run(["git", "branch", "--show-current"], cwd=root)
    st.branch = br if code == 0 and br else "(detached HEAD)"

    code, out, err = run(["git", "status", "--porcelain"], cwd=root)
    if code != 0:
        st.error = err or "Failed to read status."
        return st

    staged = unstaged = untracked = 0
    for line in out.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            untracked += 1
        else:
            x, y = line[0], line[1]
            if x != " ":
                staged += 1
            if y != " ":
                unstaged += 1

    st.staged    = staged
    st.unstaged  = unstaged
    st.untracked = untracked
    st.dirty     = (staged + unstaged + untracked) > 0

    code, remotes, _ = run(["git", "remote"], cwd=root)
    st.has_origin = code == 0 and "origin" in remotes.splitlines()

    code, upstream, _ = run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=root,
    )
    if code == 0 and upstream:
        st.upstream = upstream
        code, counts, _ = run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=root,
        )
        if code == 0 and counts:
            lr = counts.split()
            if len(lr) == 2:
                try:
                    st.ahead  = int(lr[0])
                    st.behind = int(lr[1])
                except ValueError:
                    pass

    code, last, _ = run(
        ["git", "log", "-1", "--pretty=format:%h  %s  (%cr)"], cwd=root
    )
    if code == 0 and last:
        st.last_commit = last

    return st


# ── banner ─────────────────────────────────────────────────────────────────────

BANNER = r"""
██╗ ██████╗ █████╗ ██████╗ ██╗   ██╗███████╗
██║██╔════╝██╔══██╗██╔══██╗██║   ██║██╔════╝
██║██║     ███████║██████╔╝██║   ██║███████╗
██║██║     ██╔══██║██╔══██╗██║   ██║╚════██║
██║╚██████╗██║  ██║██║  ██║╚██████╔╝███████║
╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
""".strip("\n")


def show_banner() -> None:
    console.print()
    console.print(Align.center(Text(BANNER, style="bold cyan")))
    console.print(Align.center(Text(
        "Smart Git  •  Safe Commands  •  No Wings Melted",
        style=DIM,
    )))
    console.print()


# ── status panels ──────────────────────────────────────────────────────────────

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
    t.add_row("Remote",    "origin" if st.has_origin else "—")

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


def make_suggestions_panel(st: RepoState) -> Optional[Panel]:
    """Return a suggestions panel, or None if there is nothing to suggest."""
    if st.error:
        return None

    items: List[Tuple[str, str]] = []

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


def show_status(st: RepoState) -> None:
    repo_panel = make_repo_panel(st)
    sugg_panel = make_suggestions_panel(st)
    if sugg_panel:
        console.print(Columns([repo_panel, sugg_panel], equal=True, expand=True))
    else:
        console.print(repo_panel)


# ── cookbook ───────────────────────────────────────────────────────────────────

COOKBOOK: List[Tuple[str, str, List[Tuple[str, str]]]] = [
    (
        "Initialize a local repository",
        "Start tracking a new project with Git",
        [
            ("git init",                        "Create a new .git directory"),
            ("git add .",                       "Stage all files"),
            ('git commit -m "Initial commit"',  "Create the first commit"),
            ("git branch -M main",              "Rename branch to main (optional)"),
        ],
    ),
    (
        "Connect to a remote (GitHub/GitLab)",
        "Link your local repo to a remote hosting service",
        [
            ("git remote add origin <URL>",     "Register the remote"),
            ("git push -u origin main",         "Push & set upstream tracking"),
            ("git remote -v",                   "Verify remotes"),
        ],
    ),
    (
        "Daily workflow",
        "The everyday cycle: pull → edit → add → commit → push",
        [
            ("git pull --ff-only",              "Fetch latest, fast-forward only"),
            ("git status",                      "See what changed"),
            ("git add -p",                      "Stage changes interactively"),
            ('git commit -m "message"',         "Commit with inline message"),
            ("git push",                        "Push to remote"),
        ],
    ),
    (
        "Branching",
        "Isolate features and bug-fixes in separate branches",
        [
            ("git checkout -b feature/name",    "Create and switch to new branch"),
            ("git branch",                      "List local branches"),
            ("git switch main",                 "Switch back to main"),
            ("git branch -d feature/name",      "Delete a merged branch"),
        ],
    ),
    (
        "Keeping a branch up to date",
        "Sync a feature branch with the latest changes from main",
        [
            ("git fetch origin",                "Download remote changes"),
            ("git merge origin/main",           "Merge main into your branch"),
            ("git rebase origin/main",          "Rebase (use only on private branches)"),
        ],
    ),
    (
        "Merging a feature into main (safe)",
        "Integrate completed work back into the main branch",
        [
            ("git checkout main",               "Switch to main"),
            ("git pull --ff-only",              "Make sure main is current"),
            ("git merge feature/name",          "Merge the feature branch"),
            ("git push",                        "Push merged result"),
            ("# On conflict:",                  ""),
            ("git add <resolved-files>",        "Mark conflicts resolved"),
            ("git commit",                      "Finish the merge commit"),
        ],
    ),
    (
        "Undo & Recovery",
        "Walk back mistakes at various stages",
        [
            ("git restore <file>",              "Discard unstaged changes in a file"),
            ("git restore --staged <file>",     "Unstage a file"),
            ("git reset --soft HEAD~1",         "Undo last commit, keep staged"),
            ("git reset --mixed HEAD~1",        "Undo last commit, keep unstaged"),
            ("git reset --hard HEAD~1",         "DANGER: discard last commit entirely"),
            ("git revert HEAD",                 "Create an undo-commit (safe for shared)"),
        ],
    ),
    (
        "Stashing",
        "Temporarily shelve work without committing",
        [
            ("git stash",                       "Save current changes to stash"),
            ("git stash list",                  "View all stashes"),
            ("git stash pop",                   "Restore latest stash"),
            ("git stash drop stash@{0}",        "Delete a specific stash"),
            ("git stash branch feature/name",   "Create branch from stash"),
        ],
    ),
    (
        "Viewing history",
        "Explore commits and changes",
        [
            ("git log --oneline --graph",       "Compact branch graph"),
            ("git log -p",                      "Show patches (full diffs)"),
            ("git show <sha>",                  "Inspect one commit"),
            ("git diff main..feature/name",     "Compare two branches"),
            ("git blame <file>",                "Who changed which line"),
        ],
    ),
    (
        "Tags & Releases",
        "Mark important points in history",
        [
            ("git tag v1.0.0",                  "Create a lightweight tag"),
            ('git tag -a v1.0.0 -m "Release"',  "Create an annotated tag"),
            ("git push origin v1.0.0",          "Push a single tag"),
            ("git push origin --tags",          "Push all tags"),
            ("git tag -d v1.0.0",               "Delete local tag"),
        ],
    ),
]


def show_cookbook_menu() -> None:
    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column(style="bold cyan", justify="right", no_wrap=True)
    t.add_column(style="bold white")
    t.add_column(style=DIM)
    for i, (title, desc, _) in enumerate(COOKBOOK, 1):
        t.add_row(f"[{i}]", title, f"— {desc}")
    console.print(Panel(t, title="Git Cookbook", border_style=PRIMARY))
    console.print(Text("  Type a number to open a section.", style=DIM))
    console.print()


def show_cookbook_section(n: int) -> None:
    if not (1 <= n <= len(COOKBOOK)):
        console.print(f"[{ERR}]No section {n}. Choose 1–{len(COOKBOOK)}.[/{ERR}]")
        return
    title, desc, rows = COOKBOOK[n - 1]
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Command", style="bold white", no_wrap=True)
    t.add_column("What it does", style=DIM)
    for cmd, what in rows:
        t.add_row(cmd, what)
    console.print(Panel(t, title=f"[{n}] {title}", subtitle=desc, border_style=PRIMARY))


def show_cookbook_all() -> None:
    for i in range(1, len(COOKBOOK) + 1):
        show_cookbook_section(i)
        console.print()


# ── help ───────────────────────────────────────────────────────────────────────

def show_help() -> None:
    t = Table(show_header=False, box=None, pad_edge=False, padding=(0, 3))
    t.add_column(style="bold white",  no_wrap=True)   # command
    t.add_column(style="cyan",        no_wrap=True)   # shorthand / args
    t.add_column(style=DIM)                            # description

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
    t.add_row("quit",          "q / exit",   "Exit ICARUS")

    console.print(Panel(t, title="Commands", border_style=PRIMARY))


# ── REPL ───────────────────────────────────────────────────────────────────────

def _prompt(st: Optional[RepoState]) -> str:
    branch = f" ({st.branch})" if (st and not st.error and st.branch) else ""
    return f"icarus{branch} > "


def run_passthrough(cmd: List[str], cwd: Optional[str]) -> None:
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
            console.print("[bold cyan]Goodbye. Don't fly too close to the sun.[/bold cyan]")
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
            console.print("[bold cyan]Goodbye. Don't fly too close to the sun.[/bold cyan]")
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

        # bare number → cookbook shortcut
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


# ── entry point ────────────────────────────────────────────────────────────────

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
