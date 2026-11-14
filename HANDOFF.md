# Handoff

## Current state

- The asynchronous aiogram bot responds only to /start in configured chats. No RCON or privileged whitelist operations exist.
- TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS are required environment variables. Runtime configuration validation and chat access middleware are covered by offline tests.
- .github/workflows/pipeline.yml runs hosted tests on Python 3.12/3.14, workflow lint, and deployment syntax checks. Main pushes/manual runs deploy only after tests pass, using a Linux self-hosted runner labeled mcwl-production and the production environment.
- The deploy job builds a commit-tagged local Docker image, validates settings without network access, writes private runtime configuration outside checkout, and replaces the Compose bot container. It checks process liveness and retains the last successful deployment for manual rollback. Deployments are serialized; failed deployments are not automatically rolled back.
- Actions are pinned by commit and Docker base images by digest. The bot container runs as a non-root user with a read-only root filesystem and no published ports.
- docs/DEPLOYMENT.md contains the manual SSH, Docker, runner-service, GitHub secrets/variables, logs, troubleshooting, and rollback procedure. README.md links to it.
- All repository content is English. Completed agent changes use Conventional Commits.

## Latest verification

- 13 offline tests passed on local Python 3.14.6 and on Python 3.12.16 inside the image with networking disabled. Deployment-flow tests use fake Docker/flock/sleep commands, not a live host deployment.
- Docker image build succeeded. Runtime configuration loaded in a network-disabled, read-only container as its default non-root user.
- actionlint v1.7.7 passed with the custom runner label configuration.
- Bash syntax, Docker Compose configuration, local Markdown links, English-only source/documentation content, and git diff --check passed.
- No real Telegram token was used. No GitHub settings were changed, no code was pushed, and no VM was contacted. The actual GitHub-hosted workflow, runner service, and production deployment remain unverified until manual setup.

## Open questions and blockers

- User must confirm the VM OS/architecture and provision Docker plus the runner. The guide assumes private-repository Ubuntu/systemd with SSH key access and administrator sudo.
- GitHub environment secrets/protection features depend on the plan; the guide describes repository-level fallback and removal of the environment line if environments are unavailable.
- The runner Docker account has broad host privileges; only trusted workflows/contributors should have access. Do not enable untrusted PRs on the production runner.
- User must set the production TELEGRAM_BOT_TOKEN secret and TELEGRAM_ALLOWED_CHAT_IDS variable, push main, and verify /start manually. Runtime/backed-up secrets are private files on the VM and remain readable to Docker administrators.
- Docker process liveness does not establish successful Telegram connectivity. A pre-existing webhook or duplicate polling process must be removed before production startup.
- Minecraft network integration, RCON, and user-level whitelist authorization remain future work.

## Next step

User follows docs/DEPLOYMENT.md manually and reports the first workflow/deployment result. Do not access their VM, push code, or change GitHub settings without a new request.
