# GitHub Actions and VM deployment

## Design and assumptions

These instructions assume a private repository, an Ubuntu 24.04/22.04 VM (or a compatible Debian system), systemd, SSH key access, and an administrator with sudo. The repository is https://github.com/antonkuzmn1/mcwl-tg-manager. Replace example hostnames and local SSH key paths with your own values.

The workflow in `.github/workflows/pipeline.yml` runs offline tests on GitHub-hosted Ubuntu with Python 3.12 and 3.14 for pull requests, pushes to main, and manual runs. Only a push/manual run on main can deploy, and both test jobs must pass first. The deploy job runs on the VM, builds a local Docker image tagged with the tested commit, and replaces the bot through Compose. There is no container registry or SSH connection from GitHub.

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

## 6. Add secrets and variables

Preferred location: **Repository Settings → Environments → production**.

| Type | Name | Value |
| --- | --- | --- |
| Environment secret | `TELEGRAM_BOT_TOKEN` | The complete bot token issued by BotFather |
| Environment variable | `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated numeric chat IDs, such as `-1001234567890,-987654321` |

Use **Add environment secret** for the token and the **Environment variables** section for the chat list. Enter values without surrounding quotes. The chat list is configuration, not a credential.

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

This liveness check does not prove Telegram authentication or connectivity: polling can retry a network failure while the process stays up. Check `/start` manually in an allowed chat and verify it stays silent in a disallowed one. Disable any pre-existing webhook and stop any old bot process using the same token before the first deployment.

## 8. Inspect, restart, or stop the bot

SSH as your administrator and switch to the runner account:

```sh
sudo -iu github-runner
cd ~/apps/mcwl-tg-manager
export MCWL_IMAGE="$(cat current-image)"
export BOT_ENV_FILE="$PWD/bot.env"
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
docker compose -f previous-compose.yml up -d --wait --wait-timeout 60
cp previous-compose.yml compose.yml
cp previous-bot.env bot.env
cp previous-compose.yml current-compose.yml
cp previous-bot.env current-bot.env
cp previous-image current-image
flock -u 9
```

These files exist only after a successful deployment has been replaced or a later deployment has been attempted. On a failed first deployment there is no previous version: fix configuration/code and rerun. Review logs and test `/start` after rollback. If the previous token has been revoked, supply its replacement via GitHub and redeploy instead.

After a rollback, a new push/manual run on main deploys main again. Revert the problematic code in Git before deploying it again. Do not prune the images named by `current-image` or `previous-image`. Docker build cache and unused images need periodic disk maintenance; this workflow deliberately does not run broad prune commands on a VM that may host Minecraft.

## Troubleshooting

- **Deploy job stays queued:** runner must be online with `self-hosted`, `Linux`, and `mcwl-production` labels; check environment approval and branch restrictions too.
- **Runner is offline:** open a root shell with `sudo -i`, enter the runner install directory, and check `./svc.sh status` and outbound connectivity. Runner diagnostics are in its `_diag` directory.
- **Docker permission denied:** check runner group membership and restart the runner service after changing it.
- **Empty configuration:** confirm exact secret/variable names, the production scope, and that values are not surrounded by quotes. A variable accidentally saved as a secret is not available through `vars`.
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
