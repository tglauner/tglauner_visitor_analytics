SHELL := /bin/bash

dev:
	cd collector && \
	python3 -m venv .venv && source .venv/bin/activate && \
	pip install -r requirements.txt && \
	uvicorn app:app --host 127.0.0.1 --port 9000 --reload

migrate:
	sqlite3 /var/lib/visitor_log/analytics.sqlite3 < collector/migrations/001_init.sql
