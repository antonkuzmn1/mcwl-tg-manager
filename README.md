# mcwl-tg-manager

An asynchronous Telegram bot built with aiogram. Currently, only `/start` is implemented:

> Hello! Minecraft whitelist management is coming soon.

The command works in private and group chats, including `/start@YourBotUsername`. Other messages and commands are ignored. The placeholder is public; there are no privileged operations or Minecraft connections yet.

## AI disclosure

The code in this repository was written by OpenAI Codex under the project owner's direction. The project owner did not write the code manually.

## Requirements

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

## Running

Install the locked dependencies from the project root:

```sh
uv sync --locked
```

Create a Telegram bot using BotFather. Supply its token as the `TELEGRAM_BOT_TOKEN` environment variable, then run:

```sh
uv run --locked mcwl-tg-manager
```

For a local Bash/Zsh session, enter the token without displaying it or saving it in shell history:

```sh
read -r -s TELEGRAM_BOT_TOKEN
export TELEGRAM_BOT_TOKEN
uv run --locked mcwl-tg-manager
```

The `.env.example` file lists the required variable. It is a template, not a loaded configuration file: the application reads only the process environment. Missing or malformed tokens cause startup to fail with an English error without printing the token. Token format validation does not check whether Telegram accepts the token.

The bot uses long polling and needs outbound access to Telegram; no inbound HTTP port is required. Disable any existing webhook for this bot before using polling. Stop with Ctrl+C or SIGTERM; the HTTP session is closed on shutdown. Run only one polling process per token.

## Verification

```sh
uv run --locked python -m unittest discover -s tests -v
git diff --check
```

Tests use synthetic updates and mocked Telegram requests. They do not need real credentials or a running Minecraft server.

## Future deployment

The bot reads credentials at runtime so a future GitHub Actions workflow and VM service can inject secrets without application changes. Do not commit a real token, put it in a Docker image, or print it in pipeline logs. GitHub secrets are not yet configured. The VM runtime secret storage and delivery mechanism will be selected when deployment is implemented.

Docker, CI/CD, VM provisioning, RCON, and whitelist authorization are not implemented. Deployment should replace a single polling instance and forward shutdown signals to the process.

## Project structure

- `src/mcwl_tg_manager/`: configuration, async application, and entry point.
- `tests/`: offline configuration, command routing, and lifecycle tests.
- `pyproject.toml` and `uv.lock`: dependency declaration and locked environment.

## Development workflow

- [AGENTS.md](AGENTS.md): development rules and verification requirements.
- [PLAN.md](PLAN.md): proposed milestones and acceptance criteria.
- [HANDOFF.md](HANDOFF.md): current state, verification, and the next step.

Work proceeds in small tasks: define acceptance criteria, implement, verify, update the documents, and create a Conventional Commit. Planned milestones are implemented only when requested.
