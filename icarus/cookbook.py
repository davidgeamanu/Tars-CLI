from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .theme import console, PRIMARY, DIM, ERR

COOKBOOK: list[tuple[str, str, list[tuple[str, str]]]] = [
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
        "HEAD = your current commit.  HEAD~1 = one commit before it.  ~2 = two before, etc.",
        [
            ("# Discard file changes",               ""),
            ("git restore <file>",                   "Throw away unstaged edits in a file"),
            ("git restore --staged <file>",          "Unstage a file but keep the edits"),
            ("",                                     ""),
            ("# reset — moves HEAD back, rewrites history", ""),
            ("# safe locally; avoid if already pushed",     ""),
            ("git reset --soft HEAD~1",              "Undo commit, keep changes staged"),
            ("git reset --mixed HEAD~1",             "Undo commit, keep changes unstaged"),
            ("git reset --hard HEAD~1",              "DANGER: undo commit AND discard all changes"),
            ("",                                     ""),
            ("# revert — safer alternative to reset",        ""),
            ("# adds a new commit that cancels the old one", ""),
            ("# fine to use even after pushing",             ""),
            ("git revert HEAD",                      "Create a new commit that undoes the last one"),
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
