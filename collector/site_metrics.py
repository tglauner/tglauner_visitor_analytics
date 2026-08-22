import json
import sqlite3
from typing import Any

from collector.site_widgets import widget_where


def _query_params(start: str, end: str, ip_params: tuple[Any, ...], widget: dict[str, Any]) -> tuple[Any, ...]:
    _, widget_params = widget_where(widget)
    return (start, end, *ip_params, *widget_params)


def summarize_widgets(
    connection: sqlite3.Connection,
    widgets: list[dict[str, Any]],
    start: str,
    end: str,
    ip_clause: str,
    ip_params: tuple[Any, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for widget in widgets:
        where, _ = widget_where(widget)
        result = connection.execute(
            f"""
            SELECT COUNT(DISTINCT uid) AS visitors,
                   COUNT(DISTINCT session_id) AS sessions,
                   SUM(CASE WHEN event_name='page_view' THEN 1 ELSE 0 END) AS page_views,
                   SUM(CASE WHEN event_name='outbound_click' THEN 1 ELSE 0 END) AS clicks,
                   CAST(COALESCE(AVG(CASE WHEN time_on_page_ms > 0 THEN time_on_page_ms END), 0) AS INTEGER) AS avg_time_on_page_ms
            FROM events_raw
            WHERE ts BETWEEN ? AND ?{ip_clause} AND {where}
            """,
            _query_params(start, end, ip_params, widget),
        ).fetchone()
        rows.append({
            **widget,
            "visitors": int(result["visitors"] or 0),
            "sessions": int(result["sessions"] or 0),
            "page_views": int(result["page_views"] or 0),
            "clicks": int(result["clicks"] or 0),
            "avg_time_on_page_ms": int(result["avg_time_on_page_ms"] or 0),
        })
    return rows


def widget_details(
    connection: sqlite3.Connection,
    widget: dict[str, Any],
    start: str,
    end: str,
    ip_clause: str,
    ip_params: tuple[Any, ...],
) -> dict[str, Any]:
    where, _ = widget_where(widget)
    params = _query_params(start, end, ip_params, widget)
    pages = [dict(row) for row in connection.execute(
        f"""
        SELECT COALESCE(path, '/') AS path,
               COUNT(DISTINCT uid) AS visitors,
               SUM(CASE WHEN event_name='page_view' THEN 1 ELSE 0 END) AS page_views,
               CAST(COALESCE(AVG(CASE WHEN time_on_page_ms > 0 THEN time_on_page_ms END), 0) AS INTEGER) AS avg_time_on_page_ms,
               SUM(CASE WHEN event_name='scroll' THEN 1 ELSE 0 END) AS scroll_actions,
               SUM(CASE WHEN event_name='outbound_click' THEN 1 ELSE 0 END) AS click_actions
        FROM events_raw
        WHERE ts BETWEEN ? AND ?{ip_clause} AND {where}
        GROUP BY path
        ORDER BY visitors DESC, page_views DESC, path ASC
        """,
        params,
    ).fetchall()]
    sources = [dict(row) for row in connection.execute(
        f"""
        SELECT CASE WHEN COALESCE(referrer, '') = '' THEN 'Direct / unknown' ELSE referrer END AS referrer,
               COUNT(DISTINCT uid) AS visitors,
               COUNT(DISTINCT session_id) AS sessions
        FROM events_raw
        WHERE event_name='page_view' AND ts BETWEEN ? AND ?{ip_clause} AND {where}
        GROUP BY referrer
        ORDER BY visitors DESC, sessions DESC, referrer ASC
        """,
        params,
    ).fetchall()]
    actions = [dict(row) for row in connection.execute(
        f"""
        SELECT event_name, COUNT(*) AS count
        FROM events_raw
        WHERE ts BETWEEN ? AND ?{ip_clause} AND {where}
        GROUP BY event_name
        ORDER BY count DESC, event_name ASC
        """,
        params,
    ).fetchall()]
    clicks = []
    for row in connection.execute(
        f"""
        SELECT COALESCE(button_id, '(unlabeled)') AS button_id, props_json, COUNT(*) AS count
        FROM events_raw
        WHERE event_name='outbound_click' AND ts BETWEEN ? AND ?{ip_clause} AND {where}
        GROUP BY button_id, props_json
        ORDER BY count DESC, button_id ASC
        LIMIT 50
        """,
        params,
    ).fetchall():
        try:
            props = json.loads(row["props_json"] or "{}")
        except json.JSONDecodeError:
            props = {}
        clicks.append({"button_id": row["button_id"], "href": props.get("href") or "", "count": row["count"]})
    scrolls = [dict(row) for row in connection.execute(
        f"""
        SELECT CAST(json_extract(props_json, '$.percent') AS INTEGER) AS percent, COUNT(*) AS count
        FROM events_raw
        WHERE event_name='scroll' AND ts BETWEEN ? AND ?{ip_clause} AND {where}
        GROUP BY percent
        ORDER BY percent ASC
        """,
        params,
    ).fetchall()]
    return {
        "widget": widget,
        "pages": pages,
        "sources": sources,
        "actions": actions,
        "clicks": clicks,
        "scrolls": scrolls,
    }
