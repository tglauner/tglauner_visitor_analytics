# Visitor Analytics Project Memory

## Durable context

- TGIR application developed on macOS in Dropbox and deployed to one DigitalOcean droplet.
- FastAPI receives public tracking events; a static JavaScript dashboard reads reporting APIs.
- SQLite remains appropriate at current scale and initializes idempotently at collector startup.
- Production lives under `/var/www/html/visitor_analytics`, behind Apache, with Uvicorn on port 9000.
- Root `confidential/`, `.env`, databases, GeoIP data, and generated status files never enter git.

## Security boundary

- `/collect` and `/healthz` are public.
- `/api/metrics/*` uses HTTP Basic when `ADMIN_AUTH_ENABLED=true`.
- Local development defaults to auth disabled. Production must enable it with non-default credentials.

## Commands

```bash
make setup
make test
make dev
make smoke
```

## Module decisions

- Configuration: `collector/config.py`
- SQLite lifecycle/schema: `collector/database.py`
- Request models: `collector/schemas.py`
- Host, payload, and range validation: `collector/domain.py`
- Existing endpoint paths and SQLite tables remain backward compatible.
- The visible dashboard is intentionally limited to portfolio totals, tracked-site widgets, and Top Pages; site and page drill-down modals remain available.
- Udemy CSV upload/import is intentionally unavailable; historical order data remains read-only for retained revenue metrics.
- The dashboard now starts with a local Agent Status operations panel. Agent registration and last-known state are tracked in `collector/config/agent_registry.json` and `collector/config/agent_status.json`.
- Agent lifecycle events use administrator-protected `/api/agents/*` routes. `working`, `success`, and `failure` are stored; success derives to `needs_work` after 60 minutes without a worker.
- The initial agent registry is a one-time seed of visible first-level TGIR Projects folders. UI deletions remain deleted, and the status-slide script reports lifecycle events best-effort to the local API.
- The Quant tracker was deployed to `quant.tglauner.com` on 2026-09-02 at commit `bab2470`. It uses `appId=quant`, loads the shared tracker globally, sends local debug traffic to `127.0.0.1:9000/collect`, and sends production traffic to `https://tglauner.com/collect`. The deployment workflow preserves secrets while enforcing `FLASK_DEBUG=0` on the droplet.

- Course sites and the homepage require analytics consent via `tgAnalyticsConfig.requireConsent=true`; the shared cookie manager publishes `tg:analytics-consent`. Denial prevents IDs, queueing, and sends; revocation clears queued events and analytics cookies. Other apps preserve their existing behavior. Boolean flags accept true/1/"true"/"1" explicitly; "false" stays disabled.

- October 2026 release: all four paid Udemy codes are `25OFF_TG_OCT_2026` at USD 149.99; FREE code remains `FREE_TG_OCT_2026`. VaR page lives in the homepage repository. Shared tracker supports optional consent gating on all course pages without changing other app defaults.
- Canonical coupon and analytics skill instructions now live in sibling `cross_project_tools/skills/`; the helper lives in `landing_page_tglauner.com/scripts/`. Runtime agent registry/status JSON files are host-local, ignored, and preserved during deployment.
- Local binary Python wheels must match the running Mac architecture. The old environment is preserved as `.venv.pre-coupon-release`; the active `.venv` passes the backend suite. Tests mock dotenv loading and never read the real `.env`.
- Production releases must preserve `.env`, data, geo files, and agent runtime JSON; the deployment script now excludes all `.venv*` environments and both Git directory/file metadata.
