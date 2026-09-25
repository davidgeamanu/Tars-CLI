import os
import re

from rich.markup import escape

from .config import get, get_bool
from .git import run
from .theme import DIM, WARN, ERR


class SuggestError(Exception):
    """Why no suggestions could be made. The message uses Rich markup."""


def _staged_diff(cwd: str) -> str:
    code, out, _ = run(["git", "diff", "--staged"], cwd=cwd)
    return out if code == 0 else ""


def _parse_suggestions(raw: str) -> list[str]:
    return [
        m.group(1).strip()
        for line in raw.splitlines()
        if (m := re.match(r"^\d+\.\s+(.+)$", line.strip()))
    ]


def commit_suggestions(cwd: str) -> list[str]:
    """Ask Claude for three commit messages for the staged diff.

    Never prints or reads input. Raises SuggestError when AI is off or not set up,
    nothing is staged, or the API call fails.
    """
    if not get_bool("ai", "enabled", False):
        raise SuggestError(
            f"[{DIM}]AI suggestions are disabled.[/{DIM}]  "
            r"Set [bold white]enabled = true[/bold white] under "
            r"[white]\[ai][/white] in [white]~/.tarsrc[/white] to enable."
        )

    try:
        import anthropic
    except ImportError:
        raise SuggestError(
            f"[{ERR}]anthropic not installed.[/{ERR}]  "
            "Run: [bold white]pip install anthropic[/bold white]"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SuggestError(
            f"[{ERR}]ANTHROPIC_API_KEY not set.[/{ERR}]  "
            "Export your Anthropic API key and try again."
        )

    diff = _staged_diff(cwd)
    if not diff.strip():
        raise SuggestError(
            f"[{WARN}]No staged changes.[/{WARN}]  "
            "Use [bold]stage[/bold] to stage files first."
        )

    if len(diff) > 8000:
        diff = diff[:8000] + "\n... (diff truncated)"

    model = get("ai", "model", "claude-haiku-4-5")

    client = anthropic.Anthropic(api_key=api_key)
    try:
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
    except anthropic.NotFoundError:
        raise SuggestError(
            f"[{ERR}]Model {model!r} not found.[/{ERR}]  "
            r"Check [white]model[/white] under [white]\[ai][/white] in [white]~/.tarsrc[/white]."
        )
    except anthropic.AuthenticationError:
        raise SuggestError(f"[{ERR}]Your ANTHROPIC_API_KEY was rejected.[/{ERR}]")
    except anthropic.APIStatusError as e:
        raise SuggestError(f"[{ERR}]The Anthropic API returned an error ({e.status_code}).[/{ERR}]")
    except anthropic.APIConnectionError:
        raise SuggestError(f"[{ERR}]Couldn't reach the Anthropic API.[/{ERR}]  Check your connection.")

    raw = next((b.text for b in response.content if b.type == "text"), "").strip()
    suggestions = _parse_suggestions(raw)
    if not suggestions:
        raise SuggestError(f"[{ERR}]Couldn't read Claude's reply:[/{ERR}]\n{escape(raw)}")
    return suggestions
