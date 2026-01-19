SHELL := /bin/bash
DB_PATH ?= /var/www/html/visitor_analytics/data/analytics.sqlite3

dev:
	cd collector && \
	python3 -m venv .venv && source .venv/bin/activate && \
	pip install -r requirements.txt && \
	uvicorn app:app --host 127.0.0.1 --port 9000 --reload

migrate:
	sqlite3 $(DB_PATH) < collector/migrations/001_init.sql
