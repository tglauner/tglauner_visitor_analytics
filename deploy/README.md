1) Copy collector.service → /etc/systemd/system/ and enable/start it.
2) Append apache_snippet.conf to your SSL vhost and reload Apache.
3) Copy visitor_log/* to /var/www/html/visitor_log/.
4) Copy tracking/tracking.js to /var/www/html/js/.
