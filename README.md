# mcwl-tg-manager

An asynchronous Telegram bot built with aiogram. Currently, only `/start` is implemented:

> Hello! Minecraft whitelist management is coming soon.

The command works in private and group chats, including `/start@YourBotUsername`. Other messages and commands are ignored. The placeholder is available only in explicitly allowed chats; there are no privileged operations or Minecraft connections yet.

## AI disclosure

The code in this repository was written by OpenAI Codex under the project owner's direction. The project owner did not write the code manually.

## Requirements

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

## Running

Install the locked dependencies from the project root:

```sh
uv sync --locked
```

Create a Telegram bot using BotFather. Supply its token as `TELEGRAM_BOT_TOKEN` and a comma-separated chat allowlist as `TELEGRAM_ALLOWED_CHAT_IDS`, then run:

```sh
uv run --locked mcwl-tg-manager
```

For a local Bash/Zsh session, enter the token without displaying it or saving it in shell history:

```sh
read -r -s TELEGRAM_BOT_TOKEN
export TELEGRAM_BOT_TOKEN
export TELEGRAM_ALLOWED_CHAT_IDS="-1001234567890,-987654321"
uv run --locked mcwl-tg-manager
```

The `.env.example` file lists the required variable. It is a template, not a loaded configuration file: the application reads only the process environment. Missing or malformed tokens cause startup to fail with an English error without printing the token. Token format validation does not check whether Telegram accepts the token.

## Allowed chats

`TELEGRAM_ALLOWED_CHAT_IDS` is required. For example:

```sh
export TELEGRAM_ALLOWED_CHAT_IDS="-1001234567890,-987654321,123456789"
```

Use numeric Telegram chat IDs, not usernames or invite links. Group and supergroup IDs are negative; a private chat must have its own ID explicitly included. The IDs above are examples. Obtain the real ID from a trusted Telegram client/tool or an update's `message.chat.id`; never disclose the bot token to an ID lookup service.

Spaces around IDs and duplicates are accepted. Missing, empty, malformed, zero, or out-of-range values stop startup. Messages from other chats are silently discarded before command handlers run, including `/start` in private chats. The restriction covers all message handlers; new update types must receive equivalent access control before being enabled. Group-to-supergroup migration changes the chat ID, so update the allowlist and restart the bot when needed. Changes to the environment take effect after restart.

The allowlist controls chats, not individual members: any member of an allowed chat can use the placeholder. User-level authorization for future administrative commands is still pending.

The bot uses long polling and needs outbound access to Telegram; no inbound HTTP port is required. Disable any existing webhook for this bot before using polling. Stop with Ctrl+C or SIGTERM; the HTTP session is closed on shutdown. Run only one polling process per token.

## Verification

```sh
uv run --locked python -m unittest discover -s tests -v
git diff --check
```

Tests use synthetic updates and mocked Telegram requests. They do not need real credentials or a running Minecraft server.

## CI/CD and VM deployment

See [the deployment guide](docs/DEPLOYMENT.md) for the full manual setup: SSH access, Docker, a dedicated GitHub self-hosted runner, production secrets/variables, deployment, logs, and rollback. It assumes a private repository and a Linux VM with systemd.

The CI/CD workflow runs offline tests on GitHub-hosted runners with Python 3.12 and 3.14. After both pass, main pushes or main-only manual runs build and deploy a Docker image on the production runner. PRs do not deploy. Workflow actions and container base images are pinned to immutable revisions/digests.

Set `TELEGRAM_BOT_TOKEN` as a GitHub production environment secret and `TELEGRAM_ALLOWED_CHAT_IDS` as a production environment variable. Repository-level values are an alternative if your GitHub plan does not support private environment secrets; the guide explains the environment configuration adjustment. SSH keys are not required in GitHub: the runner connects outbound from the VM.

Runtime secrets stay outside the checkout and image. The deployment validates configuration before replacing the service and checks process liveness afterward; verify actual Telegram connectivity with `/start` manually. RCON and whitelist administration are not implemented.

## Project structure

- `src/mcwl_tg_manager/`: configuration, async application, and entry point.
- `tests/`: offline configuration, command routing, and lifecycle tests.
- `pyproject.toml` and `uv.lock`: dependency declaration and locked environment.
- `.github/workflows/pipeline.yml`: hosted CI and production-runner deployment.
- `Dockerfile`, `deploy/`, and `scripts/`: container packaging and deployment helpers.
- `docs/DEPLOYMENT.md`: manual infrastructure setup and operations guide.

## Development workflow

- [AGENTS.md](AGENTS.md): development rules and verification requirements.
- [PLAN.md](PLAN.md): proposed milestones and acceptance criteria.
- [HANDOFF.md](HANDOFF.md): current state, verification, and the next step.

Work proceeds in small tasks: define acceptance criteria, implement, verify, update the documents, and create a Conventional Commit. Planned milestones are implemented only when requested.
