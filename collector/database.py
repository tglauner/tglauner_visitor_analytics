import sqlite3
import threading
from pathlib import Path


BASE_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS events_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, session_id TEXT, ts TEXT,
  event_name TEXT, path TEXT, title TEXT, referrer TEXT, course_slug TEXT,
  coupon TEXT, button_id TEXT, utm_source TEXT, utm_medium TEXT,
  utm_campaign TEXT, ip TEXT, geo_country TEXT, geo_region TEXT, device TEXT,
  browser TEXT, os TEXT, props_json TEXT, time_on_page_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events_raw(ts);
CREATE INDEX IF NOT EXISTS idx_events_event_ts ON events_raw(event_name, ts);
CREATE INDEX IF NOT EXISTS idx_events_coupon_slug ON events_raw(coupon, course_slug);
CREATE INDEX IF NOT EXISTS idx_events_uid ON events_raw(uid);
CREATE INDEX IF NOT EXISTS idx_events_session ON events_raw(session_id);
CREATE INDEX IF NOT EXISTS idx_events_path ON events_raw(path);
CREATE TABLE IF NOT EXISTS udemy_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT UNIQUE, order_ts TEXT,
  course_slug TEXT, coupon TEXT, currency TEXT, gross REAL, net REAL
);
CREATE INDEX IF NOT EXISTS idx_orders_ts ON udemy_orders(order_ts);
CREATE INDEX IF NOT EXISTS idx_orders_coupon_slug ON udemy_orders(coupon, course_slug);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.Lock()

    def initialize(self) -> None:
        with self.lock:
            self.connection.executescript(BASE_SCHEMA)

    def close(self) -> None:
        self.connection.close()
