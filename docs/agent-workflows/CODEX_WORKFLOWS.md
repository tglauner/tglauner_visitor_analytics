# Shared Agent Workflow Guide

## Purpose

Use this file as the shared home for reusable project workflows. Its existing
filename remains stable for compatibility. Copy it into a target repo as:

```text
docs/agent-workflows/CODEX_WORKFLOWS.md
```

`AGENTS.md` remains the standing operating contract. This file holds
task-specific procedures that Codex or GitHub Copilot should read when the user
asks for matching work.

Repo-scoped skills in `.agents/skills/*/SKILL.md` are the invokable version of the most common workflows. Use a matching skill when one exists, and use this file as the broader reference.

## General Rules

- When running under Codex, the prompt-submit hook must generate and open the
  dark working status slide in VS Code for every prompt. If the hook is
  unavailable, run:

  ```bash
  python3 scripts/status_slide.py start
  ```

- When running under Codex, after validation and before every final response,
  replace it with a final success or issue slide:

  ```bash
  python3 scripts/status_slide.py finish --status success --bullet "..." --bullet "..." --bullet "..."
  ```

- When running under Codex, use `--status issue` when work is incomplete,
  blocked, or validation fails.
- Codex project hooks in `.codex/hooks.json` must call `status_slide.py hook-start`
  on prompt submit and `status_slide.py hook-finish` at turn stop. Run
  `finish` manually for accurate final bullets. If it is omitted, the stop
  hook creates a fallback Issue slide instead of leaving stale Working status.
- Keep status bullets brief and concrete so the slide can be read at a glance.
- The visible dark `Status: Working` slide means work is still in progress.
- Prefer small, readable diffs.
- Reuse existing patterns before inventing new abstractions.
- Keep comments sparse and only where they save real parsing time.
- Favor explicit error handling over clever compactness.
- Avoid unrelated refactors while addressing a concrete task.
- Keep request and response shapes explicit.
- Validate inputs close to the boundary.
- Return predictable error formats.
- Do not leak secrets, credentials, or internal-only paths in responses or logs.
- Document new env vars in `.env.example`.

## Fix Issue Workflow

Use when the user reports a concrete bug, broken behavior, failing validation, or narrow implementation gap.

1. Restate the issue in repo terms.
2. Read the smallest relevant set of files first.
3. Implement the narrowest change that fixes the problem.
4. Run the most relevant validation command available.
5. Summarize changed files, validation results, and any residual risk.

## Review Workflow

Use when the user asks for a review or when a final self-review is needed before handing off.

1. Inspect `git status --short` and the current diff.
2. Read nearby files that affect behavior.
3. Prioritize bugs, regressions, security risks, and missing validation.
4. Call out assumptions that need human confirmation.
5. If no findings are present, say that explicitly and note any testing gap.

## Architecture Adoption Workflow

Use when the user asks to initialize a project from the TGIR architecture
library, compare an existing project with a starter, adopt shared standards, or
refresh previously copied guidance.

1. Apply the target project's `AGENTS.md` and relevant `MEMORY.md` first. Treat
   the architecture library as reference material, not as a replacement for the
   target project's binding instructions.
2. Run `scripts/architecture_manager.py info` from the architecture library so
   the manager reports the current platform, agent hint, shell, library root,
   and target. On Windows, invoke it with
   `py -3 scripts\architecture_manager.py`.
3. Confirm the requested profile: `tgir-app`, `teciem-app`, `knowledge-base`,
   `lecture`, or `document`.
4. For an existing project, run the manager's `audit` command with `--target`
   before making changes. The audit is read-only and must not inspect protected
   paths.
5. Review `git status --short` in the target and preserve all pre-existing user
   changes.
6. Classify each relevant path as missing, identical, different and requiring a
   semantic merge, a symlink or type conflict requiring review, or not
   applicable to the target.
7. Never inspect or modify `.env`, `confidential/`, keys, credential files, or
   secret files. Do not follow symlinks discovered at expected starter paths.
8. Present a file-by-file adoption plan before changing an existing project.
9. After approval, use the manager's `apply` command without `--force` to add
   missing standard files. Merge differing files individually.
10. Never replace `AGENTS.md`, `MEMORY.md`, `.gitignore`, `.env.example`,
    `.codex/config.toml`, `.codex/hooks.json`, or
    `.github/copilot-instructions.md` wholesale in an existing project.
    Preserve project-specific scripts, architecture decisions, and working
    behavior.
11. Run the target project's narrowest relevant tests, inspect the final diff,
    and report changed files, validation results, residual risks, and rollback
    steps.

Do not run `init-private-github-repo.sh` as part of adoption. Repository creation
is a separate external action that requires an explicit user request.

## Deployment Workflow

Use when the user asks for deployment help, rollout notes, restart commands, or production validation.

1. Identify the relevant runtime, build, sync, restart, and health-check commands.
2. List exact pre-deploy validation commands.
3. Call out config files, secrets, and local-only material that must stay out of git.
4. Prefer single-host, low-cost deployment patterns unless the repo clearly needs more.
5. Keep commands copy-ready and native to the detected local platform:
   POSIX on macOS and PowerShell on Windows.
6. Provide rollback steps that restore the previous working state.
7. Never print secrets.

## Security Review Workflow

Use when the task touches credentials, admin surfaces, deployment configs, file-access boundaries, auth, or permission controls.

1. Check whether `.env`, `confidential/`, secrets folders, or credential exports are exposed.
2. Check whether logs or user-facing responses could leak secrets.
3. Check whether admin features are protected by authentication or strong shared secrets.
4. Check whether new shell commands or automation broaden risk unnecessarily.
5. Summarize concrete findings and the narrowest safe fix.

## Frontend Workflow

Use when creating or improving web UI, dashboards, admin screens, React components, CSS, responsive layout, or visual polish.

1. Read `docs/architecture/AI_WORKFLOWS.md` when present.
2. Read `MEMORY.md`, `docs/architecture/ARCHITECTURE.md`, and relevant frontend source files.
3. Inspect existing frontend patterns before choosing a design direction.
4. Build the usable screen or component first.
5. Keep internal operations UI efficient, readable, responsive, and secure.
6. Use current project components, icons, styling conventions, and routing where practical.
7. Protect `.env`, `confidential/`, secrets, credentials, and server-only files.
8. Verify with `npm run build` and targeted smoke checks when practical.

## Validation

- Run the narrowest relevant validation first.
- Prefer existing test commands and build checks.
- If no tests exist, provide an exact smoke-check command.
- Do not fix unrelated test failures unless they block the requested task.
- Record durable validation commands in `MEMORY.md` when they matter for future sessions.

## Status Slide Workflow

Use this workflow for every Codex prompt, including questions and read-only
checks. GitHub Copilot does not run the Codex status lifecycle. The slide lets
the user scan multiple Codex VS Code windows and see which agents are still
working, done, or stopped on an issue.

1. Confirm the prompt-submit hook opened the dark working slide. If it did not,
   run:

   ```bash
   python3 scripts/status_slide.py start
   ```

2. Do the requested work.
3. Run the relevant validation.
4. Before the final response, generate a final Beamer PDF and open it in VS Code:

   ```bash
   python3 scripts/status_slide.py finish \
     --status success \
     --bullet "Implemented requested workflow" \
     --bullet "Ran validation" \
     --bullet "Opened status slide"
   ```

5. If there is a blocker or failed check, use:

   ```bash
   python3 scripts/status_slide.py finish \
     --status issue \
     --bullet "Describe the blocker" \
     --bullet "Describe what was completed" \
     --bullet "Describe what needs attention"
   ```

The `start` command compiles and opens a dark grey/blue `Status: Working`
Beamer PDF in VS Code. The final `finish` command overwrites the same
`status/status_slide.pdf` with either Success or Issue, so the visible tab shows
the current state without relying on VS Code editor-closing automation. The
hook-aware commands also maintain `status/status_slide_state.json` for status
tracking. The turn-stop hook preserves a recorded Success/Issue slide and
creates a fallback Issue slide only when Codex ends the turn without recording
a final status.

If a stale status PDF ever needs manual cleanup, use:

```bash
python3 scripts/status_slide.py close
```
