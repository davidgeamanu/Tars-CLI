import atexit
import os
import shutil
import tempfile

import pytest

from gitrepo import git, write

# Keep the tests away from your real ~/.tarsrc and git config. This has to happen
# before anything imports tars, because tars.config reads ~/.tarsrc on import.
_home = tempfile.mkdtemp(prefix="tars-test-home-")
atexit.register(shutil.rmtree, _home, ignore_errors=True)
os.environ["HOME"] = _home
os.environ["USERPROFILE"] = _home
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"


@pytest.fixture
def repo(tmp_path):
    """An empty repo on branch main, with no commits yet."""
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "TARS Test")
    git(tmp_path, "config", "user.email", "tars@example.com")
    return tmp_path


@pytest.fixture
def committed(repo):
    """A repo with one commit holding tracked.txt and half.txt."""
    write(repo, "tracked.txt", "one\n")
    write(repo, "half.txt", "one\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    return repo
