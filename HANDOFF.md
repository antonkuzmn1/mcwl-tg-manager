# Handoff

## Current state

- The bot supports /help, its hidden /start alias, /server_start, /server_stop, /wl_list, /wl_add <name>, and /wl_remove <name>. Help/menu list six commands and remain concise. Telegram-facing help, readiness, stop, usage, and whitelist strings are Russian in messages.py; other project content is English.
- Every participant of an allowed administrator chat is authorized, including anonymous senders. Other chats are silently ignored. No per-user ID list is used.
- Whitelist commands pass only validated names and fixed list/add/remove operations through the restricted local Unix socket. The host executes docker exec mc rcon-cli whitelist inside the existing container. Minecraft's RCON credentials stay there; no bot-side RCON password, published port, or additional data mount is needed.
- Minecraft must be running. Whitelist operations share the lifecycle lock with start/stop, use bounded timeouts, and parse standard Vanilla/Paper replies instead of trusting the CLI exit code. Idempotent operations have explicit statuses. Unknown/truncated responses do not claim success; raw RCON diagnostics never go to Telegram. Long player lists use a larger bounded protocol frame and split into messages of at most 4000 characters.
- Names accept 1–16 ASCII letters, digits, and underscores at both trust boundaries, preserving request case. Standard server canonical names may be returned. Short names support offline-mode servers; native Minecraft commands handle profiles/UUIDs and persistence.
- Lifecycle/readiness behavior remains: wait up to five minutes for the current run's Done marker; check ID/StartedAt; allow stop while loading; reject readiness after stop/restart. No raw Docker socket is mounted into the bot.
- GitHub CI/CD and existing configuration remain unchanged. Root-owned helper upgrades are manual. docs/DEPLOYMENT.md has a whitelist upgrade procedure; README.md covers commands, native RCON behavior, and offline-mode limitations.

## Latest verification

- 62 offline tests passed on Python 3.14.6 locally and Python 3.12.16 inside a network-disabled Linux container.
- Coverage includes exact Docker/RCON arguments, native response parsing, empty/long lists, mutation/idempotent replies, invalid/injected names, chat permissions, anonymous senders, helper contention, stopped containers, RCON errors, malformed protocol replies, and existing lifecycle/readiness behavior.
- Docker image built successfully. actionlint, Bash syntax, Compose configuration, local Markdown links, language rules, and git diff --check passed.
- All Docker/RCON operations in tests are mocked. No actual whitelist was changed, no Telegram calls were sent, no VM was contacted, and no GitHub settings were changed.

## Deployment requirements and limitations

- Install the updated deploy/server_control.py as /opt/mcwl-control/server_control.py and restart mcwl-control before deploying this bot version. The unit, secrets, and Compose settings do not change. An older helper rejects whitelist operations safely.
- On the VM, a running mc container must support its packaged rcon-cli and existing RCON configuration. Verify with the read-only command sudo docker exec mc rcon-cli whitelist list. The helper assumes the previously configured rootful Docker and github-runner service account.
- Standard English Vanilla/Paper command responses are supported; plugins/custom translations can require parser adjustments. A timeout may leave an operation's final state uncertain; check /wl_list before retrying mutations.
- Whitelist operations require a running server and do not edit files while it is stopped. Avoid a conflicting startup WHITELIST source that overwrites runtime edits unless intended.
- Offline mode does not authenticate nickname ownership; use the correct nickname/case. The bot relies on the server's identity handling rather than calculating UUIDs.

## Next step

User updates the host helper using the whitelist upgrade section in docs/DEPLOYMENT.md, deploys the bot, and verifies list/add/remove with an intended test player. Existing server control/readiness was already verified by the user. Do not access the VM, change the whitelist, or push code without a new request.
