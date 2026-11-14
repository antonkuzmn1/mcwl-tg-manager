# Development plan

This is the proposed roadmap, not authorization to implement all milestones. Implement one user-requested task at a time. Update the affected milestone and its acceptance criteria when scope changes.

## 0. Project foundation — complete

- [x] Create a Python package with an executable entry point.
- [x] Document local startup and AI authorship.
- [x] Establish agent instructions, a development plan, and a handoff document.
- [x] Require English project content and automatic Conventional Commits.

Acceptance: the skeleton starts locally, documentation describes its limitations, and the working process is recorded in the repository.

## 0.1. Async Telegram starter — complete

Scope: implement an asynchronous aiogram bot with only /start and an English placeholder response. Read TELEGRAM_BOT_TOKEN from the process environment; do not add deployment infrastructure yet.

Acceptance: /start responds in private and group chats, unrelated messages and commands are ignored, missing or malformed tokens fail without exposing secrets, and the HTTP session closes on shutdown or polling failure. Tests use mocks and do not contact Telegram. Document future runtime secret injection and single-instance VM deployment.

## 0.2. Allowed chats — complete

Scope: require TELEGRAM_ALLOWED_CHAT_IDS as a comma-separated list of signed Telegram chat IDs. Apply the restriction to all message handlers, including /start.

Acceptance: configured private, group, and supergroup chats receive replies; other chats are silently ignored before handlers run. Missing, empty, malformed, zero, or out-of-range IDs prevent startup. Whitespace and duplicate IDs are supported. Tests run without Telegram access.

## 1. Configuration — partially complete

- [x] Load and validate the Telegram token from the process environment.
- [x] Load and validate allowed chat IDs; enforce the allowlist before message handlers run.
- [ ] Add allowed user IDs and RCON connection settings when implementing privileged commands.
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

## 5. Automated checks and VM delivery — planned

- Add CI for the automated tests and selected code-quality checks.
- Agree on GitHub Actions, secret storage, and VM deployment details before implementation.
- Inject the Telegram token into the runtime environment; do not embed secrets in source or images.
- Run only one polling instance per token and stop the previous instance before replacement.
- Document the commands used locally and in CI.

Acceptance: CI runs without Telegram or Minecraft credentials and checks the same behavior as local tests.
