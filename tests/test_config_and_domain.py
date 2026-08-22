import re

import pytest
from fastapi import HTTPException

from collector.config import Settings, sqlite_path
from collector.domain import (
    allowed_host,
    base_url_from_headers,
    cors_origin_regex,
    normalize_domain,
    parse_batch_payload,
    parse_range,
    props_value_host,
)


def test_settings_parse_origins_and_boolean():
    settings = Settings.from_env({"ALLOWED_ORIGINS": "Example.COM, localhost", "ADMIN_AUTH_ENABLED": "yes"})
    assert settings.allowed_origins == ("example.com", "localhost")
    assert settings.admin_auth_enabled is True


def test_sqlite_path_absolute():
    assert sqlite_path("sqlite:////tmp/a.db").as_posix() == "/tmp/a.db"


def test_sqlite_path_rejects_other_databases():
    with pytest.raises(ValueError):
        sqlite_path("postgresql://localhost/test")


@pytest.mark.parametrize("value,expected", [
    ("https://WWW.Example.com/a", "www.example.com"),
    ("example.com/path", "example.com"),
    ("  ", None),
])
def test_normalize_domain(value, expected):
    assert normalize_domain(value) == expected


def test_allowed_host_accepts_subdomain():
    assert allowed_host("https://course.tglauner.com/page", ("tglauner.com",))


def test_allowed_host_rejects_suffix_attack():
    assert not allowed_host("https://tglauner.com.evil.test", ("tglauner.com",))


def test_cors_regex_accepts_configured_hosts_only():
    pattern = re.compile(cors_origin_regex(("tglauner.com", "localhost")))
    assert pattern.fullmatch("https://www.tglauner.com")
    assert pattern.fullmatch("http://localhost:5174")
    assert not pattern.fullmatch("https://evil.test")


def test_base_url_prefers_origin():
    assert base_url_from_headers("https://a.test/x", "https://b.test/y") == "https://a.test"


def test_base_url_falls_back_to_proxy_headers():
    assert base_url_from_headers("", "", "api.test", "http") == "http://api.test"


def test_props_value_host_uses_fallback_key():
    assert props_value_host('{"href":"https://target.test/x"}', "target_domain", "href") == "target.test"


def test_parse_batch_rejects_invalid_json():
    with pytest.raises(HTTPException) as exc:
        parse_batch_payload(b"not-json")
    assert exc.value.status_code == 400


def test_parse_batch_accepts_empty_events():
    assert parse_batch_payload(b'{"events":[]}').events == []


def test_parse_range_rejects_partial_range():
    with pytest.raises(HTTPException):
        parse_range("2026-01-01T00:00:00", None)


def test_parse_range_rejects_reverse_range():
    with pytest.raises(HTTPException):
        parse_range("2026-02-01T00:00:00", "2026-01-01T00:00:00")
