import os
import json
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'visitor-analytics-tests.sqlite3'}")
os.environ.setdefault("ADMIN_AUTH_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from unittest.mock import patch

# Test configuration is explicit; importing the app must not read a real .env.
with patch("dotenv.load_dotenv", return_value=False):
    from collector import app as app_module
from collector.agent_status import AgentStore
from collector.database import Database


@pytest.fixture
def database(tmp_path, monkeypatch):
    db = Database(tmp_path / "analytics.sqlite3")
    db.initialize()
    db.connection.create_function("props_host", 1, app_module.props_host_from_json)
    db.connection.create_function("props_page_host", 1, app_module.props_page_host_from_json)
    monkeypatch.setattr(app_module, "database", db)
    monkeypatch.setattr(app_module, "conn", db.connection)
    monkeypatch.setattr(app_module, "dblock", db.lock)
    yield db
    db.close()


@pytest.fixture
def agent_store(tmp_path, monkeypatch):
    projects_root = tmp_path / "Projects"
    (projects_root / "project-one").mkdir(parents=True)
    (projects_root / "project-two").mkdir()
    registry_path = tmp_path / "agent_registry.json"
    registry_path.write_text(json.dumps({
        "version": 1,
        "agents": [{"id": "project-one", "name": "Project One", "project_path": "project-one"}],
    }), encoding="utf-8")
    store = AgentStore(registry_path, tmp_path / "agent_status.json", projects_root)
    monkeypatch.setattr(app_module, "agent_store", store)
    return store


@pytest.fixture
def client(database, agent_store):
    return TestClient(app_module.app)


@pytest.fixture
def event_payload():
    return {
        "ts": "2026-08-20T12:00:00+00:00",
        "uid": "visitor-1",
        "session_id": "session-1",
        "event_name": "page_view",
        "path": "/welcome",
        "title": "Welcome",
        "page_url": "https://tglauner.com/welcome",
    }
