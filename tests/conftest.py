import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'visitor-analytics-tests.sqlite3'}")
os.environ.setdefault("ADMIN_AUTH_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from collector import app as app_module
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
def client(database):
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
