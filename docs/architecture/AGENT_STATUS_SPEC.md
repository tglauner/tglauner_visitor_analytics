# Local Agent Status Dashboard Specification

## Goal

Add a local-first operations section at the top of the Visitor Analytics dashboard so one person can see whether registered project agents are working, succeeded, failed, or need more work. Agent registration and last-known state use small host-local JSON files that remain editable from the dashboard and are ignored by Git.

## Scope for the first version

- Run entirely through the existing FastAPI service and static dashboard.
- Preserve the existing local registry; a new installation starts empty and uses Add agent for registration.
- Let the administrator add, edit, and delete agents from the dashboard.
- Accept lifecycle messages from agents when work starts, succeeds, or fails.
- Change a success older than one hour to the derived `needs_work` display state.
- Poll from the browser so status changes appear without a page reload.
- Reuse the existing HTTP Basic administrator boundary. Local development continues to work without authentication when `ADMIN_AUTH_ENABLED=false`.

This version does not start, stop, schedule, or remotely control agents. It reports lifecycle state only.

## Components and data flow

```text
agent or status-slide hook
        |
        | POST /api/agents/{agent_id}/events
        v
FastAPI agent-status service
        |
        | atomic JSON writes
        v
agent_registry.json + agent_status.json
        |
        | GET /api/agents every 15 seconds
        v
dashboard agent cards
```

The server clock is authoritative. Clients do not provide the event timestamp used for status aging.

## Registration

The local runtime registry file is `collector/config/agent_registry.json`.

```json
{
  "version": 1,
  "agents": [
    {
      "id": "visitor-analytics",
      "name": "Visitor Analytics",
      "project_path": "www.tglauner.com/visitor_analytics"
    }
  ]
}
```

- `id` is a stable lowercase slug used by API clients. Editing the display name or project path does not change it.
- `name` is the human-readable card title.
- `project_path` is relative to the configured Projects root. Absolute paths and paths outside that root are rejected.
- A missing registry is treated as empty. Deleting an agent in the UI does not cause it to reappear on restart.
- UI changes write the same host-local JSON file. Registrations and runtime events stay out of GitHub.

## Runtime state

The local runtime state file is `collector/config/agent_status.json`.

```json
{
  "version": 1,
  "agents": {
    "visitor-analytics": {
      "status": "success",
      "job_id": "codex-turn-123",
      "message": "Dashboard agent section implemented",
      "updated_at": "2026-08-28T14:30:00+00:00"
    }
  }
}
```

Every update uses an atomic replace so an interrupted write cannot leave partial JSON. A missing state entry is valid and displays as `needs_work`.

This ignored file preserves local status without publishing runtime state. Lifecycle events must never trigger repository operations.

## Lifecycle event protocol

Agents send:

```http
POST /api/agents/{agent_id}/events
Content-Type: application/json
Authorization: Basic ...

{
  "status": "working",
  "job_id": "codex-turn-123",
  "message": "Implementing dashboard agent status"
}
```

Allowed event statuses are:

- `working`: sent as soon as the agent starts a task.
- `success`: sent only after requested work and relevant validation complete.
- `failure`: sent when the agent stops with a blocker, failed validation, or unresolved issue.

`job_id` and `message` are optional but recommended. If a current `working` state has a job ID, a completion event with a different job ID is rejected with HTTP 409. This prevents an older task from overwriting a newer task's status.

Successful responses return the newly computed agent representation. Unknown agent IDs return HTTP 404, invalid payloads return HTTP 422, and stale job completions return HTTP 409.

### Status-slide mapping

The existing status-slide states map to dashboard events as follows:

| Status slide | Dashboard event |
| --- | --- |
| `working` | `working` |
| `success` | `success` |
| `issue` | `failure` |

The status-slide script sends the dashboard event after writing its local state file. Notification is best-effort and must not prevent the slide from being generated when the dashboard is unavailable. The dashboard URL and agent ID may be overridden with `AGENT_DASHBOARD_URL` and `AGENT_DASHBOARD_ID`.

## Derived display state

The API returns both the stored event status and a derived display status:

| Stored status | Condition | Display status |
| --- | --- | --- |
| none | no event received | `needs_work` |
| `working` | any age | `working` |
| `success` | less than 60 minutes old | `success` |
| `success` | 60 minutes old or older | `needs_work` |
| `failure` | until the next lifecycle event | `failure` |

The one-hour rule is computed on every `GET /api/agents`; no background worker or timer is required.

## Dashboard behavior

- The Agent Operations section is the first section in `<main>`.
- Summary counts show Working, Success, Failure, and Needs work.
- Each card shows agent name, status, project path, latest message, and relative update time.
- A plus button opens the add form. Each card has labeled edit and delete buttons.
- Delete requires browser confirmation and removes the registration plus its stored state.
- The section displays loading, empty, API error, save-in-progress, and successful save states.
- The browser polls `GET /api/agents` every 15 seconds and refreshes it with the main Refresh button.

## API

All routes below use the existing administrator authentication dependency.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/agents` | List agents with derived display states and counts |
| `POST` | `/api/agents` | Register an agent |
| `PUT` | `/api/agents/{agent_id}` | Edit name and project path |
| `DELETE` | `/api/agents/{agent_id}` | Delete registration and state |
| `POST` | `/api/agents/{agent_id}/events` | Record working, success, or failure |

## Configuration and security

- `AGENT_REGISTRY_PATH` may override the registry JSON location.
- `AGENT_STATUS_PATH` may override the status JSON location.
- `AGENT_PROJECTS_ROOT` may override the Projects directory used to validate project paths.
- The API never returns absolute filesystem paths.
- Path traversal, absolute project paths, duplicate IDs, and duplicate project paths are rejected.
- Messages are length-limited and rendered through HTML escaping in the browser.
- Production must keep `ADMIN_AUTH_ENABLED=true`; the event endpoint is an administrator endpoint in this first version.

## Validation and acceptance criteria

1. Existing host-local registrations are preserved; a new installation starts with an empty registry.
2. Add, edit, and delete work from the dashboard and survive a server restart.
3. `working`, `success`, and `failure` events appear on the next poll.
4. A success exactly 60 minutes old displays as `needs_work`.
5. A stale completion cannot overwrite a newer job ID.
6. Invalid or escaping project paths are rejected.
7. Existing analytics sections and APIs continue to work.
8. Backend tests and a local browser smoke check pass.
