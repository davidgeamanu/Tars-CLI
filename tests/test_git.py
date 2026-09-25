from gitrepo import git, write
from tars.git import detect_repo


def test_outside_a_repo_reports_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    st = detect_repo(str(tmp_path))
    assert st.error == "Not inside a Git repository."


def test_new_repo_has_no_commits(repo):
    st = detect_repo(str(repo))
    assert st.error is None
    assert st.branch == "main"
    assert not st.has_commits
    assert not st.dirty


def test_files_land_in_the_right_columns(committed):
    write(committed, "tracked.txt", "two\n")      # edited, not staged
    write(committed, "half.txt", "two\n")
    git(committed, "add", "half.txt")
    write(committed, "half.txt", "three\n")       # staged, then edited again
    write(committed, "staged.txt")
    git(committed, "add", "staged.txt")           # new file, staged
    write(committed, "new.txt")                   # untracked

    st = detect_repo(str(committed))

    assert st.has_commits
    assert st.staged_files == ["half.txt", "staged.txt"]
    assert st.unstaged_files == ["half.txt", "tracked.txt"]
    assert st.untracked_files == ["new.txt"]
    assert (st.staged, st.unstaged, st.untracked) == (2, 2, 1)
    assert st.dirty


def test_rename_shows_only_the_new_path(committed):
    git(committed, "mv", "tracked.txt", "renamed.txt")
    st = detect_repo(str(committed))
    assert st.staged_files == ["renamed.txt"]
    assert st.unstaged_files == []
    assert st.untracked_files == []


def test_path_with_spaces_comes_back_unquoted(committed):
    write(committed, "my file.txt")
    st = detect_repo(str(committed))
    assert st.untracked_files == ["my file.txt"]


def test_non_ascii_path_comes_back_intact(committed):
    write(committed, "café.txt")
    st = detect_repo(str(committed))
    assert st.untracked_files == ["café.txt"]


def test_new_folder_is_one_entry(committed):
    write(committed, "newdir/a.txt")
    write(committed, "newdir/b.txt")
    st = detect_repo(str(committed))
    assert st.untracked_files == ["newdir/"]
    assert st.is_untracked("newdir/a.txt")
    assert st.is_untracked("newdir\\a.txt")
    assert st.is_untracked("newdir")
    assert not st.is_untracked("tracked.txt")


def test_ahead_of_upstream(committed, tmp_path_factory):
    remote = tmp_path_factory.mktemp("remote")
    git(remote, "init", "-q", "--bare")
    git(committed, "remote", "add", "origin", str(remote))
    git(committed, "push", "-q", "-u", "origin", "main")
    write(committed, "tracked.txt", "two\n")
    git(committed, "commit", "-q", "-am", "second")

    st = detect_repo(str(committed))

    assert st.has_origin
    assert st.upstream == "origin/main"
    assert (st.ahead, st.behind) == (1, 0)
