import os
import re
import subprocess

from rich.panel import Panel
from rich.text import Text

from .config import get, get_bool
from .git import run
from .theme import console, PRIMARY, DIM, OK, WARN, ERR


def _staged_diff(cwd: str) -> str:
    code, out, _ = run(["git", "diff", "--staged"], cwd=cwd)
    return out if code == 0 else ""


def suggest_commit(cwd: str) -> None:
    if not get_bool("ai", "enabled", False):
        console.print(
            f"[{DIM}]AI suggestions are disabled.[/{DIM}]  "
            r"Set [bold white]enabled = true[/bold white] under "
            r"[white]\[ai][/white] in [white]~/.tarsrc[/white] to enable."
        )
        return

    try:
        import anthropic
    except ImportError:
        console.print(
            f"[{ERR}]anthropic not installed.[/{ERR}]  "
            "Run: [bold white]pip install anthropic[/bold white]"
        )
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(
            f"[{ERR}]ANTHROPIC_API_KEY not set.[/{ERR}]  "
            "Export your Anthropic API key and try again."
        )
        return

    diff = _staged_diff(cwd)
    if not diff.strip():
        console.print(
            f"[{WARN}]No staged changes.[/{WARN}]  "
            "Use [bold]stage[/bold] to stage files first."
        )
        return

    if len(diff) > 8000:
        diff = diff[:8000] + "\n... (diff truncated)"

    model = get("ai", "model", "claude-haiku-4-5")

    console.print(f"[{DIM}]Asking Claude for suggestions...[/{DIM}]", end="\r")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                "Suggest 3 commit messages for this diff. "
                "Use Conventional Commits format (type(scope): description). "
                "Reply with exactly 3 numbered lines — no other text:\n"
                "1. <message>\n2. <message>\n3. <message>\n\n"
                f"```diff\n{diff}\n```"
            ),
        }]
    )

    raw = next((b.text for b in response.content if b.type == "text"), "").strip()

    suggestions = [
        m.group(1).strip()
        for line in raw.splitlines()
        if (m := re.match(r"^\d+\.\s+(.+)$", line.strip()))
    ]

    console.print(" " * 40, end="\r")  # clear "Asking..." line

    if not suggestions:
        console.print(Panel(raw, title="Suggestions", border_style=PRIMARY))
        return

    body = Text()
    for i, s in enumerate(suggestions, 1):
        body.append(f"  {i}. ", style=f"bold {PRIMARY}")
        body.append(s + "\n")

    console.print(Panel(body, title="Suggested Commit Messages", border_style=PRIMARY))

    try:
        choice = input(
            f"  Pick 1-{len(suggestions)} to commit, or Enter to skip: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return

    if not choice:
        return

    try:
        idx = int(choice) - 1
    except ValueError:
        console.print(f"[{ERR}]Invalid choice.[/{ERR}]")
        return

    if not 0 <= idx < len(suggestions):
        console.print(f"[{ERR}]Invalid choice.[/{ERR}]")
        return

    msg = suggestions[idx]
    result = subprocess.run(["git", "commit", "-m", msg], cwd=cwd)
    if result.returncode == 0:
        console.print(f"[{OK}]Committed:[/{OK}] {msg}")
