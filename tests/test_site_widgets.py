import json
from dataclasses import replace

import pytest

from collector import app as app_module
from collector.site_widgets import load_site_widgets, widget_where
from scripts.update_site_widgets import parse_apache_inventory, update_config


RANGE = "start=2026-08-01T00:00:00%2B00:00&end=2026-09-01T00:00:00%2B00:00"
APACHE = """
/etc/apache2/sites-enabled/main.conf: ServerName tglauner.com
/etc/apache2/sites-enabled/main.conf: ServerAlias www.tglauner.com
/etc/apache2/sites-enabled/main.conf: Alias /multi_model_talkshow/ /var/www/html/talkshow/
/etc/apache2/sites-enabled/main.conf: Alias /visitor_log/ /var/www/html/visitor_log/
/etc/apache2/sites-enabled/sub.conf: ServerName www.course-xva-essentials.tglauner.com
/etc/apache2/sites-enabled/sub.conf: ServerAlias course-xva-essentials.tglauner.com
/etc/apache2/sites-enabled/acme.conf: ServerName unrelated.example.com
"""


def test_load_widgets_marks_sources(tmp_path):
    path = tmp_path / "widgets.json"
    path.write_text(json.dumps({
        "version": 1,
        "manual": [{"id": "m", "label": "Manual", "url": "https://a.tglauner.com/", "host": "a.tglauner.com", "path_prefix": "/"}],
        "discovered": [{"id": "d", "label": "Found", "url": "https://b.tglauner.com/", "host": "b.tglauner.com", "path_prefix": "/"}],
    }))
    assert [widget["source"] for widget in load_site_widgets(path)] == ["manual", "discovered"]


def test_load_widgets_rejects_invalid_url(tmp_path):
    path = tmp_path / "widgets.json"
    path.write_text(json.dumps({"version": 1, "manual": [{"id": "m", "label": "Bad", "url": "http://bad/", "host": "bad", "path_prefix": "/"}], "discovered": []}))
    with pytest.raises(ValueError):
        load_site_widgets(path)


def test_widget_where_root_matches_whole_host():
    clause, params = widget_where({"host": "tglauner.com", "path_prefix": "/"})
    assert "LIKE" not in clause
    assert params == ("tglauner.com",)


def test_widget_where_path_uses_prefix():
    clause, params = widget_where({"host": "tglauner.com", "path_prefix": "/course/"})
    assert "LIKE" in clause
    assert params == ("tglauner.com", "/course/%")


def test_apache_parser_finds_hosts_and_application_aliases():
    urls = {entry["url"] for entry in parse_apache_inventory(APACHE)}
    assert urls == {
        "https://tglauner.com/",
        "https://tglauner.com/multi_model_talkshow/",
        "https://course-xva-essentials.tglauner.com/",
    }


def test_apache_parser_ignores_dashboard_alias():
    assert all("visitor_log" not in entry["url"] for entry in parse_apache_inventory(APACHE))


def test_update_preserves_manual_entries(tmp_path):
    path = tmp_path / "widgets.json"
    manual = [{"id": "mine", "label": "Mine", "url": "https://manual.tglauner.com/", "host": "manual.tglauner.com", "path_prefix": "/"}]
    path.write_text(json.dumps({"version": 1, "manual": manual, "discovered": []}))
    update_config(path, parse_apache_inventory(APACHE))
    assert json.loads(path.read_text())["manual"] == manual


def test_update_filters_manual_url_duplicates(tmp_path):
    path = tmp_path / "widgets.json"
    manual = [{"id": "mine", "label": "Mine", "url": "https://tglauner.com/", "host": "tglauner.com", "path_prefix": "/"}]
    path.write_text(json.dumps({"version": 1, "manual": manual, "discovered": []}))
    update_config(path, parse_apache_inventory(APACHE))
    assert all(entry["url"] != "https://tglauner.com/" for entry in json.loads(path.read_text())["discovered"])


def test_site_summary_includes_zero_visitor_widgets(client):
    data = client.get(f"/api/sites?{RANGE}").json()
    assert len(data["widgets"]) >= 10
    assert all(widget["visitors"] == 0 for widget in data["widgets"])


def test_site_summary_counts_matching_widget(client, event_payload):
    client.post("/collect", json={"events": [event_payload]}, headers={"origin": "https://tglauner.com"})
    widgets = client.get(f"/api/sites?{RANGE}").json()["widgets"]
    home = next(widget for widget in widgets if widget["id"] == "tglauner-home")
    assert home["visitors"] == 1
    assert home["page_views"] == 1


def test_site_details_returns_pages_sources_and_actions(client, event_payload):
    events = [event_payload, {
        **event_payload,
        "event_name": "scroll",
        "percent": 50,
    }, {
        **event_payload,
        "event_name": "outbound_click",
        "button_id": "buy",
        "href": "https://example.com/buy",
    }, {
        **event_payload,
        "event_name": "page_unload",
        "time_on_page_ms": 12000,
    }]
    client.post("/collect", json={"events": events}, headers={"origin": "https://tglauner.com"})
    data = client.get(f"/api/sites/tglauner-home?{RANGE}").json()
    assert data["pages"][0]["avg_time_on_page_ms"] == 12000
    assert data["pages"][0]["scroll_actions"] == 1
    assert data["pages"][0]["click_actions"] == 1
    assert data["scrolls"] == [{"percent": 50, "count": 1}]
    assert data["clicks"][0]["button_id"] == "buy"


def test_site_details_returns_404_for_unknown_widget(client):
    assert client.get(f"/api/sites/not-configured?{RANGE}").status_code == 404


def test_site_endpoints_require_auth_when_enabled(client, monkeypatch):
    monkeypatch.setattr(app_module, "settings", replace(app_module.settings, admin_auth_enabled=True))
    assert client.get(f"/api/sites?{RANGE}").status_code == 401
