import json
from datetime import datetime, timedelta, timezone

import pytest

from collector.agent_status import AgentStore, AgentStoreError, StaleAgentEventError


def test_success_becomes_needs_work_after_one_hour(agent_store):
    started = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    agent_store.record_event("project-one", "success", job_id="job-1", now=started)

    fresh = agent_store.list_agents(now=started + timedelta(minutes=59, seconds=59))["agents"][0]
    stale = agent_store.list_agents(now=started + timedelta(hours=1))["agents"][0]

    assert fresh["display_status"] == "success"
    assert stale["display_status"] == "needs_work"
    assert stale["last_status"] == "success"


def test_stale_completion_cannot_replace_active_job(agent_store):
    agent_store.record_event("project-one", "working", job_id="new-job")

    with pytest.raises(StaleAgentEventError):
        agent_store.record_event("project-one", "success", job_id="old-job")

    assert agent_store.list_agents()["agents"][0]["display_status"] == "working"


def test_registry_crud_is_persistent_and_removes_state(agent_store):
    created = agent_store.create_agent("Second Agent", "project-two")
    agent_store.record_event(created["id"], "failure", message="Validation failed")
    updated = agent_store.update_agent(created["id"], "Renamed Agent", "project-two")
    assert updated["name"] == "Renamed Agent"

    agent_store.delete_agent(created["id"])

    assert [agent["id"] for agent in agent_store.list_agents()["agents"]] == ["project-one"]
    state = json.loads(agent_store.status_path.read_text(encoding="utf-8"))
    assert created["id"] not in state["agents"]


def test_project_paths_cannot_escape_projects_root(agent_store):
    with pytest.raises(AgentStoreError):
        agent_store.create_agent("Outside", "../outside")


@pytest.mark.parametrize("path", ["/project-one", "//host/project-one", "C:/project-one", "C:\\project-one"])
def test_absolute_project_paths_are_rejected(agent_store, path):
    with pytest.raises(AgentStoreError):
        agent_store.create_agent("Absolute Path", path)


def test_symlinked_project_path_cannot_escape_projects_root(tmp_path):
    projects_root = tmp_path / "Projects"
    projects_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (projects_root / "linked-outside").symlink_to(outside, target_is_directory=True)
    store = AgentStore(tmp_path / "registry.json", tmp_path / "status.json", projects_root)

    with pytest.raises(AgentStoreError):
        store.create_agent("Outside Link", "linked-outside")


def test_agent_api_lifecycle_and_crud(client):
    listed = client.get("/api/agents")
    assert listed.status_code == 200
    assert listed.json()["counts"]["needs_work"] == 1

    created = client.post("/api/agents", json={"name": "Project Two", "project_path": "project-two"})
    assert created.status_code == 201
    agent_id = created.json()["id"]

    working = client.post(
        f"/api/agents/{agent_id}/events",
        json={"status": "working", "job_id": "job-22", "message": "Running tests"},
    )
    assert working.status_code == 200
    assert working.json()["display_status"] == "working"

    failed = client.post(
        f"/api/agents/{agent_id}/events",
        json={"status": "failure", "job_id": "job-22", "message": "Test failed"},
    )
    assert failed.json()["display_status"] == "failure"

    edited = client.put(
        f"/api/agents/{agent_id}",
        json={"name": "Project Two Renamed", "project_path": "project-two"},
    )
    assert edited.json()["name"] == "Project Two Renamed"
    assert client.delete(f"/api/agents/{agent_id}").status_code == 204


def test_agent_api_rejects_unknown_agent_event(client):
    response = client.post("/api/agents/missing/events", json={"status": "working"})
    assert response.status_code == 404


def test_agent_api_uses_admin_auth(client, monkeypatch):
    from dataclasses import replace
    from collector import app as app_module

    monkeypatch.setattr(
        app_module,
        "settings",
        replace(app_module.settings, admin_auth_enabled=True, admin_username="demo", admin_password="demo"),
    )
    assert client.get("/api/agents").status_code == 401
    assert client.get("/api/agents", auth=("demo", "demo")).status_code == 200
