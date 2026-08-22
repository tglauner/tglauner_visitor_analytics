import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REQUIRED_WIDGET_FIELDS = ("id", "label", "url", "host", "path_prefix")


def load_site_widgets(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise ValueError("Unsupported site widget configuration version")
    widgets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for source in ("manual", "discovered"):
        entries = payload.get(source, [])
        if not isinstance(entries, list):
            raise ValueError(f"{source} must be a list")
        for raw in entries:
            if not isinstance(raw, dict) or any(not raw.get(field) for field in REQUIRED_WIDGET_FIELDS):
                raise ValueError(f"Invalid {source} widget")
            widget = {field: str(raw[field]).strip() for field in REQUIRED_WIDGET_FIELDS}
            parsed = urlparse(widget["url"])
            if parsed.scheme != "https" or parsed.hostname != widget["host"]:
                raise ValueError(f"Invalid widget URL: {widget['url']}")
            if not widget["path_prefix"].startswith("/"):
                raise ValueError(f"Invalid widget path: {widget['path_prefix']}")
            if widget["id"] in seen_ids or widget["url"] in seen_urls:
                continue
            seen_ids.add(widget["id"])
            seen_urls.add(widget["url"])
            widget["source"] = source
            widgets.append(widget)
    return widgets


def widget_where(widget: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    path_prefix = widget["path_prefix"]
    if path_prefix == "/":
        return "props_page_host(props_json) = ?", (widget["host"],)
    return "props_page_host(props_json) = ? AND COALESCE(path, '/') LIKE ?", (
        widget["host"],
        f"{path_prefix}%",
    )
