1) Copy collector.service → /etc/systemd/system/ and enable/start it.
2) Run database migrations:

```
sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/001_init.sql
sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/002_add_time_on_page.sql
```

3) Append apache_snippet.conf to your SSL vhost.

### Restarts

- After changing collector code, migrations, or `collector.service`:

```
systemctl daemon-reload   # if unit file changed
systemctl restart visitor-collector
```

- After updating dashboard files, tracking script, or Apache config:

```
systemctl reload apache2
```
