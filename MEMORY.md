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
