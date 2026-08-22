import datetime
import json
import re
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import HTTPException

from collector.schemas import Batch


def normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value or not value.strip():
        return None
    try:
        parsed = urlparse(value.strip() if "://" in value else f"//{value.strip()}", allow_fragments=False)
        host = (parsed.hostname or parsed.path or "").split("/")[0].strip().lower().rstrip(".")
        if not host or len(host) > 253:
            return None
        labels = host.split(".")
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            return None
        return host
    except Exception:
        return None


def cors_origin_regex(origins: tuple[str, ...]) -> str:
    patterns: List[str] = []
    for raw_host in origins:
        host = normalize_domain(raw_host) or raw_host.strip().lower()
        if not host:
            continue
        patterns.append(re.escape(host) if host in ("localhost", "127.0.0.1") else r"(?:[a-z0-9-]+\.)*" + re.escape(host))
    if not patterns:
        return r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$"
    return r"^https?://(?:" + "|".join(dict.fromkeys(patterns)) + r")(?::\d+)?$"


def allowed_host(url: Optional[str], origins: tuple[str, ...]) -> bool:
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
        return host in ("localhost", "127.0.0.1") or any(
            host == domain or host.endswith("." + domain) for domain in origins if domain
        )
    except Exception:
        return False


def base_url_from_headers(origin: str, referer: str, host: Optional[str] = None, proto: Optional[str] = None) -> Optional[str]:
    for candidate in (origin, referer):
        try:
            parsed = urlparse(candidate)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
    return f"{(proto or 'https').strip()}://{host}" if host else None


def props_value_host(props_json: Optional[str], *keys: str) -> str:
    try:
        payload = json.loads(props_json or "")
    except Exception:
        return ""
    for key in keys:
        normalized = normalize_domain(payload.get(key))
        if normalized:
            return normalized
    return ""


def parse_batch_payload(raw_body: bytes) -> Batch:
    if not raw_body:
        return Batch()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc
    try:
        return Batch.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid batch") from exc


def parse_range(start: Optional[str], end: Optional[str]) -> tuple[str, str]:
    if not start and not end:
        end_dt = datetime.datetime.now(datetime.timezone.utc)
        start_dt = end_dt - datetime.timedelta(days=7)
    elif not start or not end:
        raise HTTPException(status_code=400, detail="start and end must be provided together")
    else:
        try:
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date range") from exc
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="start must not be after end")
    return start_dt.isoformat(), end_dt.isoformat()
