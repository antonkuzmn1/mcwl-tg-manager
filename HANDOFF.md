# Handoff

## Current state

- Async bot supports /help, hidden /start, server start/stop with readiness notification, and whitelist list/add/remove. Every member of configured administrator chats is authorized, including anonymous senders. Russian bot strings remain isolated in messages.py; other project content is English.
- Deployment validates bot configuration, then submits the tested deploy/server_control.py on stdin to sudo -n /opt/mcwl-control/update_control.py before replacing the bot. No new secrets or variables are required.
- The root-installed updater accepts no arguments, bounds and compiles input without executing it as root, atomically updates only the fixed helper file, and restarts only mcwl-control.service. It checks active service and socket connectivity, skips unchanged healthy source, and restores/restarts the prior helper after startup failure. The helper still runs as github-runner with existing Docker access; the bot receives only the restricted socket.
- The updater, sudo rule, and systemd unit remain administrator-managed. CI cannot self-update them through the updater. Main/production access authorizes helper code deployment with the runner's existing Docker privileges.
- Successful deploys save current-helper.py alongside bot snapshots; later deploys preserve previous-helper.py for paired manual rollback. A later bot failure does not roll back a successfully updated helper automatically. The first transition from manual deployment has no old helper snapshot; recover it from the matching Git revision when needed.

## Latest verification

- 74 offline tests passed on local Python 3.14 and network-disabled Linux Python 3.12. Tests mock service/Docker/RCON operations; updater tests never execute submitted source or contact real system services.
- Coverage includes bounded input, invalid syntax, unchanged-file health check, atomic file failure, restart and recovery failures, service/socket readiness, fixed command arguments, and aborting bot replacement when helper update fails, plus existing bot and host-helper tests.
- Bash syntax, actionlint, Compose configuration, sudoers syntax, Markdown links, and git diff --check passed. No image packaging changes were needed.
- No VM, live Telegram, or Minecraft access; no push or deployment performed.

## Next step

The user installs deploy/update_control.py and deploy/mcwl-control.sudoers once following docs/DEPLOYMENT.md step 5b, then pushes main or reruns its workflow. Existing host helper/service from step 5a must already be installed. Future helper source changes deploy automatically. Unit/updater changes still need administrator installation. Avoid deploying during a pending server operation because helper restart interrupts in-flight requests. Verify /help and /wl_list after deployment; whitelist mutations require an intended test player.
