SHELL := /bin/bash
PYTHON := .venv/bin/python

setup:
	python3 -m venv --clear .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install --index-url https://pypi.org/simple -r collector/requirements-dev.txt

dev:
	$(PYTHON) -m uvicorn collector.app:app --host 127.0.0.1 --port 9000 --reload

test:
	$(PYTHON) -m pytest -q

smoke:
	curl -fsS http://127.0.0.1:9000/healthz

deploy-prod:
	./scripts/deploy_from_mac.sh

deploy-prod-bootstrap:
	./scripts/deploy_from_mac.sh --bootstrap
