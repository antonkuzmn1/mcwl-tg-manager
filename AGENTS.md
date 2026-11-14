# Project instructions

## Language

Use English for all project content, including code, comments, documentation, configuration descriptions, and user-facing messages. Do not use Russian in project files.

## Project context

This project will manage a Minecraft server whitelist from Telegram through RCON. Only the Python skeleton exists today. Read README.md for setup, PLAN.md for milestones, and HANDOFF.md for current state before starting work.

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

The current skeleton can be checked with `PYTHONPATH=src python3 -m mcwl_tg_manager` and `git diff --check`. There is no automated test suite or CI yet. Document new test commands here when they become available. Documentation-only changes require link/content checks and `git diff --check`; application tests are unnecessary unless behavior changes.

## Implementation boundaries

- Never commit credentials, Telegram tokens, RCON passwords, or real deployment secrets.
- Keep Telegram authorization explicit and deny access by default when implementing commands.
- Expose only the intended whitelist operations; do not add arbitrary remote console execution.
- Do not push, deploy, or contact live Telegram/Minecraft services unless requested.
