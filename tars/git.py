import subprocess
from dataclasses import dataclass, field


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a subprocess, return (exit_code, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
        return p.returncode, (p.stdout or "").rstrip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]!r} not found in PATH"


@dataclass
class RepoState:
    path:            str
    repo_root:       str | None  = None
    branch:          str | None  = None
    dirty:           bool        = False
    staged:          int         = 0
    unstaged:        int         = 0
    untracked:       int         = 0
    staged_files:    list[str]   = field(default_factory=list)
    unstaged_files:  list[str]   = field(default_factory=list)
    untracked_files: list[str]   = field(default_factory=list)
    has_origin:      bool        = False
    remote_url:      str | None  = None
    upstream:        str | None  = None
    ahead:           int | None  = None
    behind:          int | None  = None
    last_commit:     str | None  = None
    error:           str | None  = None


def _to_https(url: str) -> str:
    """Normalise a git remote URL to a browser-friendly HTTPS URL."""
    if url.startswith("https://"):
        return url.removesuffix(".git")
    if url.startswith("git@"):
        # git@github.com:user/repo.git  ->  https://github.com/user/repo
        url = url[4:]
        if ":" in url:
            host, path = url.split(":", 1)
            return f"https://{host}/{path.removesuffix('.git')}"
    return url


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
    staged_files: list[str] = []
    unstaged_files: list[str] = []
    untracked_files: list[str] = []
    for line in out.splitlines():
        if not line:
            continue
        x, y, path = line[0], line[1], line[3:]
        if x == "?" and y == "?":
            untracked += 1
            untracked_files.append(path)
        else:
            # renames: "old -> new" — display the new path
            if " -> " in path:
                path = path.split(" -> ")[-1]
            if x != " ":
                staged += 1
                staged_files.append(path)
            if y != " ":
                unstaged += 1
                unstaged_files.append(path)

    st.staged          = staged
    st.unstaged        = unstaged
    st.untracked       = untracked
    st.staged_files    = staged_files
    st.unstaged_files  = unstaged_files
    st.untracked_files = untracked_files
    st.dirty           = (staged + unstaged + untracked) > 0

    code, remotes, _ = run(["git", "remote"], cwd=root)
    st.has_origin = code == 0 and "origin" in remotes.splitlines()

    if st.has_origin:
        code, raw_url, _ = run(["git", "remote", "get-url", "origin"], cwd=root)
        if code == 0 and raw_url:
            st.remote_url = _to_https(raw_url.strip())

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
