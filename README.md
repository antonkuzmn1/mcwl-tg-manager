# mcwl-tg-manager

A Telegram bot project for managing a Minecraft server whitelist through RCON.

Only the Python project skeleton is currently implemented. Telegram and Minecraft connections have not been added yet.

## AI disclosure

The code in this repository was written by OpenAI Codex under the project owner's direction. The project owner did not write the code manually.

## Requirements

Python 3.12 or newer.

## Running

From the project root, without installing dependencies:

```sh
PYTHONPATH=src python3 -m mcwl_tg_manager
```

For development with an editable package installation:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
mcwl-tg-manager
```

## Project structure

- `src/mcwl_tg_manager/` — application package and entry point.
- `pyproject.toml` — package configuration; no external dependencies yet.

## Development workflow

- [AGENTS.md](AGENTS.md): development rules and verification requirements.
- [PLAN.md](PLAN.md): proposed milestones and acceptance criteria.
- [HANDOFF.md](HANDOFF.md): current state, verification, and the next step.

Work proceeds in small tasks: define acceptance criteria, implement, verify, update the documents, and create a Conventional Commit. Planned milestones are implemented only when requested.
