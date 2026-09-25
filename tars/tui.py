"""The board: a full-screen view of the repo that stays in place. Run it with `tars --tui`.

Nothing on the board changes the repo by itself. The hint panel shows the git commands for
the selected file, and you type them in the command bar, which accepts everything the
classic prompt does.
"""
import os

from rich.color import Color, ColorParseError
from rich.markup import escape
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option
from textual.worker import get_current_worker

from . import actions
from .actions import Result, Step, pathspec
from .commands import PULL_STRATEGY, Builtin, Problem, Run, interpret, needs_terminal, new_file_hints
from .cookbook import COOKBOOK, make_cookbook_menu, make_cookbook_section, no_section_message
from .display import make_help_panel, make_repo_panel, suggestions
from .git import RepoState, detect_repo
from .theme import console, PRIMARY, DIM, OK, WARN, ERR

COLUMNS = {"untracked": "Untracked", "unstaged": "Unstaged", "staged": "Staged"}


# What the board shows

def file_hints(st: RepoState, column: str, path: str) -> list[tuple[str, str, bool]]:
    """The commands for one file on the board, as (command, what it does, loses work)."""
    spec = pathspec([path])
    code = st.codes.get(path, "  ")
    if column == "untracked":
        if path.endswith("/"):
            return [(actions.stage(spec)[0].shown(), "stage this new folder", False)]
        return [(actions.stage(spec)[0].shown(), "stage this new file", False),
                (actions.show_new_file(path).shown(), "see it as a diff", False)]
    if column == "unstaged":
        if code[1] == "D":
            return [(actions.stage(spec)[0].shown(), "stage the deletion", False),
                    (actions.discard(spec)[0].shown(), "bring the file back", False)]
        return [(actions.stage(spec)[0].shown(), "stage your changes", False),
                (actions.diff(spec).shown(), "see what changed", False),
                (actions.discard(spec)[0].shown(), "throw away your edits (can't be undone)", True)]
    return [(actions.unstage(st, spec)[0].shown(), "unstage, keeping your edits", False),
            (actions.diff(spec, staged=True).shown(), "see what's staged", False)]


def _half_staged(st: RepoState, path: str) -> bool:
    return path in st.staged_files and path in st.unstaged_files


def _item(st: RepoState, column: str, path: str) -> Text:
    code = st.codes.get(path, "??")
    letter = {"untracked": "?", "unstaged": code[1], "staged": code[0]}[column]
    style = {"untracked": DIM, "unstaged": WARN, "staged": OK}[column]
    text = Text.assemble((letter + " ", f"bold {style}"), path)
    if _half_staged(st, path):
        text.append(" ◐", style=DIM)
    return text


def _hints(st: RepoState, column: str, path: str) -> Text:
    text = Text(path, style="bold")
    if _half_staged(st, path):
        text.append("   ◐ part of this file is staged; git add stages the rest", style=DIM)
    rows = file_hints(st, column, path)
    width = max(len(command) for command, _, _ in rows)
    for command, what, loses_work in rows:
        text.append("\n  ")
        text.append(command.ljust(width), style=f"bold {WARN}" if loses_work else "bold")
        text.append("   " + what, style=WARN if loses_work else DIM)
    return text


def _hex(color: str) -> str:
    # Textual drops backgrounds given as 256-colour names like deep_sky_blue1; hex works
    try:
        return Color.parse(color).get_truecolor().hex
    except ColorParseError:
        return color


def _header(st: RepoState) -> Text:
    text = Text()
    text.append(" TARS ", style=f"bold white on {_hex(PRIMARY)}")   # a span, so only the badge is coloured
    if st.error:
        text.append("  not a git repository   ", style=f"bold {ERR}")
        text.append(st.path, style=DIM)
        return text
    text.append(f"  {st.branch}", style="bold cyan")
    if st.upstream:
        ahead = "?" if st.ahead is None else st.ahead
        behind = "?" if st.behind is None else st.behind
        text.append(f"  ↑{ahead} ↓{behind}  {st.upstream}", style=DIM)
    text.append(f"   {st.repo_root}", style=DIM)
    return text


def _next_steps(st: RepoState) -> Text:
    text = Text("Next: ", style=DIM)
    if st.error:
        return text.append_text(Text.assemble(("git init", f"bold {PRIMARY}"),
                                              ("  start a repository here", DIM)))
    items = suggestions(st)
    if not items:
        return text.append("nothing to do", style=DIM)
    for i, (command, what) in enumerate(items):
        if i:
            text.append("  ·  ", style=DIM)
        text.append(command, style=f"bold {PRIMARY}")
        text.append(f"  {what}", style=DIM)
    return text


def _in_color(step: Step) -> Step:
    # git only colours output for a terminal; the output pane shows colour too
    if step.argv[:1] == ["git"]:
        return Step(["git", "-c", "color.ui=always", *step.argv[1:]], step.what)
    return step


# Widgets

class FileList(OptionList):
    """One column of the board."""

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    def __init__(self, column: str) -> None:
        super().__init__(id=column, markup=False)
        self.column = column
        self.paths: list[str] = []
        self.border_title = COLUMNS[column]

    def show(self, st: RepoState, paths: list[str]) -> None:
        """Fill the column, keeping the selection on the same file when it's still here."""
        old_index = self.highlighted
        keep = self.paths[old_index] if old_index is not None and old_index < len(self.paths) else None
        self.paths = list(paths)
        self.clear_options()
        self.add_options([Option(_item(st, self.column, p)) for p in paths])
        self.border_title = f"{COLUMNS[self.column]} ({len(paths)})"
        if paths:
            self.highlighted = paths.index(keep) if keep in paths else min(old_index or 0, len(paths) - 1)

    @property
    def selected_path(self) -> str | None:
        if self.highlighted is None or not self.paths:
            return None
        return self.paths[self.highlighted]


class Board(App):
    TITLE = "TARS"
    AUTO_FOCUS = None
    ENABLE_COMMAND_PALETTE = False

    # $panel-lighten-2 for resting borders: the theme's $border-blurred is nearly the
    # background colour, which would hide the columns' borders and titles
    CSS = """
    #header { height: 1; }
    #columns { height: 1fr; }
    FileList { width: 1fr; height: 1fr; max-height: 100%; border: round $panel-lighten-2; }
    FileList:focus { border: round $border; }
    #nogit { height: 1fr; display: none; }
    #hints { height: auto; min-height: 4; padding: 0 1; border-top: solid $panel-lighten-2; }
    #suggestions { height: auto; padding: 0 1; }
    #output { height: 14; display: none; border: round $panel-lighten-2; }
    #output.shown { display: block; }
    #bar { height: 1; margin-top: 1; }
    #prompt { width: auto; color: $accent; text-style: bold; }
    #command { width: 1fr; }
    """

    BINDINGS = [
        Binding("left,h", "column(-1)", "Column", key_display="←→"),
        Binding("right,l", "column(1)", "Column", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("colon", "command", "Type a command", key_display=":"),
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, cwd: str | None = None) -> None:
        super().__init__()
        self.cwd = cwd or os.getcwd()
        self.st = RepoState(path=self.cwd)
        self.last_list: FileList | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        with Horizontal(id="columns"):
            for column in COLUMNS:
                yield FileList(column)
        yield Static(id="nogit")
        yield Static(id="hints")
        yield Static(id="suggestions")
        yield RichLog(id="output", wrap=True, markup=False, highlight=False)
        with Horizontal(id="bar"):
            yield Static("tars > ", id="prompt")
            yield Input(id="command", placeholder="press : to type a command, like git status",
                        compact=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#hints", Static).update(Text("Checking repository…", style=DIM))
        self.refresh_repo()

    @property
    def git_cwd(self) -> str:
        """Where git commands run: the repo root, or the starting folder outside a repo."""
        return self.st.repo_root if not self.st.error and self.st.repo_root else self.cwd

    # Repo state

    @work(thread=True, exclusive=True, group="refresh")
    def refresh_repo(self) -> None:
        st = detect_repo(self.cwd)
        if not get_current_worker().is_cancelled:
            self.call_from_thread(self.show_state, st)

    def show_state(self, st: RepoState) -> None:
        self.st = st
        self.query_one("#header", Static).update(_header(st))
        self.query_one("#suggestions", Static).update(_next_steps(st))
        columns = self.query_one("#columns")
        nogit = self.query_one("#nogit", Static)
        hints = self.query_one("#hints", Static)

        if st.error:
            columns.display = False
            nogit.display = True
            nogit.update(make_repo_panel(st))
            hints.update("")
            return

        columns.display = True
        nogit.display = False
        lists = {lst.column: lst for lst in self.query(FileList)}
        lists["untracked"].show(st, st.untracked_files)
        lists["unstaged"].show(st, st.unstaged_files)
        lists["staged"].show(st, st.staged_files)

        # Never take focus from the command bar; otherwise stay on a column that has files
        focused = self.focused
        if focused is None or (isinstance(focused, FileList) and not focused.option_count):
            first = next((lst for lst in lists.values() if lst.option_count), None)
            if first is not None:
                first.focus()
        self.show_hints()

    def show_hints(self) -> None:
        if self.st.error:
            return
        hints = self.query_one("#hints", Static)
        lst = self.focused if isinstance(self.focused, FileList) else self.last_list
        if lst is None or not lst.option_count:
            lst = next((l for l in self.query(FileList) if l.option_count), None)
        if lst is None:
            hints.update(Text("Nothing to commit: the working tree is clean.", style=DIM))
            return
        hints.update(_hints(self.st, lst.column, lst.selected_path or lst.paths[0]))

    @on(OptionList.OptionHighlighted)
    def _moved(self) -> None:
        self.show_hints()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, FileList):
            self.last_list = event.widget
            self.show_hints()

    # Keys

    def action_column(self, delta: int) -> None:
        order = list(self.query(FileList))
        current = self.focused if isinstance(self.focused, FileList) else self.last_list
        i = order.index(current) + delta if current in order else (0 if delta > 0 else len(order) - 1)
        while 0 <= i < len(order):
            if order[i].option_count:
                order[i].focus()
                return
            i += delta

    def action_refresh(self) -> None:
        self.refresh_repo()

    def action_command(self) -> None:
        self.query_one("#command", Input).focus()

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            target = self.last_list if self.last_list and self.last_list.option_count else None
            target = target or next((l for l in self.query(FileList) if l.option_count), None)
            self.set_focus(target)
        else:
            self.query_one("#output", RichLog).remove_class("shown")

    # The command bar

    def output(self) -> RichLog:
        log = self.query_one("#output", RichLog)
        log.add_class("shown")
        return log

    def write_output(self, content) -> None:
        self.output().write(content)

    @on(Input.Submitted, "#command")
    def _submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""
        intent = interpret(raw, self.st)
        if intent is None:
            return
        out = self.output()
        out.write(Text(f"tars > {raw}", style=f"bold {PRIMARY}"))

        if isinstance(intent, Problem):
            out.write(Text(intent.message, style=ERR))
        elif isinstance(intent, Run):
            if any(needs_terminal(step.argv) for step in intent.steps):
                self.run_in_terminal(raw, intent)
            else:
                self.run_captured(intent)
        else:
            self.builtin(intent)

    def builtin(self, intent: Builtin) -> None:
        out = self.output()
        if intent.name == "quit":
            self.exit()
        elif intent.name == "clear":
            out.clear()
        elif intent.name == "help":
            out.write(make_help_panel(PULL_STRATEGY))
            out.write(Text("On the board: ←→ columns, ↑↓ files, r refresh, : type, Esc back, q quit",
                           style=DIM))
        elif intent.name in ("status", "files"):
            out.write(Text("refreshed", style=DIM))
            self.refresh_repo()
        elif intent.name == "suggest":
            out.write(Text("Asking Claude for suggestions…", style=DIM))
            self.suggest()
        elif intent.name == "cookbook":
            if intent.arg is None:
                out.write(make_cookbook_menu())
                out.write(Text("Type cookbook <number> to open a section.", style=DIM))
            elif intent.arg == "all":
                for n in range(1, len(COOKBOOK) + 1):
                    out.write(make_cookbook_section(n))
            else:
                panel = make_cookbook_section(intent.arg)
                out.write(panel if panel else Text(no_section_message(intent.arg), style=ERR))

    @work(thread=True, group="command")
    def run_captured(self, intent: Run) -> None:
        cwd = self.git_cwd
        # Nothing can answer a prompt here, so make git fail with a message instead of
        # waiting: no password prompts, and an "editor" that exits at once
        result = actions.run([_in_color(s) for s in intent.steps], cwd,
                             env={"GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "false"})
        hints = new_file_hints(intent.new_files, cwd)
        self.call_from_thread(self.show_result, result, hints)
        self.call_from_thread(self.refresh_repo)

    def show_result(self, result: Result, hints: list[tuple[str, Step]]) -> None:
        out = self.output()
        if result.out:
            out.write(Text.from_ansi(result.out))
        if result.err:
            out.write(Text.from_ansi(result.err, style=DIM if result.ok else ERR))
        if not result.ok and not result.found_differences:
            out.write(Text(f"Exit code {result.code}", style=ERR))
        elif result.ok and not result.out and not result.err:
            out.write(Text("done", style=DIM))
        for path, step in hints:
            out.write(Text(f"{path} is untracked, so git diff has nothing to compare it with. "
                           "To see it as a diff, type:", style=DIM))
            out.write(Text("  " + step.shown(), style="bold"))

    def run_in_terminal(self, raw: str, intent: Run) -> None:
        """Hand the terminal to git (for credentials, editors, interactive modes), then come back."""
        cwd = self.git_cwd
        result = None
        try:
            with self.suspend():
                console.print(f"[bold {PRIMARY}]tars > {escape(raw)}[/]")
                try:
                    result = actions.run(intent.steps, cwd, capture=False)
                    if not result.ok and not result.found_differences:
                        console.print(f"[{ERR}]{escape(result.err or f'Exit code {result.code}')}[/{ERR}]")
                    console.print()
                    # Without this pause the output would vanish as soon as the board comes back
                    input("Press Enter to return to TARS...")
                except (KeyboardInterrupt, EOFError):
                    pass
        except SuspendNotSupported:
            self.run_captured(intent)   # no real terminal here (tests), so capture instead
            return
        if result is not None:
            self.output().write(Text("ran in the terminal" if result.ok else f"exit code {result.code}",
                                     style=DIM if result.ok else ERR))
        self.refresh_repo()

    @work(thread=True, group="command")
    def suggest(self) -> None:
        from .ai import SuggestError, commit_suggestions
        try:
            messages = commit_suggestions(self.git_cwd)
        except SuggestError as e:
            self.call_from_thread(self.write_output, Text.from_markup(str(e)))
            return
        text = Text("Type one of these to commit:", style=DIM)
        for message in messages:
            text.append("\n  " + actions.commit(message)[0].shown(), style="bold")
        self.call_from_thread(self.write_output, text)


def run_tui(folder: str | None = None) -> None:
    Board(cwd=folder).run()
