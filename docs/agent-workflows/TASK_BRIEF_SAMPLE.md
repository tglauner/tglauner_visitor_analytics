# Task Brief Sample for Codex

## Goal

Add a launch-readiness dashboard to the course operations app so an admin can see coupon status, publish status, and unresolved blockers on one page.

## Constraints

- keep the existing React and FastAPI stack
- do not add a new paid vendor
- keep the deployment target documented in `docs/architecture/ARCHITECTURE.md`
- do not read or expose secrets

## Required output

- backend endpoint for dashboard data
- frontend page or route that renders the dashboard
- minimal tests or smoke checks
- docs update for any new env vars or deploy steps

## Validation

- `npm run build`
- `pytest`
- explain the exact route added and how to verify it manually

## Notes for the agent

- start by locating the current launch and coupon data sources
- prefer extending an existing admin page if one exists
- keep naming and folder structure aligned with the repo
- follow matching `.agents/skills/*/SKILL.md`, `docs/agent-workflows/CODEX_WORKFLOWS.md`, and `docs/architecture/AI_WORKFLOWS.md` if those files exist
