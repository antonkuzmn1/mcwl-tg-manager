#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${MCWL_IMAGE:?MCWL_IMAGE must identify the built image}"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN must be supplied}"
: "${TELEGRAM_ALLOWED_CHAT_IDS:?TELEGRAM_ALLOWED_CHAT_IDS must be supplied}"

# A dedicated path outside the runner checkout survives subsequent checkout jobs.
deploy_root="$HOME/apps/mcwl-tg-manager"
mkdir -p "$deploy_root"
chmod 700 "$deploy_root"
exec 9>"$deploy_root/deploy.lock"
flock -w 120 9

# Validate without starting polling or stopping the existing container.
docker run --rm --network none \
  --env TELEGRAM_BOT_TOKEN --env TELEGRAM_ALLOWED_CHAT_IDS \
  "$MCWL_IMAGE" /app/.venv/bin/python -c \
  'from mcwl_tg_manager.config import Settings; Settings.from_env()'

python3 scripts/write_runtime_env.py "$deploy_root/bot.env.next"
export BOT_ENV_FILE="$deploy_root/bot.env.next"
docker compose -f deploy/compose.yml config --quiet

# Keep the last successful deployment for explicit manual rollback.
if [[ -f "$deploy_root/current-image" ]]; then
  cp "$deploy_root/current-image" "$deploy_root/previous-image"
  cp "$deploy_root/current-compose.yml" "$deploy_root/previous-compose.yml"
  cp "$deploy_root/current-bot.env" "$deploy_root/previous-bot.env"
fi
mv "$deploy_root/bot.env.next" "$deploy_root/bot.env"
install -m 600 deploy/compose.yml "$deploy_root/compose.yml"
export BOT_ENV_FILE="$deploy_root/bot.env"

# Compose stops the previous instance before replacing it; no second poller is started.
docker compose -f "$deploy_root/compose.yml" up -d --wait --wait-timeout 60
sleep 10
container_id="$(docker compose -f "$deploy_root/compose.yml" ps -q bot)"
if [[ -z "$container_id" ]] || \
   [[ "$(docker inspect --format '{{.State.Running}} {{.RestartCount}}' "$container_id")" != 'true 0' ]]; then
  echo 'Deployment failed its process-liveness check. Inspect the service over SSH and use the documented rollback.' >&2
  exit 1
fi
cp "$deploy_root/compose.yml" "$deploy_root/current-compose.yml"
cp "$deploy_root/bot.env" "$deploy_root/current-bot.env"
printf '%s\n' "$MCWL_IMAGE" > "$deploy_root/current-image"
echo 'Deployment completed. Verify /start in an allowed Telegram chat.'
