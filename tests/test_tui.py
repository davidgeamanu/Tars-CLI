import asyncio

from textual.widgets import Input, RichLog, Static

from gitrepo import git, write
from tars.tui import Board, FileList, file_hints
from tars.git import detect_repo


def drive(folder, script, size=(100, 34)):
    """Run the board headless in *folder* and hand it to the async *script*."""
    async def main():
        app = Board(cwd=str(folder))
        async with app.run_test(size=size) as pilot:
            await settle(app, pilot)
            await script(app, pilot)
    asyncio.run(main())


async def settle(app, pilot):
    # A command runs on a worker, which then starts a refresh worker
    for _ in range(4):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def type_command(app, pilot, text):
    await pilot.press("colon")
    for ch in text:
        await pilot.press("space" if ch == " " else ch)
    await pilot.press("enter")
    await settle(app, pilot)


def columns(app):
    return {lst.column: lst.paths for lst in app.query(FileList)}


def status(repo):
    return git(repo, "status", "--porcelain")


def test_files_land_in_the_right_columns(committed):
    write(committed, "tracked.txt", "two\n")
    write(committed, "half.txt", "two\n")
    git(committed, "add", "half.txt")
    write(committed, "new.txt")

    async def script(app, pilot):
        assert columns(app) == {"untracked": ["new.txt"],
                                "unstaged": ["tracked.txt"],
                                "staged": ["half.txt"]}

    drive(committed, script)


def test_hints_show_the_commands_for_the_selected_file(committed):
    write(committed, "my file.txt")
    write(committed, "tracked.txt", "two\n")

    async def script(app, pilot):
        hints = app.query_one("#hints", Static)
        assert "git add 'my file.txt'" in str(hints.content)
        await pilot.press("right")
        assert isinstance(app.focused, FileList) and app.focused.column == "unstaged"
        assert "git restore tracked.txt" in str(hints.content)

    drive(committed, script)


def test_arrow_keys_skip_empty_columns(committed):
    write(committed, "new.txt")
    write(committed, "tracked.txt", "two\n")
    git(committed, "add", "tracked.txt")        # nothing unstaged

    async def script(app, pilot):
        assert app.focused.column == "untracked"
        await pilot.press("right")
        assert app.focused.column == "staged"
        await pilot.press("h")
        assert app.focused.column == "untracked"

    drive(committed, script)


def test_hints_for_every_column(committed):
    write(committed, "tracked.txt", "two\n")
    st = detect_repo(str(committed))
    assert [c for c, _, _ in file_hints(st, "unstaged", "tracked.txt")] == [
        "git add tracked.txt", "git diff tracked.txt", "git restore tracked.txt"]
    assert [c for c, _, _ in file_hints(st, "staged", "tracked.txt")] == [
        "git restore --staged tracked.txt", "git diff --staged tracked.txt"]
    assert [c for c, _, _ in file_hints(st, "untracked", "newdir/")] == ["git add newdir/"]


def test_typed_command_runs_and_the_board_redraws(committed):
    write(committed, "new.txt")

    async def script(app, pilot):
        await type_command(app, pilot, "git add new.txt")
        assert columns(app)["staged"] == ["new.txt"]
        assert app.query_one("#command", Input).value == ""
        log = app.query_one("#output", RichLog)
        assert "tars > git add new.txt" in "\n".join(line.text for line in log.lines)

    drive(committed, script)


def test_board_keys_never_change_the_repo(committed):
    write(committed, "new.txt")
    write(committed, "tracked.txt", "two\n")
    before = status(committed)

    async def script(app, pilot):
        for key in ["right", "left", "down", "up", "space", "enter", "a", "s", "p", "P", "f",
                    "g", "z", "c", "m", "d", "r", "j", "k", "h", "l", "escape"]:
            await pilot.press(key)
        await settle(app, pilot)
        assert app.query_one("#command", Input).value == ""

    drive(committed, script)
    assert status(committed) == before


def test_command_bar_is_never_filled_in_for_you(committed):
    write(committed, "new.txt")

    async def script(app, pilot):
        command = app.query_one("#command", Input)
        for key in ["right", "down", "r", "colon", "escape", "left"]:
            await pilot.press(key)
            await settle(app, pilot)
            assert command.value == ""

    drive(committed, script)


def test_outside_a_repo_then_git_init(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    async def script(app, pilot):
        assert app.query_one("#columns").display is False
        await type_command(app, pilot, "git init")
        assert app.query_one("#columns").display is True

    drive(tmp_path, script)


def test_editor_command_fails_clearly_without_a_terminal(committed):
    # Headless there is no terminal to hand over, so git commit (which opens an editor)
    # runs captured and fails at once instead of hanging
    write(committed, "tracked.txt", "two\n")
    git(committed, "add", "tracked.txt")

    async def script(app, pilot):
        await type_command(app, pilot, "git commit")
        text = "\n".join(line.text for line in app.query_one("#output", RichLog).lines)
        assert "-m" in text and "Exit code" in text

    drive(committed, script)
    assert "tracked.txt" in status(committed)    # nothing was committed
