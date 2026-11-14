# Project instructions

## Language

Use English for all project content, including code, comments, documentation, configuration descriptions, and user-facing messages. Do not use Russian in project files.

## Project context

This project will manage a Minecraft server whitelist from Telegram through RCON. An asynchronous aiogram bot handles /start and admin-only /server_start and /server_stop for the existing mc container; whitelist management is not implemented. Read README.md for setup, PLAN.md for milestones, and HANDOFF.md for current state before starting work.

## Workflow

1. Inspect the working tree and relevant code before editing. Preserve unrelated user changes.
2. Work on the task requested by the user. A planned milestone is not permission to implement it automatically.
3. For implementation work, define the expected behavior and acceptance criteria in PLAN.md before coding. Keep tasks small and independently verifiable.
4. Implement the smallest complete change. Add meaningful tests for behavior, authorization, validation, and error handling as those features are introduced.
5. Run checks appropriate to the change. Report failures and checks that could not be run; never describe unverified behavior as working.
6. Update README.md when setup or usage changes, PLAN.md when milestone status changes, and HANDOFF.md at the end of each task or before handing work over.
7. Commit every completed change you make automatically, using English Conventional Commit messages (for example, `feat: ...`, `fix: ...`, or `docs: ...`). Commit only your own changes; do not include unrelated user changes. Keep AI authorship disclosure in the README, not in commit messages.

## Document ownership

- AGENTS.md: durable development rules, not a task journal.
- README.md: purpose, setup, configuration, and usage.
- PLAN.md: milestones, acceptance criteria, and completion status.
- HANDOFF.md: concise current state, latest verification, blockers, and the next actionable step. Replace stale state instead of appending a running history. Use Git for history; do not duplicate it here or include the hash of the commit containing the handoff itself.

## Checks

Install the locked environment with `uv sync --locked`. Run offline tests with `uv run --locked python -m unittest discover -s tests -v` and check whitespace with `git diff --check`. GitHub-hosted CI runs these tests on Python 3.12 and 3.14. Validate deployment edits with `bash -n scripts/deploy.sh`, actionlint v1.7.7 (custom runner labels are in .github/actionlint.yaml), and `CONTROL_GID=999 MCWL_IMAGE=mcwl-tg-manager:test BOT_ENV_FILE=/dev/null docker compose -f deploy/compose.yml config --quiet`. Build the image after Dockerfile changes when Docker is available. See docs/DEPLOYMENT.md for deployment operations. Do not start the bot during verification without explicit authorization to contact Telegram. Documentation-only changes require link/content checks and `git diff --check`; application tests are unnecessary unless behavior changes.

## Implementation boundaries

- Never commit credentials, Telegram tokens, RCON passwords, or real deployment secrets.
- Require TELEGRAM_ALLOWED_CHAT_IDS and silently ignore messages from other chats, including private chats. Apply equivalent access control before enabling new update types. Future privileged commands also require explicit user authorization and must deny access by default.
- Expose only the intended whitelist operations and fixed start/stop operations for mc; do not add arbitrary remote console execution, user-supplied Docker arguments, or a host Docker socket mount in the bot. Host lifecycle operations belong in the restricted helper service.
- Do not push, deploy, or contact live Telegram/Minecraft services unless requested.
