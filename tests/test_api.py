from dataclasses import replace

from collector import app as app_module


RANGE = "start=2026-08-01T00:00:00%2B00:00&end=2026-09-01T00:00:00%2B00:00"


def test_health_is_public(client):
    assert client.get("/healthz").json() == {"ok": True}


def test_collect_rejects_untrusted_origin(client, event_payload):
    response = client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://evil.test"})
    assert response.status_code == 403


def test_collect_rejects_invalid_batch(client):
    response = client.post("/collect", content=b"bad", headers={"origin": "https://tglauner.com"})
    assert response.status_code == 400


def test_collect_stores_event(client, database, event_payload):
    response = client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://tglauner.com"})
    assert response.json() == {"ok": True, "n": 1}
    assert database.connection.execute("SELECT COUNT(*) FROM events_raw").fetchone()[0] == 1


def test_collect_constructs_page_url(client, database, event_payload):
    event_payload.pop("page_url")
    client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://tglauner.com"})
    props = database.connection.execute("SELECT props_json FROM events_raw").fetchone()[0]
    assert '"page_url": "https://tglauner.com/welcome"' in props


def test_summary_counts_events(client, event_payload):
    client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://tglauner.com"})
    data = client.get(f"/api/metrics/summary?{RANGE}").json()
    assert (data["visitors"], data["sessions"], data["page_views"]) == (1, 1, 1)


def test_top_pages_groups_by_host(client, event_payload):
    client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://tglauner.com"})
    rows = client.get(f"/api/metrics/top_pages?{RANGE}").json()["rows"]
    assert rows[0]["display_path"] == "https://tglauner.com/welcome"


def test_site_snapshot_requires_host(client):
    assert client.get(f"/api/metrics/site_snapshot?{RANGE}").status_code == 422


def test_site_snapshot_rejects_invalid_host(client):
    assert client.get(f"/api/metrics/site_snapshot?host=%%%25&{RANGE}").status_code == 400


def test_udemy_csv_import_route_is_removed(client):
    assert client.post("/api/import/udemy_csv").status_code == 404


def test_admin_auth_blocks_missing_credentials(client, monkeypatch):
    monkeypatch.setattr(app_module, "settings", replace(app_module.settings, admin_auth_enabled=True, admin_username="demo", admin_password="demo"))
    assert client.get(f"/api/metrics/summary?{RANGE}").status_code == 401


def test_admin_auth_accepts_credentials(client, monkeypatch):
    monkeypatch.setattr(app_module, "settings", replace(app_module.settings, admin_auth_enabled=True, admin_username="demo", admin_password="demo"))
    assert client.get(f"/api/metrics/summary?{RANGE}", auth=("demo", "demo")).status_code == 200


def test_health_remains_public_when_auth_enabled(client, monkeypatch):
    monkeypatch.setattr(app_module, "settings", replace(app_module.settings, admin_auth_enabled=True))
    assert client.get("/healthz").status_code == 200
