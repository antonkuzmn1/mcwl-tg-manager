# mcwl-tg-manager

An asynchronous Telegram bot built with aiogram. `/help` shows a concise Russian command list, and `/start` remains an unadvertised alias. The placeholder has been removed.

The help text and slash menu list only `help`, `server_start`, and `server_stop`. On startup, the bot registers Russian command descriptions with Telegram for each allowed chat, so clients can suggest them when typing `/`. Registration failures are logged without disabling polling. Reopen the chat if the client has not refreshed the command list. No BotFather setup is required for the automatic chat-scoped menu.

All commands require an allowed chat; unknown messages and commands are ignored. Menu visibility does not grant access: chat authorization still applies to manually entered commands.

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

Spaces around IDs and duplicates are accepted. Missing, empty, malformed, zero, or out-of-range values stop startup. Messages from other chats are silently discarded before command handlers run, including `/start` and `/help` in private chats. The restriction covers all message handlers; new update types must receive equivalent access control before being enabled. Group-to-supergroup migration changes the chat ID, so update the allowlist and restart the bot when needed. Changes to the environment take effect after restart.

The allowlist identifies trusted administrator chats. Every participant in an allowed chat can use server control, including anonymous senders. No per-user ID list or Telegram administrator-role check is required; whitelist administration is still pending.

The bot uses long polling and needs outbound access to Telegram; no inbound HTTP port is required. Disable any existing webhook for this bot before using polling. Stop with Ctrl+C or SIGTERM; the HTTP session is closed on shutdown. Run only one polling process per token.

## Verification

```sh
uv run --locked python -m unittest discover -s tests -v
git diff --check
```

Tests use synthetic updates and mocked Telegram requests. They do not need real credentials or a running Minecraft server.

## Server lifecycle commands

- `/server_start`: start the existing Docker container named `mc`.
- `/server_stop`: stop `mc`, giving it up to 120 seconds for graceful shutdown before Docker may force termination.

Both support `@YourBotUsername` in groups and accept no arguments. Every participant in an allowed administrator chat can use them, including anonymous administrators. Authorization is based only on `TELEGRAM_ALLOWED_CHAT_IDS`; commands from other chats are silently ignored.

The bot talks asynchronously to a host helper over `/var/lib/mcwl-control/control.sock`. The helper accepts only start/stop and read-only readiness checks for `mc`; the bot has no access to the Docker API socket, arbitrary shell commands, container creation/removal, or other containers. Install the helper using [the deployment guide](docs/DEPLOYMENT.md#5a-install-the-restricted-server-control-helper) before deploying this version. The bot container needs the helper directory bind mount and its group ID; the deployment script detects the group automatically.

The Minecraft container must already exist on the same VM under the exact name `mc`. Create it once using your existing Compose file (`docker compose up -d mc`). The bot can start a stopped container, but cannot recreate one removed with `docker compose down`. After a successful start, the bot waits for Minecraft readiness before announcing that players can join. Repeated requests report an already-running/stopped state; overlapping operations are rejected. Docker failures and timeouts produce operator-facing messages.

After `/server_start`, the bot sends a Russian loading message, then waits asynchronously for the Paper `Done (...)! For help, type "help"` marker. Only logs since the current Docker `StartedAt` timestamp count; the helper checks container ID and start time before accepting a marker. Old runs, stopped containers, and replacements cannot confirm readiness. The helper scans logs as a bounded stream instead of buffering full history and checks every three seconds for up to five minutes. A read-only readiness wait does not hold the lifecycle lock, so `/server_stop` remains available while loading.

Stop progress, successful stop, already-stopped, and stop failure replies are Russian. A final Russian message confirms readiness in the requesting chat. Timeout, exit, or restart produces a failure message instead. This confirms the Paper startup marker, not external network reachability. Retain the current run's startup logs; if those logs have been rotated away, readiness cannot be confirmed from them. Notifications follow `/server_start` requests; there is no continuous monitor for external starts, and pending notifications are not persisted across bot/helper restarts.

**Upgrade requirement:** update the root-owned host helper using [the readiness upgrade procedure](docs/DEPLOYMENT.md#updating-the-helper-for-readiness-notifications) before deploying this bot version. The new protocol adds `wait_ready`; an old helper will reject it. No new credentials or systemd unit changes are needed.

No RCON connection is required for these commands. Your Minecraft Compose file can stay as shown; optionally add `stop_grace_period: 120s` under `mc` for a similar grace period when stopping it manually through Compose. Docker's `unless-stopped` policy respects an explicit stop until the container is started again.

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
