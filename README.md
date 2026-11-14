# mcwl-tg-manager

A Telegram bot project for managing a Minecraft server whitelist through RCON.

Only the Python project skeleton is currently implemented. Telegram and Minecraft connections have not been added yet.

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
