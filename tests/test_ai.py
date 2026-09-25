import pytest

from tars.ai import SuggestError, _parse_suggestions, commit_suggestions


def test_parse_keeps_only_numbered_lines():
    raw = "Here you go:\n1. feat(repl): add stage\n2.  fix: quote paths \n3. docs: readme\n"
    assert _parse_suggestions(raw) == ["feat(repl): add stage", "fix: quote paths", "docs: readme"]


def test_disabled_by_default(committed):
    # conftest points HOME at an empty folder, so there is no ~/.tarsrc turning AI on
    with pytest.raises(SuggestError, match="disabled"):
        commit_suggestions(str(committed))
