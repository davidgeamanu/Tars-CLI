<div align="center">

```
                                ██╗ ██████╗ █████╗ ██████╗ ██╗   ██╗███████╗
                                ██║██╔════╝██╔══██╗██╔══██╗██║   ██║██╔════╝
                                ██║██║     ███████║██████╔╝██║   ██║███████╗
                                ██║██║     ██╔══██║██╔══██╗██║   ██║╚════██║
                                ██║╚██████╗██║  ██║██║  ██║╚██████╔╝███████║
                                ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

### A REPL-style CLI git assistant that keeps you oriented in any repository.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

*Banner • repo status • suggestions • git cookbook*

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
- **Status panel** — branch, clean/dirty, staged / unstaged / untracked counts, remote URL, sync info, last commit
- **Suggestions panel** — context-aware next steps shown side-by-side

</td>
<td width="50%">

### REPL Prompt
- Persistent session — stays open until you type `q`
- Prompt shows active branch: `icarus (main) >`
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
- Colour palette editable in a single file

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

#### 2. Clone or download ICARUS

```bash
git clone https://github.com/your-username/icarus.git
cd icarus
```

Or if you already have the folder, just `cd` into it:

```bash
cd C:\Projects\Icarus        # Windows
# cd ~/Projects/Icarus       # macOS / Linux
```

#### 3. Install with pipx

From **inside the ICARUS folder**, run:

```bash
pipx install .
```

This installs the `icarus` command globally so it is available in every terminal, in every folder — no virtual environment activation needed.

For editable mode (changes to the source take effect immediately):

```bash
pipx install . --editable
```

#### 4. Verify the install

```bash
icarus --help
```

If the command is found, you're done.

#### 5. Run

```bash
icarus
```

Type `icarus` from **any folder** — it always reads the git repo in your current working directory.

---

### Updating after edits

```bash
pipx reinstall icarus
```

---

## Usage

### Startup

Navigate to any folder and run `icarus`. You'll see:

1. ASCII banner + current working directory
2. Spinner while the repo is checked
3. **Repository panel** (or a "not initialised" panel in red if there's no `.git`)
4. **Suggestions panel** with context-aware next steps
5. The REPL prompt

---

### Commands

| Command | Shorthand | Description |
|---------|-----------|-------------|
| `status` | `s` | Refresh and display repo status + suggestions |
| `log` | `l` | `git log --oneline --decorate --graph -n 25` |
| `diff [args]` | | `git diff` with optional extra arguments |
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
| `quit` | `q` / `exit` | Exit ICARUS |

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

### Colours

All colours are defined at the top of `icarus/theme.py`:

```python
PRIMARY = "cyan"    # panels, borders, banner
DIM     = "dim"     # labels, secondary text
OK      = "green"   # CLEAN status
WARN    = "yellow"  # DIRTY status
ERR     = "red"     # errors, not-a-repo panel
```

Rich accepts named colours (`"magenta"`), hex (`"#a855f7"`), or RGB (`"rgb(100,200,255)"`). Change the values and run `pipx reinstall icarus`.

---

## Project Structure

```
icarus/
├── __init__.py       — package marker
├── theme.py          — console instance + colour constants
├── git.py            — RepoState dataclass, detect_repo(), git helpers
├── display.py        — ASCII banner, repo panel, suggestions panel
├── cookbook.py       — COOKBOOK data + menu/section display functions
├── repl.py           — REPL loop, command dispatch, show_help()
└── cli.py            — main() entry point, UTF-8 setup
icarus.py             — shim so `python icarus.py` still works
setup.py              — package config and `icarus` console script
.gitignore
```

---

## Author

**David Geamanu**

---

</div>

