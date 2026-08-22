---
name: frontend-design
description: Create or improve production web UI for this app, including dashboards, admin screens, React components, styling passes, responsive layout, and frontend polish.
---

# Frontend Design

Use this skill when the task asks for UI design, component work, page creation, responsive layout, or visual refinement.

## Required Context

1. Read `MEMORY.md`.
2. Read `docs/architecture/ARCHITECTURE.md` when present.
3. Read `docs/architecture/AI_WORKFLOWS.md` when present and follow its Frontend Design Workflow.
4. Inspect the relevant frontend source files before choosing a design direction.

## Working Rules

- Build the usable screen or component first.
- Keep internal operations UI efficient, readable, responsive, and secure.
- Use existing project components, icons, styling conventions, routing, and state patterns where practical.
- Include realistic loading, empty, error, disabled, and success states when the screen needs them.
- Protect `.env`, `confidential/`, secrets, credentials, and server-only files.
- Verify with `npm run build` and targeted smoke checks when practical.

## Output

Report changed files, validation results, and any residual risk.
