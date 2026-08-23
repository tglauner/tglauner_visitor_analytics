# Visitor Analytics Architecture

## Purpose

Provide low-cost, first-party analytics for TGIR sites without an external analytics platform.

## Runtime

```text
tracked sites -> POST /collect -> FastAPI -> SQLite
administrator -> /visitor_log/ -> /api/metrics/* -> SQLite
```

- Frontend: static HTML, CSS, and JavaScript in `visitor_log/`
- Backend: FastAPI/Uvicorn in `collector/`
- Database: SQLite with WAL, initialized idempotently at startup
- Production: one DigitalOcean droplet, Apache HTTPS reverse proxy, systemd service
- Storage: `/var/www/html/visitor_analytics`; no worker or managed database

## Module boundaries

- `app.py`: HTTP routes and metric queries
- `config.py`: environment contract
- `database.py`: connection and idempotent schema initialization
- `domain.py`: boundary validation and normalization
- `schemas.py`: request models
- `reporting_filters.py`: reloadable reporting exclusions

## Security

- Origin validation limits event collection to configured domains.
- Collection and health checks remain public.
- Reporting routes require HTTP Basic when enabled.
- Production must set `ADMIN_AUTH_ENABLED=true` with strong credentials in `.env`.
- Secrets, databases, GeoIP data, status artifacts, and `confidential/` stay out of git.

## Reliability

- Startup schema creation is idempotent.
- Event batches use one locked bulk insert.
- Reporting filters reload after file changes without restarting the service.

## Validation

```bash
make test
.venv/bin/python -m compileall -q collector tests
make dev
make smoke
```
