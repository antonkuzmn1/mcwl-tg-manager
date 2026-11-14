# Handoff

## Current state

- The Python 3.12+ application uses aiogram 3 and asyncio with long polling.
- The only handler is public /start, including commands addressed to the bot in groups. It replies: "Hello! Minecraft whitelist management is coming soon."
- Other messages and commands are ignored. No Minecraft/RCON operations or privileged commands exist.
- TELEGRAM_BOT_TOKEN is required in the process environment. Missing or malformed values fail without printing the token. .env.example contains no credentials; .env files are not loaded automatically.
- Dependencies are locked in uv.lock. README.md documents installation, startup, verification, AI authorship, and future runtime secret injection.
- The HTTP session closes after polling exits or fails. aiogram handles SIGINT/SIGTERM during polling.
- All project content must be in English. Completed agent changes must use Conventional Commits.

## Latest verification

- `uv sync` installed the application and locked dependencies successfully with Python 3.14.6.
- `uv run --locked python -m unittest discover -s tests -v`: 5 tests passed, including subcases for token validation, routing in private/groups, ignored messages, and session cleanup on normal exit and failure.
- The installed entry point exits with the expected error when TELEGRAM_BOT_TOKEN is missing.
- Local Markdown links, English-only source/documentation content, and `git diff --check` passed.
- No real token was used. Telegram polling and signal handling have not been verified against a live service. No Minecraft service was contacted.

## Open questions and blockers

- No blockers for the /start placeholder.
- GitHub Actions, secret storage/delivery, and VM service configuration remain to be selected. No CI/CD, Docker configuration, or deployment has been added.
- Production polling must run as a single instance per token; an existing webhook must be disabled before polling.
- RCON library, connection settings, and authorization for future whitelist commands remain unimplemented. The public placeholder does not imply public access to future administrative operations.

## Next step

Wait for the next user-requested task. PLAN.md records the remaining configuration, RCON, authorization, deployment, and CI/CD work. Do not implement a milestone automatically.
