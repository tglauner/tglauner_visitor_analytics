#!/usr/bin/env python3
"""Refresh discovered site widgets from Apache configuration without changing manual entries."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "collector/config/site_widgets.json"
DEFAULT_HOST = "root@45.55.196.120"
REMOTE_COMMAND = (
    "grep -RHE '^[[:space:]]*(ServerName|ServerAlias|Alias)[[:space:]]+' "
    "/etc/apache2/sites-enabled 2>/dev/null"
)
EXCLUDED_ALIAS_PREFIXES = (
    "/.well-known/",
    "/visitor_log/",
    "/visitor_analytics/",
    "/js/",
    "/javascript",
)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def label_for(host: str, path: str) -> str:
    if path != "/":
        return path.strip("/").replace("_", " ").replace("-", " ").title()
    name = host.removeprefix("www.").split(".tglauner.com")[0]
    return "TGlauner.com" if name == "tglauner.com" else name.replace("-", " ").title()


def canonical_host(names: list[str]) -> str:
    candidates = [name.lower().rstrip(".") for name in names if name and "*" not in name]
    non_www = [name for name in candidates if not name.startswith("www.")]
    return sorted(non_www or candidates, key=lambda value: (len(value), value))[0]


def parse_apache_inventory(text: str) -> list[dict[str, str]]:
    files: dict[str, dict[str, list[str]]] = {}
    for raw_line in text.splitlines():
        match = re.match(r"(?P<file>[^:]+):\s*(?P<kind>ServerName|ServerAlias|Alias)\s+(?P<value>.+)$", raw_line.strip())
        if not match:
            continue
        record = files.setdefault(match.group("file"), {"names": [], "aliases": []})
        if match.group("kind") in ("ServerName", "ServerAlias"):
            record["names"].extend(match.group("value").split())
        else:
            alias_path = match.group("value").split()[0].strip('"')
            if alias_path.startswith("/") and not alias_path.startswith(EXCLUDED_ALIAS_PREFIXES):
                record["aliases"].append(alias_path)

    discovered: dict[str, dict[str, str]] = {}
    for record in files.values():
        if not record["names"]:
            continue
        host = canonical_host(record["names"])
        if not host.endswith("tglauner.com"):
            continue
        paths = {"/", *record["aliases"]}
        for path in paths:
            normalized_path = "/" if path == "/" else f"/{path.strip('/')}/"
            url = f"https://{host}{normalized_path}"
            discovered[url] = {
                "id": f"apache-{slug(host)}{('-' + slug(normalized_path)) if normalized_path != '/' else ''}",
                "label": label_for(host, normalized_path),
                "url": url,
                "host": host,
                "path_prefix": normalized_path,
            }
    return [discovered[url] for url in sorted(discovered)]


def fetch_inventory(host: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, REMOTE_COMMAND],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def update_config(config_path: Path, discovered: list[dict[str, str]], *, check: bool = False) -> bool:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    manual_before = json.dumps(payload.get("manual", []), sort_keys=True)
    manual_urls = {entry["url"] for entry in payload.get("manual", [])}
    payload["discovered"] = [entry for entry in discovered if entry["url"] not in manual_urls]
    if json.dumps(payload.get("manual", []), sort_keys=True) != manual_before:
        raise RuntimeError("Manual widgets changed unexpectedly")
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    current = config_path.read_text(encoding="utf-8")
    changed = current != rendered
    if changed and not check:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, delete=False) as handle:
            handle.write(rendered)
            temporary = Path(handle.name)
        temporary.replace(config_path)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="SSH target used for read-only Apache discovery")
    parser.add_argument("--input", type=Path, help="Parse a saved Apache inventory instead of SSH")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--check", action="store_true", help="Exit 1 when discovered widgets differ; do not write")
    args = parser.parse_args()
    inventory = args.input.read_text(encoding="utf-8") if args.input else fetch_inventory(args.host)
    discovered = parse_apache_inventory(inventory)
    changed = update_config(args.config, discovered, check=args.check)
    print(f"discovered={len(discovered)} changed={'yes' if changed else 'no'} manual=preserved")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
