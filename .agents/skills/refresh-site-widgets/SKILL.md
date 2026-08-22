---
name: refresh-site-widgets
description: Refresh the dashboard's discovered site widgets from the DigitalOcean Apache configuration while preserving manually maintained widget URLs. Use when Apache sites or aliases change, or when asked to sync the site-widget inventory.
---

# Refresh Site Widgets

Use `scripts/update_site_widgets.py` from the repository root. The script reads only Apache `ServerName`, `ServerAlias`, and application `Alias` directives over SSH. It never changes the server.

## Workflow

1. Read `collector/config/site_widgets.json` without changing its `manual` array.
2. Preview drift:

   ```bash
   .venv/bin/python scripts/update_site_widgets.py --check
   ```

3. If the user authorized a refresh, update only `discovered`:

   ```bash
   .venv/bin/python scripts/update_site_widgets.py
   python3 -m json.tool collector/config/site_widgets.json >/dev/null
   git diff -- collector/config/site_widgets.json
   ```

4. Confirm the `manual` array is byte-for-byte equivalent as parsed JSON, run `make test`, and report added or removed discovered URLs.

## Boundaries

- Never edit, reorder, or delete `manual` entries during discovery.
- Ignore certificate challenges, dashboard paths, tracking assets, and system aliases.
- Discovery is read-only on DigitalOcean; deployment is a separate explicitly authorized action.
- Never read `.env`, credentials, private keys, or `confidential/`.
