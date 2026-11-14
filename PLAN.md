# Development plan

This is the proposed roadmap, not authorization to implement all milestones. Implement one user-requested task at a time. Update the affected milestone and its acceptance criteria when scope changes.

## 0. Project foundation — complete

- [x] Create a Python package with an executable entry point.
- [x] Document local startup and AI authorship.
- [x] Establish agent instructions, a development plan, and a handoff document.
- [x] Require English project content and automatic Conventional Commits.

Acceptance: the skeleton starts locally, documentation describes its limitations, and the working process is recorded in the repository.

## 1. Configuration — planned

- Load the Telegram token, allowed user IDs, allowed chat IDs, and RCON connection settings from environment variables.
- Validate required values and fail with actionable errors without revealing secrets.
- Provide a placeholder-only .env.example and configuration documentation.

Acceptance: valid configuration loads; missing or invalid values fail clearly; authorization lists cannot silently enable public access. Configuration validation has automated tests.

## 2. RCON integration — planned

- Add an RCON client with bounded connection and response timeouts.
- Support whitelist add, remove, and list through a narrow interface.
- Validate player names before constructing commands.

Acceptance: tests cover command construction, invalid names, authentication failure, connection failure, and timeouts without requiring a live server. No arbitrary command interface is exposed to Telegram users.

## 3. Telegram commands and authorization — planned

- Add /help, /wl_add, /wl_remove, and /wl_list.
- Support commands addressed to the bot in group chats.
- Restrict commands to configured user IDs and chat IDs; reject anonymous or unverifiable senders.
- Return readable validation and service error messages without leaking secrets.

Acceptance: tests cover allowed and denied requests, malformed commands, and RCON failures. Denied requests never reach RCON. Bot startup and shutdown are documented.

## 4. Docker deployment — planned

- Add a bot image and Compose integration alongside the existing Minecraft service.
- Connect to mc:25575 over the Compose network without publishing the RCON port.
- Document credentials, startup, logs, and offline-mode limitations.

Acceptance: image build and Compose validation pass where Docker is available. Live verification is performed only when requested and configured; unavailable checks are explicitly recorded.

## 5. Automated checks — planned

- Add CI for the automated tests and selected code-quality checks.
- Document the commands used locally and in CI.

Acceptance: CI runs without Telegram or Minecraft credentials and checks the same behavior as local tests.
