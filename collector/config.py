import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def sqlite_path(database_url: str) -> Path:
    for prefix in ("sqlite:////", "sqlite:///"):
        if database_url.startswith(prefix):
            suffix = database_url[len(prefix):]
            return Path("/" + suffix if prefix.endswith("////") else suffix)
    raise ValueError("DATABASE_URL must use sqlite:/// or sqlite:////")


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: tuple[str, ...]
    maxmind_db: Path
    reporting_filters_path: Path
    xva_target_domain: str
    admin_auth_enabled: bool
    admin_username: str
    admin_password: str

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        values = os.environ if env is None else env
        package_dir = Path(__file__).resolve().parent
        origins = tuple(
            item.strip().lower()
            for item in values.get("ALLOWED_ORIGINS", "tglauner.com,localhost,127.0.0.1").split(",")
            if item.strip()
        )
        return cls(
            database_url=values.get("DATABASE_URL", "sqlite:////var/lib/visitor_log/analytics.sqlite3"),
            allowed_origins=origins,
            maxmind_db=Path(values.get("MAXMIND_DB", "/opt/visitor_log/geo/GeoLite2-City.mmdb")),
            reporting_filters_path=Path(values.get("REPORTING_FILTERS_PATH", package_dir / "config/reporting_filters.json")),
            xva_target_domain=values.get("XVA_TARGET_DOMAIN", "course-xva-essentials.tglauner.com"),
            admin_auth_enabled=_bool(values.get("ADMIN_AUTH_ENABLED", "false")),
            admin_username=values.get("ADMIN_USERNAME", "demo"),
            admin_password=values.get("ADMIN_PASSWORD", "demo"),
        )
