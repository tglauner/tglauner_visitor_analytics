from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_keeps_only_requested_visible_sections():
    html = (ROOT / "visitor_log" / "index.html").read_text(encoding="utf-8")

    summary = html.index("All Tracked Sites")
    sites = html.index("Tracked sites")
    pages = html.index("Top Pages")
    assert summary < sites < pages

    for removed_heading in (
        "OpenClaw Site Snapshot",
        "Coupons & Courses",
        "Locations",
        "XVA Essentials Clicks",
        "Import Udemy CSV",
    ):
        assert removed_heading not in html


def test_dashboard_refreshes_only_visible_data_sections():
    javascript = (ROOT / "visitor_log" / "app.js").read_text(encoding="utf-8")

    assert "loadSiteWidgets()," in javascript
    assert "loadSummary()," in javascript
    assert "loadPages()," in javascript
    for removed_loader in (
        "loadOpenClawSnapshot",
        "loadCoupons",
        "loadLocations",
        "loadXvaClicks",
        "/api/import/udemy_csv",
    ):
        assert removed_loader not in javascript


def test_dashboard_displays_privacy_safe_login_state_metrics():
    html = (ROOT / "visitor_log" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "visitor_log" / "app.js").read_text(encoding="utf-8")
    tracker = (ROOT / "tracking" / "tracking.js").read_text(encoding="utf-8")

    assert "Login state" in html
    assert "Signed-in visitors" in javascript
    assert "Looked only" in javascript
    assert "login_conversion_pct" in javascript
    assert "authState" in tracker
    assert "ev.auth_state = C.authState" in tracker
