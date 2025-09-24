import json
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


class ReportingFilterLoader:
    """Loads reporting filters from a JSON document on disk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._excluded_ips: List[str] = []
        self._mtime_ns: Optional[int] = None

    def excluded_ips(self) -> List[str]:
        with self._lock:
            self._refresh_if_needed()
            return list(self._excluded_ips)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _refresh_if_needed(self) -> None:
        try:
            mtime_ns = self.path.stat().st_mtime_ns
        except FileNotFoundError:
            self._excluded_ips = []
            self._mtime_ns = None
            return

        if self._mtime_ns == mtime_ns:
            return

        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return

        raw = raw.strip()
        if not raw:
            self._excluded_ips = []
            self._mtime_ns = mtime_ns
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Keep the previous configuration and retry on next call.
            return

        self._excluded_ips = self._parse_payload(payload)
        self._mtime_ns = mtime_ns

    def _parse_payload(self, payload: object) -> List[str]:
        if isinstance(payload, dict):
            # Prefer the structured "exclude" block, fall back to top-level keys
            blocks: Sequence[Optional[Iterable[object]]] = (
                self._ensure_iterable(payload.get("exclude"), key="ip_addresses"),
                self._ensure_iterable(payload, key="ip_addresses"),
            )
            for block in blocks:
                if block is not None:
                    return self._parse_ip_entries(block)
            return []

        if isinstance(payload, list):
            return self._parse_ip_entries(payload)

        return []

    def _ensure_iterable(self, value: object, key: str) -> Optional[Iterable[object]]:
        if isinstance(value, dict):
            candidate = value.get(key)
            if isinstance(candidate, list):
                return candidate
        return None

    def _parse_ip_entries(self, entries: Iterable[object]) -> List[str]:
        ips: List[str] = []
        for entry in entries:
            if isinstance(entry, str):
                ip = entry.strip()
                if ip:
                    ips.append(ip)
            elif isinstance(entry, dict):
                ip_value = self._extract_ip_from_dict(entry)
                if ip_value:
                    ips.append(ip_value)
        # Deduplicate while preserving order
        seen = set()
        unique_ips = []
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                unique_ips.append(ip)
        return unique_ips

    def _extract_ip_from_dict(self, entry: dict) -> Optional[str]:
        for key in ("value", "ip", "address"):
            if key in entry and entry[key] is not None:
                ip = str(entry[key]).strip()
                if ip:
                    return ip
        return None

    # ------------------------------------------------------------------
    # SQL helpers
    # ------------------------------------------------------------------
    def sql_fragment(self, column: str = "ip") -> tuple[str, tuple]:
        ips = self.excluded_ips()
        if not ips:
            return "", tuple()
        placeholders = ",".join(["?"] * len(ips))
        clause = f" AND ({column} IS NULL OR {column} NOT IN ({placeholders}))"
        return clause, tuple(ips)


__all__ = ["ReportingFilterLoader"]
