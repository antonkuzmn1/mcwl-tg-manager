# GitHub Actions and VM deployment

## Design and assumptions

These instructions assume a private repository, an Ubuntu 24.04/22.04 VM (or a compatible Debian system), systemd, SSH key access, and an administrator with sudo. The repository is https://github.com/antonkuzmn1/mcwl-tg-manager. Replace example hostnames and local SSH key paths with your own values.

The workflow in `.github/workflows/pipeline.yml` runs offline tests on GitHub-hosted Ubuntu with Python 3.12 and 3.14 for pull requests, pushes to main, and manual runs. Only a push/manual run on main can deploy, and both test jobs must pass first. The deploy job runs on the VM, builds a local Docker image tagged with the tested commit, updates the host helper, and replaces the bot through Compose. There is no container registry or SSH connection from GitHub.

The runner initiates outbound HTTPS connections to GitHub. Keep SSH key authentication for your own administration; do not upload your private SSH key to GitHub. The bot also needs outbound HTTPS access to Telegram. The runner, bot, and Docker image downloads require DNS and outbound access; no extra inbound ports are required.

A persistent runner can execute repository code with access to this machine. The runner's Docker-group membership grants effectively root-level access. Use a private repository with trusted contributors and protected main; never route untrusted PR jobs to this runner. A dedicated deployment VM is preferable to a machine holding unrelated sensitive workloads. An `if` condition in the checked-in workflow is not isolation from a malicious change to another workflow.

## 1. Prepare GitHub before registering the runner

1. Make sure the repository is private and only trusted users have write access.
2. Open **Settings → Actions → General** and enable the actions used here. Under workflow permissions, select **Read repository contents and packages permissions**. The workflow explicitly requests only `contents: read`.
3. Open **Settings → Environments → New environment** and create `production`.
4. Restrict its deployment branches to `main`. If your plan supports required reviewers, you can enable one to require a confirmation before each deployment. For a solo repository, do not prevent self-review unless another reviewer is available.
5. Protect `main` with a ruleset/branch protection where your GitHub plan supports it. Require the `Test (Python 3.12)` and `Test (Python 3.14)` checks after they first appear. Review workflow/deployment-script changes carefully.

Environment availability and protection features depend on repository visibility and your GitHub plan. If private-repository environment secrets are unavailable, use repository-level secrets and variables at the paths in step 6; the expressions in the workflow are unchanged. Do not make a repository public just to unlock environment features for a persistent production runner. If environments themselves are unavailable on your plan, remove the workflow's `environment: production` line and rely on protected main/manual workflow runs; environment-level protections then do not apply.

## 2. Connect to the VM and install prerequisites

Run on your own computer:

```sh
ssh -i ~/.ssh/YOUR_VM_KEY YOUR_ADMIN_USER@YOUR_VM_IP
```

On the VM, using the existing administrator account:

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3 util-linux
```

Install Docker Engine and the Docker Compose plugin using the official instructions for your OS. If Docker is already running Minecraft, verify it and skip installation; do not replace an existing installation blindly.

- Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Debian: https://docs.docker.com/engine/install/debian/

Verify and enable Docker at boot:

```sh
docker --version
sudo docker version
sudo docker compose version
sudo systemctl enable --now docker
```

Compose must be **2.30.0 or newer**, because the deployment uses raw environment files. Modern Compose v5 also supports this. Do not use the old `docker-compose` binary.

## 3. Create a dedicated runner account

As the VM administrator:

```sh
sudo adduser --disabled-password --gecos '' github-runner
sudo usermod -aG docker github-runner
sudo install -d -o github-runner -g github-runner -m 700 /home/github-runner/actions-runner
sudo -iu github-runner
```

Do not add this account to sudoers. It still has broad host access through Docker, as explained above. It does not need its own SSH key or password: use the administrator account for SSH and `sudo -iu github-runner` locally.

As `github-runner`:

```sh
id
docker version
docker compose version
cd /home/github-runner/actions-runner
```

`docker version` must show both client and server without sudo. If access is denied, leave and reopen the runner login shell after group membership changes.

## 4. Register the GitHub runner

In the repository, open **Settings → Actions → Runners → New self-hosted runner**.

1. Select **Linux** and your VM architecture. `uname -m` returns `x86_64` for x64 and `aarch64` for ARM64.
2. In the runner login shell in `/home/github-runner/actions-runner`, run the download, checksum verification, and extraction commands shown by GitHub. Use the current commands from that page rather than copying an old runner version.
3. Run the generated `./config.sh --url ... --token ...` command as `github-runner`, not root. The registration token is short-lived (normally one hour). It is not a bot token or a deployment secret; do not commit it or add it to Actions secrets. If expired, generate a new one.
4. Set the runner name to `mcwl-production-1`.
5. Keep the default labels (`self-hosted`, `Linux`, architecture) and add the custom label **`mcwl-production`**. The workflow requires this exact custom label.
6. Keep the work folder `_work`. Do not start `./run.sh` as a second runner process.

If dependency installation is requested, return to the administrator shell and run `/home/github-runner/actions-runner/bin/installdependencies.sh` with sudo, then repeat configuration as the runner user.

## 5. Install the runner as a service

Exit the runner login shell to return to your existing administrator shell:

```sh
exit
sudo -i
cd /home/github-runner/actions-runner
./svc.sh install github-runner
./svc.sh start
./svc.sh status
exit
```

The service must run as `github-runner`, not root. GitHub should now show the runner as **Idle**. It starts automatically after reboot; do not leave an SSH terminal running `./run.sh`.

If you changed Docker group membership after starting the service, restart it:

```sh
sudo -i
cd /home/github-runner/actions-runner
./svc.sh stop
./svc.sh start
exit
```

## 5a. Install the restricted server control helper

Complete this step before deploying this version. The bot must not receive the host Docker API socket. Instead, it connects to a narrow Unix-socket helper whose only operations are start, stop, read-only readiness checks, and validated whitelist operations for the existing container `mc`. The helper uses the existing runner account's Docker access; its Python script and systemd unit are installed as root-owned files. No new TCP port is opened.

From the local project root on your own computer, upload the two setup files using your existing SSH key:

```sh
ssh -i ~/.ssh/YOUR_VM_KEY YOUR_ADMIN_USER@YOUR_VM_IP 'mkdir -p ~/mcwl-control-setup'
scp -i ~/.ssh/YOUR_VM_KEY deploy/server_control.py deploy/mcwl-control.service YOUR_ADMIN_USER@YOUR_VM_IP:mcwl-control-setup/
```

On the VM, as your administrator:

```sh
getent group mcwl-control >/dev/null || sudo groupadd --system mcwl-control
sudo install -d -o root -g root -m 755 /opt/mcwl-control
sudo install -o root -g root -m 755 ~/mcwl-control-setup/server_control.py /opt/mcwl-control/server_control.py
sudo install -o root -g root -m 644 ~/mcwl-control-setup/mcwl-control.service /etc/systemd/system/mcwl-control.service
sudo systemctl daemon-reload
sudo systemctl enable --now mcwl-control
sudo systemctl status mcwl-control --no-pager
sudo stat -c '%a %U %G' /var/lib/mcwl-control/control.sock
```

If you created the files manually as `github-runner` in `~/apps/mcwl-tg-manager`, they are in `/home/github-runner/apps/mcwl-tg-manager`, not in the administrator's home directory. `mkdir -p ~/mcwl-control-setup` does not move files into that directory, and `~` changes when switching accounts. As the administrator, use the actual absolute source paths:

```sh
sudo ls -l /home/github-runner/apps/mcwl-tg-manager/server_control.py /home/github-runner/apps/mcwl-tg-manager/mcwl-control.service
sudo install -d -o root -g root -m 755 /opt/mcwl-control
sudo install -o root -g root -m 755 /home/github-runner/apps/mcwl-tg-manager/server_control.py /opt/mcwl-control/server_control.py
sudo install -o root -g root -m 644 /home/github-runner/apps/mcwl-tg-manager/mcwl-control.service /etc/systemd/system/mcwl-control.service
sudo systemctl daemon-reload
sudo systemctl enable --now mcwl-control
sudo systemctl status mcwl-control --no-pager
sudo stat -c '%a %U %G' /var/lib/mcwl-control/control.sock
```

Ensure the `mcwl-control` group exists using the command in the main installation block. Run installation commands one line at a time and resolve any error before proceeding. If the first `ls` cannot find a file, locate it before attempting installation. A shell warning about returning to a nonexistent directory after `exit` is separate from the missing installation sources; run `cd ~` to reset the administrator's current directory.

The socket should be mode `660` with group `mcwl-control`. The state directory should be mode `750`. It persists across service restarts and reboots, so the bot's directory bind mount remains valid when the helper replaces its socket. The bot remains non-root; Compose adds this group as a supplementary group using `CONTROL_GID`, which the deploy script detects from the directory. Do not change socket permissions to `666` and do not mount `/var/run/docker.sock` into the bot.

The helper expects `/usr/bin/docker` and the normal rootful socket `/var/run/docker.sock`. A rootless Docker installation or a different Docker binary/socket path requires an explicit operator-reviewed helper adjustment. Python 3.10+ is sufficient for the host helper; it uses only the standard library. No bot token is supplied to it.

Make sure the Minecraft container exists on this same VM as `mc`. From its existing Compose directory, create it once if needed:

```sh
docker compose up -d mc
```

Do not run that command in the bot deployment directory. The helper cannot create or remove containers; `docker compose down` removes `mc` and requires manual creation again. The bot can start it after a normal stop. Add `stop_grace_period: 120s` to the Minecraft service if you also want a longer shutdown grace period for manual Compose stops; the helper passes its own 120-second Docker timeout.

After deployment, try `/server_start` or `/server_stop` in an allowed chat. The bot reports loading first and sends a Russian ready notification only after the current run emits its Paper Done marker. Readiness waits up to five minutes, checks for stop/restart, and leaves /server_stop available during loading. Stop allows graceful shutdown for up to 120 seconds, after which Docker can force termination. Only one operation runs at a time; after a timeout the daemon may still finish the operation, so inspect state before trying again.

After the one-time automation setup below, deployments update the helper automatically. Changes to the systemd unit or privileged updater still require administrator installation. Deployments do not restart Minecraft. Inspect helper logs privately using `sudo journalctl -u mcwl-control -n 100 --no-pager`.

## 5b. Enable automatic helper updates (one-time setup)

Existing installations must complete this step before the next deployment. On your computer, from the project root, upload the updater and sudo rule using your existing SSH key (replace the key path and VM address):

```sh
ssh -i ~/.ssh/YOUR_VM_KEY anton@YOUR_VM_IP 'mkdir -p /home/anton/mcwl-control-setup'
scp -i ~/.ssh/YOUR_VM_KEY deploy/update_control.py deploy/mcwl-control.sudoers anton@YOUR_VM_IP:/home/anton/mcwl-control-setup/
```

On the VM, as `anton`:

```sh
sudo install -d -o root -g root -m 755 /opt/mcwl-control
sudo install -o root -g root -m 755 /home/anton/mcwl-control-setup/update_control.py /opt/mcwl-control/update_control.py
sudo visudo -cf /home/anton/mcwl-control-setup/mcwl-control.sudoers
sudo install -o root -g root -m 440 /home/anton/mcwl-control-setup/mcwl-control.sudoers /etc/sudoers.d/mcwl-control
sudo visudo -c
sudo -u github-runner sudo -n -l
```

The final listing should include `/opt/mcwl-control/update_control.py` with no arguments. The helper and unit from step 5a must already exist. No new GitHub secrets or variables are required. Push main from your computer or rerun the main workflow after this setup.

The root-owned updater runs isolated system Python (`-I`), accepts bounded Python source on stdin, checks syntax without executing it as root, and atomically replaces only `/opt/mcwl-control/server_control.py`. It restarts only `mcwl-control.service`, which still runs as `github-runner`, and waits for an active service and connectable control socket. The sudo rule grants this exact no-argument command, not general installation or systemctl access. The runner can now deploy helper code with the helper service account's existing Docker privileges; protect main and production deployment access accordingly. The bot still receives only the restricted socket.

Unchanged source is checked for readiness without a restart. Failed restart/readiness restores the prior source and attempts to restart it; the deployment fails before replacing the bot. Recovery failure also fails the job and requires operator intervention. Updates interrupt pending helper requests, so deploy when no server operation is in progress. A later bot deployment failure leaves the successfully updated helper in place; use the paired manual rollback below if needed. The updater's final error is intentionally generic: inspect `sudo journalctl -u mcwl-control -n 100 --no-pager` and `sudo systemctl status mcwl-control --no-pager`.

The updater and sudo rule are not self-updated by CI. Future changes to those files or the systemd unit require repeating the relevant administrator installation steps.

## Updating the helper for readiness notifications

With automatic updates enabled in step 5b, CI installs the required helper before the bot. The following is the manual alternative for installations without automation. Existing installations must update `server_control.py` before deploying the bot with readiness support. The bot calls the new read-only `wait_ready` operation; an older helper only understands start/stop. No new secrets or systemd unit changes are required.

On your local computer, from the project root:

```sh
scp -i ~/.ssh/YOUR_VM_KEY deploy/server_control.py YOUR_ADMIN_USER@YOUR_VM_IP:server_control.py
```

On the VM, as that same administrator account (for the current installation, `anton`):

```sh
sudo install -o root -g root -m 755 "$HOME/server_control.py" /opt/mcwl-control/server_control.py
sudo systemctl restart mcwl-control
sudo systemctl status mcwl-control --no-pager
```

Then push the bot update or run the normal main deployment workflow. In an allowed chat, send `/server_start`. The bot sends a Russian loading message followed by a ready message once the current run's Done marker is found. If mc is already running, it checks that run's logs and confirms readiness without restarting the server. Test `/server_stop` during loading only when stopping the server is acceptable; the pending readiness request should report that it stopped instead of sending a ready notification.

The helper reads only mc's logs since Docker StartedAt, checks container identity/start time around each read, and does not return logs to Telegram. The maximum readiness wait is five minutes with three-second polling; a stop or restart cancels confirmation. Startup logs must remain available. A timeout does not stop Minecraft, which may still finish loading later. This notification confirms the Paper startup marker, not external connectivity, and is triggered only by /server_start. Pending notifications are not persisted if the bot/helper restarts.

## Updating the helper for whitelist commands

With step 5b enabled, CI performs this update automatically. The commands below remain a manual alternative.

Install the updated `deploy/server_control.py` before deploying the bot that adds /wl_list, /wl_add, and /wl_remove. The systemd unit, bot secrets, and Compose mounts do not change. On your local computer, from the project root:

```sh
scp -i ~/.ssh/YOUR_VM_KEY deploy/server_control.py YOUR_ADMIN_USER@YOUR_VM_IP:server_control.py
```

On the VM, as that same administrator account:

```sh
sudo install -o root -g root -m 755 "$HOME/server_control.py" /opt/mcwl-control/server_control.py
sudo systemctl restart mcwl-control
sudo systemctl status mcwl-control --no-pager
```

Ensure Minecraft is running and verify its existing RCON setup with this read-only command:

```sh
sudo docker exec mc rcon-cli whitelist list
```

RCON is enabled by default in the image and uses its existing configuration. If it has been disabled, enable it in the original Minecraft Compose configuration before using whitelist commands. Do not publish port 25575 or add RCON credentials to the bot/GitHub for this implementation. The helper accesses the packaged CLI inside mc and never returns passwords or raw diagnostic output.

Deploy the bot normally, then test `/wl_list`, `/wl_add YourPlayerName`, and `/wl_remove YourPlayerName` in the allowed administrator chat. Use an intended test player: add/remove modify the actual whitelist. A stopped server must produce a request to start it rather than a success reply. An old helper rejects the new operations until updated; if the server is still loading or RCON fails, the bot reports a failure without claiming the change succeeded.

Only whitelist list/add/remove are exposed; there is no arbitrary exec/RCON interface. Names are validated in both bot/client and helper, and mutations use the native Minecraft whitelist commands. Repeated add/remove operations get explicit already-listed/not-listed responses. Unknown or plugin-modified response text is rejected; check `/wl_list` before retrying an uncertain mutation. Long lists are split into Telegram-sized messages. With offline mode, nickname ownership is not authenticated; preserve the intended spelling/case and test with the actual client.

## 6. Add secrets and variables

Preferred location: **Repository Settings → Environments → production**.

| Type | Name | Value |
| --- | --- | --- |
| Environment secret | `TELEGRAM_BOT_TOKEN` | The complete bot token issued by BotFather |
| Environment variable | `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated numeric chat IDs, such as `-1001234567890,-987654321` |

Use **Add environment secret** for the token and the **Environment variables** section for the chat list. Enter values without surrounding quotes. The chat list is configuration, not a credential. Allowed chats are dedicated administrator chats: every participant can start or stop the server, and no per-user setting or Telegram administrator-role lookup is used. Remove any obsolete per-user variable left from earlier versions; it is no longer consumed.

Fallback for plans without environment secrets: **Settings → Secrets and variables → Actions → Secrets → New repository secret** for the token, and the **Variables → New repository variable** tab for the chat list. Avoid duplicate values at different scopes to prevent confusion; environment values take precedence when present.

No `SSH_PRIVATE_KEY`, VM password, `SSH_HOST`, Docker registry password, or PAT is needed. The runner registration handles GitHub connectivity; the workflow's built-in `GITHUB_TOKEN` checks out the repository. The image is built on the VM.

During deployment, only the deploy step receives the token. Runtime configuration is written to `/home/github-runner/apps/mcwl-tg-manager/bot.env`, outside the runner checkout, with directory mode 700 and file mode 600. The token is not baked into the image. Docker administrators can still read container environment variables, and successful/previous configuration backups also contain the token. This is the intended trust boundary; GitHub secret masking does not encrypt data on the VM.

## 7. Push and deploy

From your local project, inspect the changes and push main when ready:

```sh
git push origin main
```

The agent has only created a local commit; it has not pushed or changed your GitHub settings.

Open **Actions → CI/CD**. The two test jobs run first, followed by **Deploy production** on your runner. If environment approval is enabled, approve the pending deployment.

For a manual redeployment, use **Actions → CI/CD → Run workflow → main**. Manual runs on other branches test but do not deploy. Rotating the bot token or changing chat IDs in GitHub requires a new deployment/manual run; a plain container restart does not fetch new GitHub values.

The deploy script validates settings in an isolated container before stopping the current bot. It writes the runtime file, saves the last successful image/configuration for rollback, runs Compose, and checks that the process stays running without restarts for ten seconds. Deployments are serialized. Compose stops the old container before starting the replacement, so there is brief downtime but no intentional overlap of two polling processes.

This liveness check does not prove Telegram authentication or connectivity: polling can retry a network failure while the process stays up. Check `/help` (or `/start`) manually in an allowed chat and verify it stays silent in a disallowed one. Disable any pre-existing webhook and stop any old bot process using the same token before the first deployment.

## 8. Inspect, restart, or stop the bot

SSH as your administrator and switch to the runner account:

```sh
sudo -iu github-runner
cd ~/apps/mcwl-tg-manager
export MCWL_IMAGE="$(cat current-image)"
export BOT_ENV_FILE="$PWD/bot.env"
export CONTROL_GID="$(stat -c '%g' /var/lib/mcwl-control)"
docker compose -f compose.yml ps
docker compose -f compose.yml logs --tail=100 bot
```

Do not print `bot.env` or run `docker compose config` without `--quiet` in logs you share: rendered configuration can expose secrets.

Restart or stop:

```sh
docker compose -f compose.yml restart bot
# Or stop until the next explicit startup/deployment:
docker compose -f compose.yml stop bot
```

Docker's `unless-stopped` policy restarts the bot after a reboot unless you explicitly stopped it. The runner service is separate from the bot container; stopping the runner does not stop the bot.

## 9. Roll back manually

If a deploy fails after replacing the old container, it is not rolled back automatically. The workflow fails and preserves the previous successful deployment files. To restore them, first ensure no deployment is currently running and disable automatic deployments temporarily if necessary. Run as `github-runner`:

```sh
cd ~/apps/mcwl-tg-manager
exec 9>deploy.lock
flock -w 120 9
export MCWL_IMAGE="$(cat previous-image)"
export BOT_ENV_FILE="$PWD/previous-bot.env"
export CONTROL_GID="$(stat -c '%g' /var/lib/mcwl-control)"
if [ -f previous-helper.py ]; then
  sudo -n /opt/mcwl-control/update_control.py < previous-helper.py
fi
docker compose -f previous-compose.yml up -d --wait --wait-timeout 60
cp previous-compose.yml compose.yml
cp previous-bot.env bot.env
cp previous-compose.yml current-compose.yml
cp previous-bot.env current-bot.env
cp previous-image current-image
if [ -f previous-helper.py ]; then
  cp previous-helper.py current-helper.py
fi
flock -u 9
```

Helper snapshots are recorded by automated deployments as current-helper.py and previous-helper.py. The first deployment after enabling automation cannot snapshot the helper from an earlier manual deployment: if a paired rollback needs that older helper, recover deploy/server_control.py from the matching Git revision and submit it through the installed updater before restoring the bot. Unit/updater changes require separate administrator rollback.

These files exist only after a successful deployment has been replaced or a later deployment has been attempted. On a failed first deployment there is no previous version: fix configuration/code and rerun. Review logs and test `/start` after rollback. If the previous token has been revoked, supply its replacement via GitHub and redeploy instead.

After a rollback, a new push/manual run on main deploys main again. Revert the problematic code in Git before deploying it again. Do not prune the images named by `current-image` or `previous-image`. Docker build cache and unused images need periodic disk maintenance; this workflow deliberately does not run broad prune commands on a VM that may host Minecraft.

## Help and command suggestions

The bot registers help/server_start/server_stop/wl_list/wl_add/wl_remove with Russian descriptions for every allowed chat when polling starts. `/help` shows a concise six-line Russian command list; `/start` remains a hidden alias and is omitted from help and slash suggestions. After deploying, type `/` in an allowed chat; reopen the chat if suggestions have not refreshed. If no menu appears, check bot logs for `Could not register command menu`, confirm the bot belongs to the allowed chat, and restart after fixing access. The commands still work when typed manually if menu registration failed. There is no need to configure BotFather for the automatic menu; existing more-specific language/member menus set externally can take precedence and must be removed or updated separately.

The repository remains English except for the user-requested Russian help, menu, readiness, stop, and usage strings in `src/mcwl_tg_manager/messages.py`.

If `/server_start` reports a Docker failure and `sudo docker ps -a --filter 'name=^/mc$'` returns no container, the host helper has nothing to start. Its systemd service can be healthy while mc does not exist. In the original Minecraft Compose directory, run `sudo docker compose up -d mc` once, then inspect `sudo docker logs --tail=100 mc`. Use the Minecraft Compose file, not the bot deployment file. Preserve the existing `./data` directory and its Compose-relative location to keep using the intended world. This creates and starts mc; `/server_start` may then report that it is already running. The bot intentionally cannot create or remove containers.

## Troubleshooting

- **Deploy job stays queued:** runner must be online with `self-hosted`, `Linux`, and `mcwl-production` labels; check environment approval and branch restrictions too.
- **Runner is offline:** open a root shell with `sudo -i`, enter the runner install directory, and check `./svc.sh status` and outbound connectivity. Runner diagnostics are in its `_diag` directory.
- **Docker permission denied:** check runner group membership and restart the runner service after changing it.
- **Empty configuration:** confirm exact secret/variable names, the production scope, and that values are not surrounded by quotes. A variable accidentally saved as a secret is not available through `vars`.
- **Server control unavailable:** install/start `mcwl-control`, check its socket directory group and permissions, and confirm container `mc` exists. Every member of an allowed chat can control the server, including anonymous senders. If the bot is silent, confirm the chat is in TELEGRAM_ALLOWED_CHAT_IDS and redeploy after changing it.
- **Token invalid or bot silent:** inspect logs privately, check BotFather credentials and Telegram connectivity, and make sure the bot is present in the allowed chat. Numeric IDs must match the current chat ID; migrating to a supergroup can change it.
- **Telegram conflict:** another polling process or webhook is active for the same bot. Stop the duplicate or disable the webhook.
- **CI succeeded but deployment failed:** open the deploy job, then inspect the service over SSH. Successful tests do not configure the runner, Docker, or secrets for you.

## References

- GitHub runner setup: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- GitHub runner service: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application
- GitHub environments and plan limitations: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- GitHub workflow security: https://docs.github.com/en/actions/reference/security/secure-use
- Docker group privileges: https://docs.docker.com/engine/install/linux-postinstall/
- Compose raw environment files: https://docs.docker.com/reference/compose-file/services/#env_file
