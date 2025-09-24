# tglauner_visitor_analytics
Analytics platform for all pages under www.tglauner.com domain. Creates a dashboard that allows me to see what's happening on my web site.

Here’s a **production-ready `README.md`** draft you can drop into your repo.
It documents **DigitalOcean + Apache deployment** and the exact **HTML modifications** needed for tracking across all course pages.

---

# Visitor Analytics Platform

This project provides a **self-hosted visitor analytics dashboard** for `tglauner.com` and its course landing pages.
It captures outbound clicks (e.g. Udemy coupons), page views, and user interactions, and displays metrics in a consolidated dashboard.

---

## 1. Architecture

* **`collector/`**: FastAPI backend that receives events (`/collect`), stores them in SQLite, and serves metrics (`/api/metrics/...`).
* **`visitor_log/`**: Static frontend dashboard (HTML + JS) that visualizes traffic, coupons, locations, and top pages.
* **Database**: SQLite (no external service required). File lives under `/var/www/html/visitor_analytics/data/analytics.sqlite3` in production.
* **Web server**: Apache 2.4 on DigitalOcean droplet (already hosting `tglauner.com`). Apache serves:

  * Existing course sites (`/frtb_fundamentals/`, `/mastering_interest_rate_derivatives/`, `/mastering_mbs_and_abs/`, `course-xva-essentials.tglauner.com`, and others)
  * Visitor dashboard under `/visitor_log/`
  * Reverse proxy from `/api/` → FastAPI collector (port 9000).

---

## 2. Production Installation (DigitalOcean + Apache)

### 2.1. Install requirements

App lives in /var/www/html/visitor_analytics on droplet

### 2.2 Setup and activate python

```bash
  cd visitor_analytics
  python3 -m venv .venv
  source .venv/bin/activate
  cd collector
```

### 2.3. Deploy collector (FastAPI backend)

```bash
  cd visitor_analytics/collector
  pip install -r requirements.txt
```

Initialize the database:

```bash
sqlite3 /var/lib/visitor_log/analytics.sqlite3 < migrations/001_init.sql
```

Create systemd service `/etc/systemd/system/visitor-collector.service`:

```ini
[Unit]
Description=Visitor Analytics Collector (FastAPI)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/visitor_analytics/collector
Environment=DATABASE_URL=sqlite:////var/www/html/visitor_analytics/data/analytics.sqlite3
Environment=MAXMIND_DB=/var/www/html/visitor_analytics/geo/GeoLite2-City.mmdb
Environment=ALLOWED_ORIGINS=tglauner.com,localhost,127.0.0.1,course-xva-essentials.tglauner.com
ExecStart=/var/www/html/visitor_analytics/collector/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
systemctl daemon-reexec
systemctl enable --now visitor-collector
systemctl restart visitor-collector
```

### 2.4. Apache reverse proxy

Edit `/etc/apache2/sites-enabled/tglauner-ssl.conf`:

```apache
# Serve dashboard under /visitor_log/
Alias /visitor_log /var/www/html/visitor_log
<Directory /var/www/html/visitor_log>
    Options -Indexes +FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>

# Proxy API requests to FastAPI
ProxyPreserveHost On
ProxyPass /api http://127.0.0.1:9000/api
ProxyPassReverse /api http://127.0.0.1:9000/api
```

Enable needed modules:

```bash
a2enmod proxy proxy_http headers
systemctl reload apache2
```

Now the dashboard is available at:

```
https://tglauner.com/visitor_log/
```

---

## 3. Tracking Setup (HTML Modifications)

To capture outbound clicks and page views across all courses, add the tracking script.

### 3.1. Insert tracking script

At the **bottom of `<body>`** in each course landing page:

```html
    <script src="/js/tracking.js" defer data-vite-ignore></script>
```

Make sure `/js/tracking.js` is deployed into `/var/www/html/js/tracking.js` or apache below is added as alias.
We used alias to /js/tracking.js to keep everything in visitor_analytics contained.

Apache also needs to be updated
```
        # Tracking script (new path)
        Alias /js/ "/var/www/html/visitor_analytics/tracking/"
        <Directory "/var/www/html/visitor_analytics/tracking">
                Options -Indexes
                Require all granted
        </Directory>
```

### 3.2. Coupon tracking

Ensure Udemy links **contain the coupon code** (monthly updates):

* Interest Rate Derivatives → `IRD25_AUG_2025`
* MBS/ABS → `MBS25_AUG_2025`
* FRTB → `FRTB25_AUG_2025`

Example HTML:

```html
<a href="https://www.udemy.com/course/interest-rate-derivatives/?couponCode=IRD25_AUG_2025" target="_blank">
  Enroll with Coupon
</a>
```

The collector extracts coupon codes from `href` automatically.

### 3.3. Pages to update

* `/index.html` (main landing page)
* `/frtb_fundamentals/index.html`
* `/mastering_interest_rate_derivatives/index.html`
* `/mastering_mbs_and_abs/index.html`
* `/course-xva-essentials.tglauner.com/index.html`

### 3.4. React/Vite apps (Talkshow & AI Value Advisor)

Both `/multi_model_talkshow/` and `/ai_value_advisor/` ship as React single-page apps. To tag
events from these apps with a stable identifier, include the helper near the end of their
`index.html` files:

```html
<!-- multi_model_talkshow/index.html -->
<script src="/visitor_analytics/tracking/apps/multi_model_talkshow.js" defer></script>

<!-- ai_value_advisor/index.html -->
<script src="/visitor_analytics/tracking/apps/ai_value_advisor.js" defer></script>
```

The helper sets `window.tgAnalyticsConfig.appId` before loading the shared tracker, so the
dashboard's detail view can display which app generated each event.

---

## 4. Maintenance

* **Logs**:

  ```bash
  journalctl -u visitor-collector -f
  tail -f /var/log/apache2/error.log
  ```
* **DB backup**:

  ```bash
  cp /var/lib/visitor_log/analytics.sqlite3 /root/backups/analytics.sqlite3.$(date +%F)
  ```
* **Update coupons**: edit the HTML pages monthly to reflect the current coupon codes.

---

## 5. Security Notes

* Collector is bound only to `127.0.0.1:9000`, not exposed externally.
* Apache proxies `/api/` over TLS (your Let’s Encrypt cert).
* Only `/visitor_log/` and `/api/` endpoints are exposed to the public.

---

✅ After this setup:

* Visiting `https://tglauner.com/visitor_log/` shows the dashboard.
* All tracked events flow into the SQLite DB via `/api/collect`.

---

## 6. Data Management and Test Filtering

### 6.1 Delete Specific Entries

Events and Udemy orders are stored in the SQLite tables `events_raw` and `udemy_orders`.
To remove individual rows, open the database and execute:

```bash
sqlite3 /var/lib/visitor_log/analytics.sqlite3
DELETE FROM events_raw WHERE id = <event_id>;
DELETE FROM udemy_orders WHERE order_id = '<order_id>';
```

### 6.2 Reset the Database

The collector uses the `DATABASE_URL` environment variable to locate the DB file (defaults to `/var/lib/visitor_log/analytics.sqlite3`).
To wipe everything and start fresh:

1. Stop the collector service:

   ```bash
   systemctl stop visitor-collector
   ```

2. Delete and reinitialize the database:

   ```bash
   rm /var/lib/visitor_log/analytics.sqlite3
   sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/001_init.sql
   ```

Alternatively, run `DELETE FROM` on each table instead of removing the file.

### 6.3 Exclude Test Traffic

* Restrict collector access to production hosts by setting `ALLOWED_ORIGINS` before starting the service.
* During tests, disable the tracking script by calling `window.tgAnalytics.setSampleRate(0);` on the client side.

### 6.4 Reporting Filters (exclude internal IPs)

The collector can hide internal or test traffic from every dashboard view by reading
`collector/config/reporting_filters.json`. Update the `exclude.ip_addresses` list with
any IPv4 or IPv6 addresses that should be ignored:

```json
{
  "version": 1,
  "exclude": {
    "ip_addresses": [
      { "value": "198.51.100.10", "label": "Home office" },
      "203.0.113.42"
    ]
  }
}
```

If you don't need labels, you can shorten the file to a plain array of IPs:

```json
["198.51.100.10", "203.0.113.42"]
```

Changes are picked up automatically—no FastAPI restart is required. If you want to store the
file elsewhere (for example under `/var/www/html/visitor_analytics/config/`), set the
`REPORTING_FILTERS_PATH` environment variable in the `visitor-collector` service definition.

