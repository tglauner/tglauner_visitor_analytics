# GitHub Copilot Project Adapter

- Read and follow the root `AGENTS.md`; it is the shared project contract for
  Codex and GitHub Copilot.
- Read root `MEMORY.md` before material work and update it only with durable,
  non-secret context.
- Detect the operating system before choosing commands. On Windows, use
  PowerShell-native commands and Windows paths. On macOS or Linux, use POSIX
  shell commands and paths.
- For Python on Windows, use `.venv\Scripts\python.exe` when the environment
  exists and `py -3` to create it. On macOS or Linux, use `.venv/bin/python`
  when it exists and `python3` to create it. The environment directory is
  always `.venv/`.
- Read matching workflows under `docs/agent-workflows/` and matching skills
  under `.agents/skills/` before performing specialized work.
- `.codex/` contains Codex-only configuration and hooks. Do not run or rewrite
  Codex status hooks from GitHub Copilot unless the user explicitly requests
  work on that integration.
- Never read `.env`, `confidential/`, keys, credential files, or secret files
  unless the user explicitly authorizes that exact access.
- Preserve existing project changes, run the narrowest relevant validation,
  and report changed files, validation results, and rollback steps.

## Status Slide Workflow (Copilot)

GitHub Copilot does not have automatic hooks. Run status commands manually:

1. **At the start of material work** (not quick questions), run:
   ```bash
   python3 scripts/status_slide.py start
   ```

2. **Before your final response**, run:
   ```bash
   python3 scripts/status_slide.py finish --status success --bullet "First outcome" --bullet "Second outcome" --bullet "Third outcome"
   ```
   Use `--status issue` if work is blocked or incomplete.

The finish command sends a Telegram notification if configured. Use `--no-notify`
to skip notification for a single run.
