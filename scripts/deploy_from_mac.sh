#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DROPLET="${DROPLET:-root@45.55.196.120}"
REMOTE_APP_ROOT="${REMOTE_APP_ROOT:-/var/www/html/visitor_analytics}"
REMOTE_DASHBOARD_ROOT="${REMOTE_DASHBOARD_ROOT:-/var/www/html/visitor_analytics/visitor_log}"
REMOTE_DB_PATH="${REMOTE_DB_PATH:-$REMOTE_APP_ROOT/data/analytics.sqlite3}"
REMOTE_SERVICE_PATH="${REMOTE_SERVICE_PATH:-/etc/systemd/system/visitor-collector.service}"
REMOTE_SSL_VHOST="${REMOTE_SSL_VHOST:-/etc/apache2/sites-available/tglauner-ssl.conf}"

BOOTSTRAP=0
SKIP_PIP=0
SKIP_VALIDATE=0
SYNC_UNIT=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Deploy visitor_analytics from this Mac to the DigitalOcean droplet.

Options:
  --bootstrap      First-time install: create dirs, venv, service, DB, Apache wiring
  --skip-pip       Skip remote pip install -r collector/requirements.txt
  --skip-validate  Skip post-deploy health checks
  --skip-unit-sync Skip syncing deploy/visitor-analytics.service to systemd
  -h, --help       Show this help

Environment overrides:
  DROPLET              Default: $DROPLET
  REMOTE_APP_ROOT      Default: $REMOTE_APP_ROOT
  REMOTE_DASHBOARD_ROOT Default: $REMOTE_DASHBOARD_ROOT
  REMOTE_DB_PATH       Default: $REMOTE_DB_PATH
  REMOTE_SERVICE_PATH  Default: $REMOTE_SERVICE_PATH
  REMOTE_SSL_VHOST     Default: $REMOTE_SSL_VHOST

Examples:
  ./scripts/deploy_from_mac.sh
  ./scripts/deploy_from_mac.sh --bootstrap
  DROPLET=root@1.2.3.4 ./scripts/deploy_from_mac.sh
EOF
}

while (($#)); do
  case "$1" in
    --bootstrap)
      BOOTSTRAP=1
      ;;
    --skip-pip)
      SKIP_PIP=1
      ;;
    --skip-validate)
      SKIP_VALIDATE=1
      ;;
    --skip-unit-sync)
      SYNC_UNIT=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

run_ssh() {
  ssh "$DROPLET" "$@"
}

echo "Deploy target: $DROPLET"
echo "Remote app root: $REMOTE_APP_ROOT"
echo "Remote dashboard root: $REMOTE_DASHBOARD_ROOT"

if [[ "$BOOTSTRAP" -eq 1 ]]; then
  echo "Bootstrap: creating remote directories and Python venv"
  run_ssh "
    mkdir -p '$REMOTE_APP_ROOT' '$REMOTE_DASHBOARD_ROOT' '$REMOTE_APP_ROOT/data' '$REMOTE_APP_ROOT/geo' &&
    cd '$REMOTE_APP_ROOT' &&
    if [[ ! -x .venv/bin/python3 ]]; then
      python3 -m venv .venv
    fi
  "
fi

echo "Syncing application code"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.DS_Store' \
  --exclude 'data/' \
  --exclude 'geo/' \
  --exclude 'collector/.env' \
  --exclude 'collector/analytics.sqlite3' \
  --exclude 'collector/analytics.sqlite3-shm' \
  --exclude 'collector/analytics.sqlite3-wal' \
  --exclude 'visitor_log/' \
  "$ROOT_DIR/" "$DROPLET:$REMOTE_APP_ROOT/"

echo "Syncing dashboard assets"
rsync -az --delete \
  --exclude '.DS_Store' \
  "$ROOT_DIR/visitor_log/" "$DROPLET:$REMOTE_DASHBOARD_ROOT/"

if [[ "$BOOTSTRAP" -eq 1 ]]; then
  echo "Installing systemd unit"
  scp "$ROOT_DIR/deploy/visitor-analytics.service" "$DROPLET:/tmp/visitor-analytics.service"
  run_ssh "
    mv /tmp/visitor-analytics.service '$REMOTE_SERVICE_PATH' &&
    systemctl daemon-reload &&
    systemctl enable visitor-collector
  "

  echo "Running database migrations"
  run_ssh "
    sqlite3 '$REMOTE_DB_PATH' < '$REMOTE_APP_ROOT/collector/migrations/001_init.sql'
  "
  if ! run_ssh "sqlite3 '$REMOTE_DB_PATH' \"PRAGMA table_info(events_raw);\" | grep -q '|time_on_page_ms|'" ; then
    run_ssh "sqlite3 '$REMOTE_DB_PATH' < '$REMOTE_APP_ROOT/collector/migrations/002_add_time_on_page.sql'"
  fi

  echo "Appending Apache wiring if missing"
  run_ssh "
    grep -q 'Visitor Analytics wiring' '$REMOTE_SSL_VHOST' ||
    cat '$REMOTE_APP_ROOT/deploy/apache_snippet.conf' >> '$REMOTE_SSL_VHOST'
  "

  echo "Ensuring required Apache modules are enabled"
  run_ssh "a2enmod proxy proxy_http headers rewrite >/dev/null 2>&1 || true"
fi

if [[ "$SYNC_UNIT" -eq 1 && "$BOOTSTRAP" -eq 0 ]]; then
  echo "Syncing systemd unit"
  scp "$ROOT_DIR/deploy/visitor-analytics.service" "$DROPLET:/tmp/visitor-analytics.service"
  run_ssh "
    mv /tmp/visitor-analytics.service '$REMOTE_SERVICE_PATH' &&
    systemctl daemon-reload
  "
fi

if [[ "$SKIP_PIP" -eq 0 ]]; then
  echo "Installing Python requirements on droplet"
  run_ssh "
    cd '$REMOTE_APP_ROOT' &&
    ./.venv/bin/pip install -r collector/requirements.txt
  "
fi

echo "Restarting services"
run_ssh "
  systemctl daemon-reload &&
  systemctl restart visitor-collector &&
  apache2ctl configtest &&
  systemctl reload apache2
"

if [[ "$SKIP_VALIDATE" -eq 0 ]]; then
  echo "Running validation checks"
  run_ssh "systemctl --no-pager --lines=0 status visitor-collector"
  echo "Waiting for collector health endpoint"
  run_ssh '
    for attempt in $(seq 1 20); do
      if curl -fsS http://127.0.0.1:9000/healthz >/dev/null; then
        exit 0
      fi
      sleep 1
    done
    echo "Collector health endpoint did not become ready in time" >&2
    systemctl --no-pager -l status visitor-collector >&2 || true
    journalctl -u visitor-collector -n 50 --no-pager >&2 || true
    exit 1
  '
  curl -fsSI https://tglauner.com/visitor_log/ >/dev/null
  curl -fsSI https://tglauner.com/visitor_analytics/tracking/apps/openclaw_private_setup.js >/dev/null
  echo "Validation passed"
fi

echo "Deployment complete"
