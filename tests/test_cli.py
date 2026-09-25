import subprocess
import sys

from tars import __version__


def tars(*args: str, cwd=None, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tars.cli", *args], cwd=cwd, input=stdin,
                          capture_output=True, text=True, encoding="utf-8")


def test_version():
    p = tars("--version")
    assert p.returncode == 0
    assert p.stdout.strip() == f"tars {__version__}"


def test_rejects_a_folder_that_does_not_exist(tmp_path):
    p = tars(str(tmp_path / "nope"))
    assert p.returncode == 2
    assert "not a folder" in p.stderr


def test_opens_the_given_folder(repo, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    p = tars(str(repo), cwd=elsewhere, stdin="q\n")
    assert p.returncode == 0
    assert "tars (main) >" in p.stdout
