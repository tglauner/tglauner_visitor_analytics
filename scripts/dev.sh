#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run: make setup" >&2
  exit 1
fi
exec .venv/bin/python -m uvicorn collector.app:app --host 127.0.0.1 --port 9000 --reload
