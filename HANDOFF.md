# Handoff

## Current state

- The asynchronous bot supports /start and /server_start plus /server_stop for the existing Docker container mc.
- All messages require an allowed chat. Lifecycle commands also require a positive user ID in TELEGRAM_ADMIN_USER_IDS; missing/empty administrator IDs disable them. Anonymous/chat senders and bots are rejected. Commands accept no container names or arguments.
- ServerController uses a restricted Unix socket, not the host Docker API. The host helper exposes only two operations, invokes fixed Docker arguments without a shell, checks container state, serializes operations, and gives stop a 120-second graceful timeout. It never creates/removes containers or runs arbitrary console commands.
- deploy/server_control.py and deploy/mcwl-control.service must be manually installed as root-owned files on the VM. The helper runs as the existing github-runner account with Docker access and a dedicated mcwl-control group. Its persistent state directory is mounted read-only into the non-root bot; Compose adds the detected control socket group. No host Docker socket is mounted into the bot.
- GitHub-hosted CI runs tests on Python 3.12/3.14. Main deployments pass TELEGRAM_ADMIN_USER_IDS into the runtime file and detect CONTROL_GID from /var/lib/mcwl-control. The helper must be installed before deploying this version. Root-owned host helper updates remain manual.
- docs/DEPLOYMENT.md section 5a covers helper installation through existing SSH key access. Section 6 lists the new GitHub variable. README.md describes the commands, permissions, limitations, and the optional Minecraft stop_grace_period setting.
- RCON and whitelist management are not implemented. Project content remains English and completed changes use Conventional Commits.

## Latest verification

- 32 offline tests passed on local Python 3.14.6, covering configuration, authorization, command routing, client/helper Unix-socket communication, fixed Docker arguments, graceful timeout, idempotence, concurrent requests, missing containers, errors, and private runtime-file handling.
- The updated Docker image built successfully. All 32 offline tests also passed inside the Linux image on Python 3.12.16 with networking disabled. Tests mock Docker processes; no real server actions are performed.
- actionlint v1.7.7, Bash syntax, Compose configuration, local Markdown links, English-only content, and git diff --check were checked.
- No real Minecraft container was started/stopped, no Telegram requests were sent, and no VM or GitHub settings were changed. Actual systemd service installation, socket permissions on the production host, and live server control remain manual verification steps.

## Deployment requirements and limitations

- User must install the host helper first, configure TELEGRAM_ADMIN_USER_IDS as a GitHub production variable (or repository fallback), and redeploy. Existing token/chat configuration remains required.
- Helper assumes rootful Docker at /var/run/docker.sock, /usr/bin/docker, a github-runner account, and systemd. It uses Python 3.10+ standard library only. It does not need the bot token.
- Container mc must already exist on the same VM; create it once from the Minecraft Compose directory. docker compose down removes it and cannot be repaired by /server_start.
- Successful start indicates container startup, not Minecraft readiness. Stop can be forced by Docker after 120 seconds. After a timeout the daemon may still complete an operation.
- The helper retains the existing Docker privilege boundary on the host while exposing only mc lifecycle operations to the bot. Its files must stay root-owned; do not expose the raw Docker socket to the bot.
- Deployment liveness does not verify Telegram or Minecraft connectivity. Host-helper changes need manual installation/restart, not just a bot deployment.

## Next step

User installs the restricted helper following docs/DEPLOYMENT.md section 5a, adds administrator user IDs, and deploys to verify server commands. Do not access the VM, operate Minecraft, or push code without a new request.
