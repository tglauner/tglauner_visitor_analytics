1) Install the systemd unit and start the collector:

```
sudo cp deploy/collector.service /etc/systemd/system/visitor-collector.service
sudo systemctl daemon-reload
sudo systemctl enable --now visitor-collector
```

2) Run database migrations:

```
sudo sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/001_init.sql
sudo sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/002_add_time_on_page.sql
```

3) Append apache_snippet.conf to your SSL vhost:

```
sudo tee -a /etc/apache2/sites-available/YOUR_VHOST.conf < deploy/apache_snippet.conf
```

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
