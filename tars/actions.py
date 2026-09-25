"""Git actions shared by the REPL and the TUI.

Each action returns the steps it stands for instead of running them, so the same
command can be shown to you to type, or run for you with run().
"""
import shlex
import subprocess
from dataclasses import dataclass

from .git import RepoState, git_lock, run as run_captured


@dataclass
class Step:
    argv: list[str]   # ["git", "add", "tars/repl.py"]
    what: str         # "stage changes"

    def shown(self) -> str:
        """The command exactly as you would type it at the TARS prompt."""
        return shlex.join(self.argv)


@dataclass
class Result:
    code:   int
    out:    str = ""
    err:    str = ""
    failed: Step | None = None   # the step that stopped the run, if any

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def found_differences(self) -> bool:
        """git diff exits with 1 when it finds differences (always, with --no-index): not an error."""
        return self.code == 1 and self.failed is not None and self.failed.argv[:2] == ["git", "diff"]


def pathspec(paths: list[str]) -> list[str]:
    """File paths as git arguments.

    "--" is added only when a path starts with "-", so the command shown stays the
    one people normally type.
    """
    return ["--", *paths] if any(p.startswith("-") for p in paths) else list(paths)


# actions

def stage(args: list[str]) -> list[Step]:
    return [Step(["git", "add", *(args or ["."])], "stage changes")]


def unstage(st: RepoState, args: list[str]) -> list[Step]:
    if not st.has_commits:
        # git restore --staged needs HEAD, which doesn't exist before the first commit.
        # reset always gets "--": without it, a file deleted from disk is ambiguous.
        sep = [] if "--" in args else ["--"]
        return [Step(["git", "reset", *sep, *args], "unstage, keeping your edits")]
    return [Step(["git", "restore", "--staged", *args], "unstage, keeping your edits")]


def stash_push(message: str | None = None) -> list[Step]:
    extra = ["-m", message] if message else []
    return [Step(["git", "stash", "push", *extra], "stash your changes")]


def stash_drop(n: str | None = None) -> list[Step]:
    target = [f"stash@{{{n}}}"] if n is not None else []
    return [Step(["git", "stash", "drop", *target], "delete a stash")]


def stash_pop(args: list[str]) -> list[Step]:
    return [Step(["git", "stash", "pop", *args], "restore the latest stash")]


def fetch(args: list[str]) -> list[Step]:
    return [Step(["git", "fetch", "--all", "--prune", *args], "download remote changes")]


def pull(args: list[str], strategy: str) -> list[Step]:
    return [Step(["git", "pull", *(args or [f"--{strategy}"])], "get remote changes")]


def push(args: list[str]) -> list[Step]:
    return [Step(["git", "push", *args], "upload your commits")]


def commit(message: str) -> list[Step]:
    return [Step(["git", "commit", "-m", message], "commit staged changes")]


def discard(args: list[str]) -> list[Step]:
    return [Step(["git", "restore", *args], "throw away your edits")]


# views

def diff(args: list[str], staged: bool = False) -> Step:
    if staged:
        return Step(["git", "diff", "--staged", *args], "see what's staged")
    return Step(["git", "diff", *args], "see what changed")


def show_new_file(path: str) -> Step:
    """git diff shows nothing for an untracked file; this shows it as all-new lines."""
    return Step(["git", "diff", "--no-index", "--", "/dev/null", path], "see a new file as a diff")


# running

def run(steps: list[Step], cwd: str | None, *, capture: bool = True,
        env: dict[str, str] | None = None) -> Result:
    """Run *steps* in order and stop at the first failure. Never prints.

    With capture=False git inherits the terminal, so output streams live and git can
    ask for credentials; the Result then only carries the exit code. *env* adds
    environment variables to captured runs.
    """
    outs: list[str] = []
    errs: list[str] = []
    for step in steps:
        if capture:
            code, out, err = run_captured(step.argv, cwd=cwd, env=env)
        else:
            try:
                with git_lock:
                    code, out, err = subprocess.run(step.argv, cwd=cwd).returncode, "", ""
            except FileNotFoundError:
                code, out, err = 127, "", f"{step.argv[0]!r} not found in PATH"
        if out:
            outs.append(out)
        if err:
            errs.append(err)
        if code != 0:
            return Result(code, "\n".join(outs), "\n".join(errs), failed=step)
    return Result(0, "\n".join(outs), "\n".join(errs))
