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
* **Database**: SQLite (no external service required). File lives under `/var/lib/visitor_log/analytics.sqlite3` in production.
* **Web server**: Apache 2.4 on DigitalOcean droplet (already hosting `tglauner.com`). Apache serves:

  * Existing course sites (`/frtb_fundamentals/`, `/mastering_interest_rate_derivatives/`, `/mastering_mbs_and_abs/`)
  * Visitor dashboard under `/visitor_log/`
  * Reverse proxy from `/api/` → FastAPI collector (port 9000).

---

## 2. Production Installation (DigitalOcean + Apache)

### 2.1. Install requirements

SSH into the droplet:

```bash
ssh root@45.55.196.120
apt update && apt install -y python3 python3-venv python3-pip
```

### 2.2. Create app directories

```bash
mkdir -p /opt/visitor_log/collector
mkdir -p /var/lib/visitor_log
mkdir -p /var/www/html/visitor_log
```

### 2.3. Deploy collector (FastAPI backend)

```bash
cd /opt/visitor_log/collector
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Initialize the database:

```bash
sqlite3 /var/lib/visitor_log/analytics.sqlite3 < migrations/001_init.sql
```

Create systemd service `/etc/systemd/system/visitor-collector.service`:

```ini
[Unit]
Description=Visitor Analytics Collector
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/visitor_log/collector
Environment="DATABASE_URL=sqlite:////var/lib/visitor_log/analytics.sqlite3"
ExecStart=/opt/visitor_log/collector/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
systemctl daemon-reexec
systemctl enable --now visitor-collector
```

### 2.4. Deploy dashboard (frontend)

```bash
rsync -avz visitor_log/ /var/www/html/visitor_log/
```

### 2.5. Apache reverse proxy

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
<script src="/js/tracking.js" defer></script>
```

Make sure `/js/tracking.js` is deployed into `/var/www/html/js/tracking.js`.
This script automatically records page views and outbound link clicks.

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

