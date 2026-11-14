# Handoff

## Current state

- The asynchronous bot supports /help, its /start alias, and /server_start plus /server_stop for the existing Docker container mc. The placeholder is removed. Help is a three-line Russian list of help/server_start/server_stop; start remains an unadvertised alias and is absent from slash suggestions. Stop progress/success/already-stopped/failure and usage replies are also Russian; other repository content remains English.
- At polling startup, chat-scoped Telegram menus are registered for every allowed chat. API failures are logged and do not block polling or registration for remaining chats. Tests mock all Telegram calls.
- Authorization is chat-only: every participant of a configured trusted administrator chat can use lifecycle commands, including anonymous senders. Per-user configuration and checks have been removed by explicit user request. Disallowed chats are silently ignored. Commands accept no container names or arguments.
- ServerController uses a restricted Unix socket, not the host Docker API. The host helper exposes start/stop and a read-only wait_ready operation, invokes fixed Docker arguments without a shell, checks container state, serializes lifecycle operations, and gives stop a 120-second graceful timeout. It never creates/removes containers or runs arbitrary console commands.
- After /server_start the bot asynchronously waits up to five minutes for the current run's Paper Done marker, then sends a Russian ready notification in the requesting chat. The helper streams only logs since Docker StartedAt and verifies ID/start time around each read. Exit, restart, or timeout prevents confirmation; stop stays available while loading. Raw logs never go to Telegram.
- deploy/server_control.py and deploy/mcwl-control.service must be manually installed as root-owned files on the VM. The helper runs as the existing github-runner account with Docker access and a dedicated mcwl-control group. Its persistent state directory is mounted read-only into the non-root bot; Compose adds the detected control socket group. No host Docker socket is mounted into the bot.
- GitHub-hosted CI runs tests on Python 3.12/3.14. Main deployments pass only the required token/chat configuration into the runtime file and detect CONTROL_GID from /var/lib/mcwl-control. The helper must be installed before deploying this version. Root-owned host helper updates remain manual.
- docs/DEPLOYMENT.md section 5a covers helper installation through existing SSH key access. Section 5a also explains recovery when files were saved in the runner home but installed from another account; it supplies absolute source paths. Section 6 lists only token/chat configuration. README.md describes the commands, permissions, limitations, and the optional Minecraft stop_grace_period setting.
- RCON and whitelist management are not implemented. Project content remains English except for requested Russian text in messages.py; completed changes use Conventional Commits.

## Latest verification

- 42 offline tests passed on local Python 3.14.6 after shortening help, removing start from the menu, and translating stop replies. Coverage includes the exact three-command menu, short help, localized stop results, and existing readiness/authorization behavior.
- The prior readiness implementation passed 41 tests on Python 3.12.16 inside the Docker image. This text/menu update was verified locally; no new image build was required. Docker processes are mocked; no real server actions are performed.
- actionlint v1.7.7, Bash syntax, Compose configuration, local Markdown links, English content outside the explicit messages.py exception, and git diff --check were checked.
- No real Minecraft container was started/stopped, no Telegram requests were sent, and no VM or GitHub settings were changed. Actual systemd service installation, socket permissions on the production host, and live server control remain manual verification steps.

## Deployment requirements and limitations

- User must install the host helper first and redeploy. Only existing token/chat configuration is required; any obsolete per-user GitHub variable can be removed.
- Helper assumes rootful Docker at /var/run/docker.sock, /usr/bin/docker, a github-runner account, and systemd. It uses Python 3.10+ standard library only. It does not need the bot token.
- Container mc must already exist on the same VM; create it once from the Minecraft Compose directory. docker compose down removes it and cannot be repaired by /server_start.
- The final ready notification confirms the Paper Done marker for the observed run, not external network access. Notifications are request-bound and are not persisted across bot/helper restarts. Current-run startup logs must be retained to confirm readiness. Stop can be forced by Docker after 120 seconds. After a timeout the daemon may still complete an operation.
- The helper retains the existing Docker privilege boundary on the host while exposing only mc lifecycle operations to the bot. Its files must stay root-owned; do not expose the raw Docker socket to the bot.
- Deployment liveness does not verify Telegram or Minecraft connectivity. Host-helper changes need manual installation/restart, not just a bot deployment.

## Next step

User has verified start readiness notifications and stop in production. Deploy this bot-only text/menu update normally; no host-helper/service/secret changes are needed. Reopen the Telegram chat if its command menu is cached. Do not access the VM, operate Minecraft, or push code without a new request.
