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

## 0.3. Server lifecycle commands — complete; host setup pending

Scope: add /server_start and /server_stop for the existing Docker container named mc. Require an allowed administrator chat; all its participants are authorized. Use an asynchronous client for a restricted host helper with fixed Docker lifecycle operations; never accept container names or arbitrary commands from Telegram.

Acceptance: offline tests cover allowed/denied/anonymous senders, malformed commands, successful/idempotent start/stop, missing container, API errors, connection failure, timeout, and concurrent requests. Stop grants a 120-second graceful shutdown window. Deployment passes allowed chat IDs and the restricted control socket group, documents host-helper setup and the socket privilege boundary, and does not operate a real Minecraft container during verification.

## 0.4. Chat-only authorization and setup recovery — complete

Scope: treat every allowed chat as a trusted administrator chat. Remove per-user configuration and checks, including anonymous sender restrictions. Keep silent rejection outside the chat allowlist. Document recovery when helper files were created under the runner account but installation runs under another account.

Acceptance: lifecycle commands work for different members and anonymous senders in allowed chats, disallowed chats never reach the helper, configuration/deployment no longer requires per-user IDs, and setup recovery uses absolute source paths with sudo.

## 0.5. Help and Telegram command menu — complete

Scope: replace the placeholder with Russian /help instructions; /start opens the same help. Register help/start/server_start/server_stop commands with Russian descriptions for each allowed chat during polling startup. Keep source documentation in English, with an explicit exception for requested Russian help/menu text. Explain the missing mc container and one-time creation from the existing Minecraft Compose directory.

Acceptance: help/start routes work in allowed private/group chats and stay silent elsewhere. Startup registers chat-scoped menus, and a Telegram API failure for one menu does not disable polling or remaining menus. Tests mock all Telegram calls; no live Minecraft container is created or changed.

## 0.6. Minecraft readiness notification — complete; host-helper upgrade pending

Scope: after /server_start, asynchronously wait up to five minutes for the Paper Done marker from the current container run, then notify the requesting chat in Russian. Extend the restricted host helper with a read-only wait_ready operation; do not expose Docker or raw logs to the bot.

Acceptance: ignore previous runs using Docker StartedAt, pin container ID/start time and reject restart/replacement/exit during waiting, bound CLI/client/wait timeouts, keep stop available during loading, scan logs without buffering full history, and cover success/failure/concurrency with offline tests. Document the required manual host-helper update before redeploying the bot.

## 0.7. Concise help and Russian stop replies — complete

Scope: remove start from help and slash suggestions while keeping it as an unadvertised help alias. Reduce help to the three visible commands. Translate stop progress, success, already-stopped, failure, and command usage messages in the bot without requiring a host-helper update.

Acceptance: the registered menu contains only help/server_start/server_stop, help contains no start alias or deployment details, and stop replies are Russian for normal, idempotent, and error paths. Existing chat authorization and readiness behavior remain covered.

## 0.8. Whitelist management — complete; host-helper upgrade pending

Scope: add /wl_list, /wl_add <name>, and /wl_remove <name> for every member of allowed chats. Extend the restricted helper with only these validated operations through docker exec mc rcon-cli whitelist. Keep RCON credentials in Minecraft, validate ASCII player names at both trust boundaries, and require a running server. Show concise Russian replies/help/menu entries and split long lists for Telegram.

Acceptance: offline tests cover routing, chat authorization, malformed names and injection attempts, exact fixed Docker arguments, list/empty list, add/remove/idempotent responses, stopped server, busy helper, RCON errors and unexpected responses, protocol validation, and long lists. Do not infer command success from CLI exit status alone. Document the manual host-helper update and existing RCON requirement without adding secrets or publishing ports.

## 1. Configuration — partially complete

- [x] Load and validate the Telegram token from the process environment.
- [x] Load and validate allowed chat IDs; enforce the allowlist before message handlers run.
- [x] Authorize server lifecycle commands by trusted administrator chat membership.
- [x] Reuse Minecraft's existing RCON configuration through its packaged CLI; no bot-side RCON secrets are required.
- Validate required values and fail with actionable errors without revealing secrets.
- Provide a placeholder-only .env.example and configuration documentation.

Acceptance: valid configuration loads; missing or invalid values fail clearly; authorization lists cannot silently enable public access. Configuration validation has automated tests.

## 2. RCON integration — complete through the restricted host helper

- [x] Invoke the packaged rcon-cli inside mc with bounded timeouts and fixed arguments.
- [x] Support whitelist add, remove, and list through a narrow interface.
- [x] Validate player names before constructing commands at both trust boundaries.

Acceptance: tests cover command construction, invalid names, authentication failure, connection failure, and timeouts without requiring a live server. No arbitrary command interface is exposed to Telegram users.

## 3. Telegram commands and authorization — complete

- [x] Add /help, /wl_add, /wl_remove, and /wl_list.
- Support commands addressed to the bot in group chats.
- Restrict commands to configured trusted administrator chats; do not add per-user restrictions without a new request.
- Return readable validation and service error messages without leaking secrets.

Acceptance: tests cover allowed and denied requests, malformed commands, and RCON failures. Denied requests never reach RCON. Bot startup and shutdown are documented.

## 4. Docker deployment — complete through the restricted helper

- [x] Add a bot image and standalone Compose deployment.
- [x] Reach Minecraft through the host helper and packaged CLI without a shared bot/Minecraft network or published RCON port.
- Document credentials, startup, logs, and offline-mode limitations.

Acceptance: image build and Compose validation pass where Docker is available. Live verification is performed only when requested and configured; unavailable checks are explicitly recorded.

## 5. Automated checks and VM delivery — complete; production verified by user

Implemented scope: add hosted CI and a main-only Docker deployment job on a Linux self-hosted runner labeled mcwl-production. Provide manual Ubuntu setup, GitHub secret/variable placement, first-deploy, troubleshooting, and rollback instructions. Do not configure GitHub or contact the VM automatically.

Acceptance: offline tests and workflow lint pass; Docker configuration validates; image build is checked if a daemon is available. Deploy requires successful CI for the same commit, never runs for PRs, serializes production changes, validates runtime configuration before replacing the service, and keeps secrets outside checkout/images. Document live checks that remain manual.


- [x] Add hosted CI for automated tests, workflow lint, and deployment syntax checks.
- [x] Provide GitHub Actions configuration and a manual Linux runner/Docker setup guide.
- [x] User: provision the runner, configure GitHub settings, push main, and verify live deployment.
- [x] Inject the Telegram token from GitHub secrets into a private runtime environment file outside checkout/images.
- [x] Serialize deployment and replace the prior Compose container.
- [x] Document local/CI commands, first deployment, logs, and manual rollback.

Acceptance: CI runs without Telegram or Minecraft credentials and checks the same behavior as local tests.
