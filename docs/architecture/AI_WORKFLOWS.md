# AI Workflow Architecture

## Purpose

Keep reusable, app-specific AI workflows in the application architecture so Codex works from the same product and delivery standards across independent sessions.

An application workflow is the source of truth for recurring work such as frontend design, release checks, data imports, or admin hardening. Codex-specific files such as `AGENTS.md`, `docs/agent-workflows/CODEX_WORKFLOWS.md`, and `.agents/skills/*/SKILL.md` should be thin adapters that point back to this document.

## Target placement

Copy this file to the target repo as:

```text
docs/architecture/AI_WORKFLOWS.md
```

For a new Course Operations Portal target repo, use this shape:

```text
course-operations/
|-- AGENTS.md
|-- MEMORY.md
|-- docs/
|   |-- agent-workflows/
|   |   `-- CODEX_WORKFLOWS.md
|   `-- architecture/
|       |-- ARCHITECTURE.md
|       |-- IMPLEMENTATION_PLAN.md
|       `-- AI_WORKFLOWS.md
|-- .agents/
|   `-- skills/
|       |-- deploy/
|       |   `-- SKILL.md
|       |-- frontend-design/
|       |   `-- SKILL.md
|       `-- security-review/
|           `-- SKILL.md
`-- confidential/
```

## Agent boundaries

- `AI_WORKFLOWS.md` defines what good work means for this application.
- `AGENTS.md` tells Codex how to behave in the repo and when to read this workflow file.
- `docs/agent-workflows/CODEX_WORKFLOWS.md` gives Codex reusable task procedures for fixes, review, deployment, security review, and frontend work.
- `.agents/skills/*/SKILL.md` makes selected workflows invokable as Codex skills.

## Frontend Design Workflow

Use this workflow when creating or improving web UI, including dashboards, admin screens, landing pages, React components, CSS, layout polish, and responsive behavior.

### Inputs

- Read `MEMORY.md` for durable project context.
- Read `docs/architecture/ARCHITECTURE.md` for stack, deployment, data, and security constraints.
- Inspect the current frontend before choosing a visual direction.
- Identify the user, workflow goal, page density, required states, and deployment risk.

### Design rules

- Build the usable screen or component first, not a marketing explanation of it.
- Match the interface to the app's job. Internal tools should be quiet, fast to scan, and efficient for repeated use.
- Pick one deliberate visual direction that fits the domain, then carry it through typography, spacing, color, motion, and empty states.
- Use production components, real states, accessible labels, responsive layout, and working data paths.
- Prefer existing component, icon, router, state, and styling patterns from the target repo.
- Keep admin screens protected and avoid exposing local paths, `.env`, secrets, or `confidential/` content.

### Implementation steps

1. Read the app architecture, memory, and existing frontend files.
2. State the intended UI direction in one sentence before making broad visual changes.
3. Implement the smallest complete workflow that satisfies the request.
4. Add realistic loading, empty, error, disabled, and success states when the screen needs them.
5. Verify mobile and desktop layouts so text, buttons, controls, and panels do not overlap.
6. Run the local build and the most relevant backend or smoke checks.
7. Record durable UI decisions in `MEMORY.md` when they should survive future sessions.

## Codex Integration

Add this section to `AGENTS.md`:

```markdown
## Application workflow packs

- If `docs/agent-workflows/CODEX_WORKFLOWS.md` exists, read it before review, fix, deploy, security, or frontend workflow tasks.
- If `docs/architecture/AI_WORKFLOWS.md` exists, read it before frontend design, release, deployment, data import, admin, or security workflow tasks.
- If a matching `.agents/skills/*/SKILL.md` exists, use it for the task-specific workflow.
- Treat workflow files as task-specific guidance and this `AGENTS.md` file as Codex operating guidance.
- For frontend work, follow the Frontend Design Workflow and verify with `npm run build` plus targeted smoke checks.
```

Keep `docs/agent-workflows/CODEX_WORKFLOWS.md` as the readable Codex workflow guide, `.agents/skills/` as the skill trigger surface, and this file as the application-specific workflow guide.

## Local build and test

For the Course Operations Portal starter:

```bash
npm run build
pytest
curl http://127.0.0.1:8100/api/health
```

When running the app locally, use Vite for the frontend and FastAPI with Uvicorn for the backend. Keep `.env` local and do not commit it.

## DigitalOcean production

Production remains the normal application architecture:

- deploy under `/var/www/html/course-operations`
- serve HTTPS through Apache on the droplet
- run the FastAPI service through systemd
- keep production secrets in the droplet `.env`
- validate Apache and the app health endpoint before declaring the deployment done

Production validation:

```bash
sudo apachectl -t
systemctl status course-operations
curl -k https://courseops.example.com/api/health
```
