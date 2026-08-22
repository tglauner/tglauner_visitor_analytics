# Visitor Analytics Implementation Plan

## Completed foundation

- Adopt TGIR agent, memory, confidential-data, and workflow conventions.
- Separate configuration, persistence, schemas, and domain validation from routes.
- Initialize the SQLite schema safely at startup.
- Preserve existing collection, reporting, dashboard, and deployment contracts.
- Add optional authentication to reporting and import APIs.
- Cover critical behavior with more than 20 automated tests.

## Production rollout

1. Back up `data/analytics.sqlite3`.
2. Deploy through `make deploy-prod`.
3. Set `ADMIN_AUTH_ENABLED=true`, `ADMIN_USERNAME`, and a strong `ADMIN_PASSWORD` in the server `.env`.
4. Restart `visitor-collector` and verify `/healthz`, collection, and authenticated dashboard access.

## Later, only when justified

- Split metric SQL into repository modules if route growth continues.
- Add a Job table only when long-running or scheduled work is introduced.
- Move from SQLite only if measured contention or operational scale requires PostgreSQL.
