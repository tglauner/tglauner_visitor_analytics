# AGENTS.md — Shared Agent Project Standard

## Mission

Build and maintain a production-minded codebase with small diffs, explicit validation, and no secrets in git.

## Working rules

- Read the repo before making structural changes.
- Detect the operating system before choosing commands. Use POSIX commands and
  `python3` on macOS; use PowerShell commands and `py -3` on Windows. Use the
  project `.venv/` on every platform.
- When running under Codex, every user prompt must start a visible status
  lifecycle, including questions and read-only checks. The required
  `.codex/hooks.json` prompt-submit hook opens a dark Beamer slide in VS Code
  that says `Status: Working`. If the hook is unavailable, run this before
  handling the prompt:

  ```bash
  python3 scripts/status_slide.py start
  ```

  When running under Codex, after validation and before every final response,
  generate and open the final Beamer status PDF in VS Code:

  ```bash
  python3 scripts/status_slide.py finish --status success --bullet "..." --bullet "..." --bullet "..."
  ```

  Use `--status issue` instead of `success` when the work ends with a blocker,
  failed validation, or unresolved risk. Do not close the working slide as the
  normal workflow; replace it with Success or Issue at the end. The required
  turn-stop hook preserves an existing final slide. If Codex fails to create
  one, the hook replaces stale Working status with a fallback Issue slide.
- Prefer boring dependencies and existing local patterns.
- **Tooling Stack:** Maintained in Visual Studio Code (VS Code) using Codex & Copilot in-IDE, or Google Antigravity CLI in the macOS terminal when hitting IDE usage limits.
- **Model Selection:** Default to balanced, medium-cost models (`gpt-4o`).
- Keep edits scoped to the requested feature or bug.
- Add or update docs when behavior changes.
- **Storage Assumptions:** TGIR projects use local **Dropbox** paths; Teciem projects use local **SharePoint / OneDrive** paths.
- Keep a root `confidential/` directory for local-only private material and keep it out of git.
- Do not read `.env`, `confidential/`, secret files, or credential exports unless the task explicitly requires it and the human approves.


## Project memory

- Treat root `MEMORY.md` as durable cross-session memory.
- Read it at the start of any material task.
- Update it before finishing when the work creates durable decisions, commands, risks, or recurring gotchas.
- Compress it periodically so it stays short and useful.
- Never store secrets, tokens, or raw logs in `MEMORY.md`.

## Project architecture

- Read `docs/architecture/ARCHITECTURE.md` before choosing the stack,
  authentication model, storage, or deployment target.
- Treat that file as the project-specific source of truth.
- If it is missing, ask for the minimum missing deployment context instead of
  assuming a public cloud target.

## Application workflow packs

- If `docs/agent-workflows/CODEX_WORKFLOWS.md` exists, read it before review, fix, deploy, security, or frontend workflow tasks.
- If `docs/architecture/AI_WORKFLOWS.md` exists, read it before frontend design, release, deployment, data import, admin, or security workflow tasks.
- If a matching `.agents/skills/*/SKILL.md` exists, use it for the task-specific workflow.
- Treat workflow files as task-specific application guidance and this
  `AGENTS.md` file as shared agent operating guidance.
- For frontend work, follow the Frontend Design Workflow and verify with `npm run build` plus targeted smoke checks.

## Change expectations

- update existing files before inventing new abstractions
- write idempotent jobs and retry-safe scripts
- include smoke checks for critical paths
- use `.venv/` for Python environments

## Before finishing

- run the most relevant validation command
- when running under Codex, generate and open the final status Beamer slide
  with three brief bullets
- explain what changed
- note any blockers or limits

## Validation

- frontend: `npm run build`
- backend: `pytest`
- targeted smoke checks where tests do not exist
