"""Helpers for building throwaway git repos in tests."""
import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    """Run git in *cwd* and return its stdout. Fails the test if git fails."""
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8")
    assert p.returncode == 0, f"git {' '.join(args)} failed: {p.stderr}"
    return p.stdout


def write(repo: Path, name: str, text: str = "x\n") -> None:
    """Create or overwrite a file in *repo*, making folders as needed."""
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
