Here’s a **monthly operations checklist** for your visitor analytics platform. You can drop this into the repo as `MAINTENANCE.md` so you don’t lose track.

---

# Visitor Analytics – Monthly Operations Checklist

This checklist ensures that the tracking and dashboard remain accurate and production-ready.

---

## 1. Coupon Codes

* [ ] Verify **Udemy coupons** for each course (they change monthly):

  * Interest Rate Derivatives → `IRD##_MMM_YYYY`
  * MBS/ABS → `MBS##_MMM_YYYY`
  * FRTB → `FRTB##_MMM_YYYY`
* [ ] Update links in:

  * `/index.html`
  * `/frtb_fundamentals/index.html`
  * `/mastering_interest_rate_derivatives/index.html`
  * `/mastering_mbs_and_abs/index.html`
* [ ] Test by clicking the links → check collector logs:

  ```bash
  journalctl -u visitor-collector -f
  ```

---

## 2. Database Health

* [ ] Check SQLite DB file size and integrity:

  ```bash
  ls -lh /var/lib/visitor_log/analytics.sqlite3
  sqlite3 /var/lib/visitor_log/analytics.sqlite3 "PRAGMA integrity_check;"
  ```
* [ ] Backup database:

  ```bash
  cp /var/lib/visitor_log/analytics.sqlite3 /root/backups/analytics.sqlite3.$(date +%F)
  ```

---

## 3. Logs & Monitoring

* [ ] Review collector logs:

  ```bash
  journalctl -u visitor-collector -n 100 --no-pager
  ```
* [ ] Review Apache logs for errors:

  ```bash
  tail -n 100 /var/log/apache2/error.log
  tail -n 100 /var/log/apache2/access.log
  ```

---

## 4. System Updates

* [ ] Update apt packages:

  ```bash
  apt update && apt upgrade -y
  ```
* [ ] Update Python dependencies:

  ```bash
  cd /opt/visitor_log/collector
  source .venv/bin/activate
  pip install --upgrade -r requirements.txt
  ```

---

## 5. Functionality Tests

* [ ] Visit `https://tglauner.com/visitor_log/` and confirm dashboard loads.
* [ ] Trigger a test event:

  ```bash
  curl -X POST https://tglauner.com/api/collect \
    -H "Origin: https://tglauner.com" \
    -H "Content-Type: application/json" \
    -d '{"events":[{"ts":"2025-08-16T12:00:05Z","uid":"u_test","session_id":"s_test","event_name":"outbound_click","path":"/","href":"https://www.udemy.com/course/test-course/?couponCode=TEST25_AUG_2025","title":"Test"}]}'
  ```
* [ ] Check if the event appears in dashboard within the time window.

---

## 6. Optional Cleanup

* [ ] Delete old backups (>6 months old).
* [ ] Archive monthly CSV exports (if enabled later).

---

⚡ This routine should take \~20 minutes per month once everything is stable.

---

Do you want me to also write a **daily lightweight checklist** (basically a quick health check in <5 min), or just stick with monthly?
