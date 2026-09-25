"""What a line typed at the TARS prompt means, shared by the REPL and the board.

interpret() turns the text into an intent. Each interface decides how to carry it out:
the REPL prints to the terminal, the board shows the output in its output pane.
"""
import os
import shlex
from dataclasses import dataclass, field

from . import actions
from .actions import Step
from .config import get, get_int
from .git import RepoState, detect_repo

LOG_COUNT     = get_int("behavior", "log_count",      25)
PULL_STRATEGY = get("behavior",     "pull_strategy",  "ff-only")

_LOG_FORMAT = "%C(yellow)%h%Creset %C(auto)%d%Creset %s %C(dim white)(%cr) <%an>%Creset"


@dataclass
class Run:
    """Run git steps. Afterwards: show the status, refresh quietly, or do nothing."""
    steps: list[Step]
    after: str = "status"                                  # "status" | "refresh" | "none"
    new_files: list[str] = field(default_factory=list)     # paths to check for untracked files (diff)


@dataclass
class Builtin:
    """Something TARS does itself: quit, clear, help, status, files, cookbook, suggest."""
    name: str
    arg: int | str | None = None


@dataclass
class Problem:
    message: str


def interpret(raw: str, st: RepoState) -> Run | Builtin | Problem | None:
    """What *raw* asks for. None for an empty line."""
    try:
        parts = shlex.split(raw)
    except ValueError as e:
        return Problem(f"Parse error: {e}")
    if not parts:
        return None
    cmd, *args = parts

    if cmd in ("quit", "q", "exit"):
        return Builtin("quit")
    if cmd == "clear":
        return Builtin("clear")
    if cmd in ("help", "?"):
        return Builtin("help")
    if cmd in ("status", "s"):
        return Builtin("status")
    if cmd == "files":
        return Builtin("files")
    if cmd in ("suggest", "sg"):
        return Builtin("suggest")

    if cmd in ("log", "l"):
        # tformat ends every entry with a newline, so the prompt starts on a line of its own
        return Run([Step(["git", "log", "--graph", "--color=always",
                          f"--pretty=tformat:{_LOG_FORMAT}", "-n", str(LOG_COUNT), *args],
                         "show recent commits")], after="none")
    if cmd == "diff":
        return Run([Step(["git", "diff", "--color=always", *args], "see what changed")],
                   after="none", new_files=args)
    if cmd == "stage":
        return Run(actions.stage(args))
    if cmd == "unstage":
        if not args:
            return Problem("Usage: unstage <file> … (or unstage . to unstage all)")
        return Run(actions.unstage(st, args))
    if cmd == "stash":
        if not args:
            return Run(actions.stash_push())
        if args[0] == "list":
            return Run([Step(["git", "stash", "list", "--color=always"], "list stashes")], after="none")
        if args[0] == "drop":
            return Run(actions.stash_drop(args[1] if len(args) > 1 else None), after="none")
        return Run(actions.stash_push(" ".join(args)))
    if cmd == "pop":
        return Run(actions.stash_pop(args))
    if cmd in ("fetch", "f"):
        return Run(actions.fetch(args))
    if cmd == "pull":
        return Run(actions.pull(args, PULL_STRATEGY))
    if cmd == "push":
        return Run(actions.push(args))

    if cmd in ("cookbook", "cb"):
        if not args:
            return Builtin("cookbook")
        if args[0] == "all":
            return Builtin("cookbook", "all")
        if args[0].isdigit():
            return Builtin("cookbook", int(args[0]))
        return Problem("Usage: cookbook <number> | cookbook all")
    if cmd.isdigit():
        return Builtin("cookbook", int(cmd))

    if cmd == "git":
        return Run([Step(["git", *args], "")], after="refresh")

    return Problem(f"Unknown command: {cmd!r}  Type help or ? for a list.")


def new_file_hints(paths: list[str], cwd: str) -> list[tuple[str, Step]]:
    """git diff shows nothing for an untracked file. For each such path in *paths*:
    (path, the command that shows it)."""
    if not paths:
        return []
    st = detect_repo(cwd)
    if st.error:
        return []
    return [(p, actions.show_new_file(p)) for p in paths
            if st.is_untracked(p) and os.path.isfile(os.path.join(cwd, p))]


# Which git commands need the real terminal

_NETWORK = {"push", "pull", "fetch", "clone", "ls-remote", "submodule"}   # may ask for credentials
_TOOLS = {"mergetool", "difftool"}
_INTERACTIVE_FLAGS = {
    "add":      {"-p", "--patch", "-i", "--interactive", "-e", "--edit"},
    "checkout": {"-p", "--patch"},
    "restore":  {"-p", "--patch"},
    "reset":    {"-p", "--patch"},
    "stash":    {"-p", "--patch"},
    "commit":   {"-p", "--patch", "-i", "--interactive", "-e", "--edit"},
    "rebase":   {"-i", "--interactive", "--continue", "--edit-todo"},
    "merge":    {"-e", "--edit", "--continue"},
    "clean":    {"-i", "--interactive"},
    "config":   {"-e", "--edit"},
    "tag":      {"-e", "--edit"},
}
_MESSAGE_FLAGS = ("-m", "--message", "-F", "--file", "-C", "--reuse-message", "--no-edit")


def _has_message(args: list[str]) -> bool:
    for a in args:
        if a in _MESSAGE_FLAGS or a.startswith(("--message=", "--file=")):
            return True
        # short flags bundled together, like -am "message"
        if a.startswith("-") and not a.startswith("--") and ("m" in a[1:] or "F" in a[1:]):
            return True
    return False


def needs_terminal(argv: list[str]) -> bool:
    """True if this git command may prompt, open an editor or run interactively, so it
    can't run with its output captured."""
    if not argv or argv[0] != "git":
        return False
    args = argv[1:]
    i = 0
    while i < len(args) and args[i].startswith("-"):   # git's own options, like -C <dir>
        i += 2 if args[i] in ("-C", "-c") else 1
    if i >= len(args):
        return False
    sub, rest = args[i], args[i + 1:]

    if sub in _NETWORK or sub in _TOOLS:
        return True
    if any(a in _INTERACTIVE_FLAGS.get(sub, ()) for a in rest):
        return True
    if sub == "commit" and not _has_message(rest):
        return True                                    # opens the editor for the message
    if sub == "revert" and not any(a in ("--no-edit", "-n", "--no-commit") for a in rest):
        return True
    if sub == "tag" and any(a in ("-a", "--annotate", "-s", "--sign") for a in rest) and not _has_message(rest):
        return True
    return False
