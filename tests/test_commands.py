import shlex

import pytest

from tars.commands import Builtin, Problem, Run, interpret, needs_terminal
from tars.git import RepoState

ST = RepoState(path=".", has_commits=True)


def test_shorthand_becomes_the_git_command():
    intent = interpret("stage 'my file.txt'", ST)
    assert isinstance(intent, Run)
    assert intent.steps[0].argv == ["git", "add", "my file.txt"]
    assert intent.after == "status"


def test_git_passes_through():
    intent = interpret("git log --oneline", ST)
    assert isinstance(intent, Run)
    assert intent.steps[0].argv == ["git", "log", "--oneline"]
    assert intent.after == "refresh"


def test_pull_uses_the_configured_strategy():
    assert interpret("pull", ST).steps[0].argv == ["git", "pull", "--ff-only"]


def test_diff_remembers_paths_to_check_for_new_files():
    assert interpret("diff new.txt", ST).new_files == ["new.txt"]


def test_builtins():
    assert interpret("q", ST) == Builtin("quit")
    assert interpret("?", ST) == Builtin("help")
    assert interpret("cb 3", ST) == Builtin("cookbook", 3)
    assert interpret("7", ST) == Builtin("cookbook", 7)
    assert interpret("cookbook all", ST) == Builtin("cookbook", "all")


def test_problems():
    assert interpret("   ", ST) is None
    assert isinstance(interpret("unstage", ST), Problem)
    assert "Parse error" in interpret("git commit -m 'oops", ST).message
    assert "bogus" in interpret("bogus", ST).message


@pytest.mark.parametrize("command, needs", [
    ("git push", True),
    ("git -C sub push", True),
    ("git pull --rebase", True),
    ("git fetch --all --prune", True),
    ("git add -p", True),
    ("git add notes.txt", False),
    ("git commit", True),
    ("git commit --amend", True),
    ("git commit -m 'fix'", False),
    ("git commit -am 'fix'", False),
    ("git commit --amend --no-edit", False),
    ("git revert HEAD", True),
    ("git revert --no-edit HEAD", False),
    ("git tag -a v1.0", True),
    ("git tag -a v1.0 -m 'release'", False),
    ("git tag v1.0", False),
    ("git rebase -i HEAD~2", True),
    ("git log -p", False),
    ("git grep -i todo", False),
    ("git status", False),
    ("git", False),
])
def test_needs_terminal(command, needs):
    assert needs_terminal(shlex.split(command)) is needs
