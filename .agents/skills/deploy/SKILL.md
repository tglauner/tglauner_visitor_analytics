---
name: deploy
description: Prepare safe deployment steps, validation commands, restart commands, rollback notes, and rollout guidance for the current project's documented target.
---

# Deploy

Use this skill when the task asks for deployment help, rollout notes, restart commands, production smoke checks, or rollback planning.

## Required Context

1. Read `MEMORY.md`.
2. Read `docs/architecture/ARCHITECTURE.md` and deployment/runbook docs when present.
3. Inspect current infra samples, service files, Apache config, and build commands.

## Required Output

1. Exact pre-deploy validation commands.
2. Exact build, sync, restart, and health-check commands.
3. Config and secret handling notes.
4. Rollback steps that restore the previous working state.

## Guardrails

- Prefer single-host, low-cost deployment patterns unless the repo clearly needs more.
- Keep commands copy-ready and native to the detected local platform: POSIX on
  macOS and PowerShell on Windows.
- Keep production secrets in the deployment environment's `.env` or approved
  secret store.
- Never print secrets.
