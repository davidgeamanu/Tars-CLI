<div align="center">

```
                                      ████████╗ █████╗ ██████╗ ███████╗
                                      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝
                                         ██║   ███████║██████╔╝███████╗
                                         ██║   ██╔══██║██╔══██╗╚════██║
                                         ██║   ██║  ██║██║  ██║███████║
                                         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
```

### A REPL-style CLI git assistant that keeps you oriented in any repository.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)


[Features](#features) •
[Getting Started](#getting-started) •
[Usage](#usage) •
[Cookbook](#cookbook) •
[Customisation](#customisation) •
[Project Structure](#project-structure)

</div>

---

## Features

<table>
<tr>
<td width="50%">

### Startup
- **ASCII banner** with current working directory
- **Live repo spinner** while git is queried
- **Status panel** showing branch, clean/dirty, staged / unstaged / untracked counts, remote URL, sync info, last commit
- **Suggestions panel** with context-aware next steps shown side-by-side

</td>
<td width="50%">

### REPL Prompt
- Persistent session that stays open until you type `q`
- Prompt shows active branch: `tars (main) >`
- Built-in shortcuts for the most common git operations
- Full git pass-through for everything else

</td>
</tr>
<tr>
<td width="50%">

### Git Cookbook
- 10 reference sections covering the full git workflow
- Numbered menu — type a number to jump straight to a section
- Inline comments explain *why*, not just *what*
- Covers: init, remotes, daily flow, branching, merging, undo, stash, history, tags

</td>
<td width="50%">

### Quality of Life
- `shlex`-based argument parsing — quoted commit messages work correctly
- Repo state re-detected after every mutating command
- Clickable remote URL in terminals that support hyperlinks
- `~/.tarsrc` config file for colours and behaviour — no code edits needed

</td>
</tr>
</table>

<div>

---

## Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| **Python** | 3.9+ |
| **pipx** | any |

### Installation

#### 1. Install pipx (if you don't have it)

```bash
pip install pipx
pipx ensurepath
```

> **Restart your terminal** after running `ensurepath` so the new PATH takes effect.

#### 2. Clone or download TARS

```bash
git clone https://github.com/davidgeamanu/Tars-CLI.git
cd tars
```

Or if you already have the folder, just `cd` into it:

```bash
cd path\to\tars        # Windows
# cd path/to/tars      # macOS / Linux
```

#### 3. Install with pipx

From **inside the TARS folder**, run:

```bash
pipx install .
```

This installs the `tars` command globally so it is available in every terminal, in every folder — no virtual environment activation needed.

For editable mode (changes to the source take effect immediately):

```bash
pipx install . --editable
```

#### 4. Verify the install

```bash
tars --help
```

If the command is found, you're done.

#### 5. Run

```bash
tars
```

Type `tars` from **any folder**, it always reads the git repo in your current working directory.

---

### Updating after edits

```bash
pipx reinstall tars
```

---

## Usage

### Startup

Navigate to any folder and run `tars`. You'll see:

1. ASCII banner + current working directory
2. Spinner while the repo is checked
3. **Repository panel** (or a "not initialised" panel in red if there's no `.git`)
4. **Suggestions panel** with context-aware next steps
5. The REPL prompt

Type `files` at any point to see a colour-coded list of staged, unstaged, and untracked files.

---

### Commands

| Command | Shorthand | Description |
|---------|-----------|-------------|
| `status` | `s` | Refresh repo status + suggestions |
| `files` | | Show changed / untracked file list |
| `log [args]` | `l` | `git log` with graph and color |
| `diff [args]` | | `git diff` with color |
| `suggest` | `sg` | AI commit message suggestions (needs `ANTHROPIC_API_KEY`) |
| `stage [files]` | | `git add` (defaults to `.` for all) |
| `unstage <files>` | | `git restore --staged <files>` |
| `stash [msg]` | | Stash working changes with optional message |
| `stash list` | | List all stashes |
| `stash drop [n]` | | Drop a stash entry (default: latest) |
| `pop` | | `git stash pop` |
| `fetch` | `f` | `git fetch --all --prune` |
| `pull [args]` | | `git pull --ff-only` (default) |
| `push [args]` | | `git push` |
| `cookbook` | `cb` | Browse numbered cookbook menu |
| `cookbook <N>` | | Show section N directly |
| `cookbook all` | | Dump all sections |
| `<number>` | | Shortcut for `cookbook <number>` |
| `git <args>` | | Pass any git command through directly |
| `clear` | | Clear the screen |
| `help` | `?` | Show command reference |
| `quit` | `q` / `exit` | Exit TARS |

---

### Status Panel

When inside a git repository the status panel shows:

| Field | Description |
|-------|-------------|
| **Root** | Absolute path to the repo root |
| **Branch** | Current branch name |
| **Status** | `CLEAN` or `DIRTY` |
| **Staged** | Number of staged files |
| **Unstaged** | Number of unstaged files |
| **Untracked** | Number of untracked files |
| **Remote** | Clickable HTTPS URL of `origin` (if set) |
| **Upstream** | Tracking branch |
| **Sync** | How many commits ahead / behind the remote |
| **Last** | Short hash, message, and relative timestamp of last commit |

---

## Cookbook

The built-in cookbook covers 10 sections. Access from the REPL with `cookbook` or `cb`:

| # | Section |
|---|---------|
| 1 | Initialize a local repository |
| 2 | Connect to a remote (GitHub / GitLab) |
| 3 | Daily workflow |
| 4 | Branching |
| 5 | Keeping a branch up to date |
| 6 | Merging a feature into main (safe) |
| 7 | Undo & Recovery |
| 8 | Stashing |
| 9 | Viewing history |
| 10 | Tags & Releases |

Each section is a two-column table of commands and plain-English descriptions. Section 7 (Undo & Recovery) includes inline notes explaining `HEAD`, `reset` vs `revert`, and when each is safe to use.

---

## Customisation

Create `~/.tarsrc` (INI format) to override colours or behaviour without touching the source:

```ini
[theme]
primary = deep_sky_blue1   # panels, borders, banner
ok      = green            # CLEAN status
warn    = yellow           # DIRTY status
err     = red              # errors, not-a-repo panel
dim     = dim              # labels, secondary text

[behavior]
max_files     = 15         # max files shown per category in 'files' command
log_count     = 25         # number of commits shown by 'log'
pull_strategy = ff-only    # default pull flag (ff-only | rebase | no-rebase)

[ai]
enabled = false            # set to true to enable AI commit suggestions (opt-in)
model   = claude-haiku-4-5  # default; use claude-opus-4-8 for more complex diffs
```

Rich accepts named colours (`magenta`), hex (`#a855f7`), or RGB (`rgb(100,200,255)`). Changes to `~/.tarsrc` take effect the next time you run `tars` — no reinstall needed.

### AI commit suggestions

The `suggest` command calls the Claude API to analyse your staged diff and propose three [Conventional Commit](https://www.conventionalcommits.org/) messages. Pick a number to commit immediately, or press Enter to skip.

AI suggestions are **opt-in** — nothing runs until you enable them in `~/.tarsrc`.

**Setup:**

1. Get an API key from [console.anthropic.com](https://console.anthropic.com) (separate from a Claude Pro subscription - the API has its own billing, pay-as-you-go).
2. Install the SDK and set your key:

```bash
pip install anthropic          # or: pipx inject tars anthropic
export ANTHROPIC_API_KEY=sk-…  # add to your shell profile to persist it
```

3. Enable in `~/.tarsrc`:

```ini
[ai]
enabled = true
model   = claude-haiku-4-5    # default; use claude-opus-4-8 for more complex diffs
```

To disable without removing the key, set `enabled = false` (or omit the key entirely — the default is disabled).

---

## Project Structure

```
tars/
├── __init__.py       — package marker
├── config.py         — ~/.tarsrc reader (colours + behaviour overrides)
├── theme.py          — console instance + colour constants
├── git.py            — RepoState dataclass, detect_repo(), git helpers
├── display.py        — ASCII banner, repo/suggestions/files panels
├── cookbook.py       — COOKBOOK data + menu/section display functions
├── repl.py           — REPL loop, command dispatch, show_help()
├── ai.py             — Claude-powered commit message suggestions
└── cli.py            — main() entry point, UTF-8 setup
tars.py               — shim so 'python tars.py' still works
setup.py              — package config and 'tars' console script
~/.tarsrc             — optional user config (colours, behaviour)
.gitignore
```

---

## Author

**David Geamanu**

---

</div>
