import shlex

from gitrepo import git, write
from tars import actions
from tars.actions import Step, pathspec
from tars.git import detect_repo


def test_shown_command_is_what_the_prompt_would_parse():
    (step,) = actions.stage(pathspec(["my file.txt"]))
    assert step.argv == ["git", "add", "my file.txt"]
    assert step.shown() == "git add 'my file.txt'"
    assert shlex.split(step.shown()) == step.argv


def test_double_dash_only_when_a_path_starts_with_a_dash():
    assert pathspec(["notes.txt"]) == ["notes.txt"]
    assert pathspec(["-notes.txt"]) == ["--", "-notes.txt"]


def test_stage_defaults_to_everything():
    (step,) = actions.stage([])
    assert step.argv == ["git", "add", "."]


def test_staging_a_path_with_spaces_from_detect_repo(committed):
    write(committed, "my file.txt")
    st = detect_repo(str(committed))

    result = actions.run(actions.stage(pathspec(st.untracked_files)), str(committed))

    assert result.ok, result.err
    assert detect_repo(str(committed)).staged_files == ["my file.txt"]


def test_unstage_after_first_commit_uses_restore(committed):
    write(committed, "tracked.txt", "two\n")
    git(committed, "add", "tracked.txt")
    st = detect_repo(str(committed))

    steps = actions.unstage(st, ["tracked.txt"])
    assert steps[0].argv == ["git", "restore", "--staged", "tracked.txt"]

    assert actions.run(steps, str(committed)).ok
    after = detect_repo(str(committed))
    assert after.staged_files == []
    assert after.unstaged_files == ["tracked.txt"]


def test_unstage_before_first_commit(repo):
    write(repo, "notes.txt", "one\n")
    git(repo, "add", "notes.txt")
    write(repo, "notes.txt", "two\n")   # staged, then edited: git rm --cached refuses this one
    st = detect_repo(str(repo))

    steps = actions.unstage(st, ["notes.txt"])
    assert steps[0].argv == ["git", "reset", "--", "notes.txt"]

    result = actions.run(steps, str(repo))
    assert result.ok, result.err
    after = detect_repo(str(repo))
    assert after.staged_files == []
    assert after.untracked_files == ["notes.txt"]
    assert (repo / "notes.txt").read_text(encoding="utf-8") == "two\n"   # edits kept


def test_unstage_a_deleted_file_before_first_commit(repo):
    write(repo, "gone.txt")
    git(repo, "add", "gone.txt")
    (repo / "gone.txt").unlink()
    st = detect_repo(str(repo))

    assert actions.run(actions.unstage(st, ["gone.txt"]), str(repo)).ok
    assert not detect_repo(str(repo)).dirty


def test_run_stops_at_the_first_failure(committed):
    write(committed, "tracked.txt", "two\n")
    steps = [Step(["git", "add", "missing.txt"], ""), Step(["git", "add", "tracked.txt"], "")]

    result = actions.run(steps, str(committed))

    assert not result.ok
    assert result.failed is steps[0]
    assert detect_repo(str(committed)).staged_files == []


def test_run_reports_a_missing_program(tmp_path):
    for capture in (True, False):
        result = actions.run([Step(["no-such-program-tars"], "")], str(tmp_path), capture=capture)
        assert result.code == 127
        assert "not found" in result.err


def test_stash_drop_names_the_entry():
    assert actions.stash_drop("1")[0].argv == ["git", "stash", "drop", "stash@{1}"]
    assert actions.stash_drop()[0].argv == ["git", "stash", "drop"]


def test_stash_push_with_a_message():
    assert actions.stash_push("wip login")[0].argv == ["git", "stash", "push", "-m", "wip login"]
    assert actions.stash_push()[0].argv == ["git", "stash", "push"]


def test_pull_uses_the_strategy_only_without_args():
    assert actions.pull([], "ff-only")[0].argv == ["git", "pull", "--ff-only"]
    assert actions.pull(["--rebase"], "ff-only")[0].argv == ["git", "pull", "--rebase"]


def test_show_new_file_diffs_an_untracked_file(committed):
    write(committed, "new.txt", "hello\n")
    result = actions.run([actions.show_new_file("new.txt")], str(committed))
    assert result.code == 1          # git diff --no-index exits 1 when it finds differences
    assert "+hello" in result.out
