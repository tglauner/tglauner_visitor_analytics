import json

from collector.database import Database
from collector.importer.udemy_csv_importer import parse_udemy_csv
from collector.reporting_filters import ReportingFilterLoader


def test_database_initialize_is_idempotent(tmp_path):
    db = Database(tmp_path / "db.sqlite3")
    db.initialize()
    db.initialize()
    tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    db.close()
    assert {"events_raw", "udemy_orders"}.issubset(tables)


def test_reporting_filter_reads_structured_ips(tmp_path):
    path = tmp_path / "filters.json"
    path.write_text(json.dumps({"exclude": {"ip_addresses": ["1.2.3.4", {"ip": "5.6.7.8"}]}}))
    assert ReportingFilterLoader(path).excluded_ips() == ["1.2.3.4", "5.6.7.8"]


def test_reporting_filter_deduplicates_ips(tmp_path):
    path = tmp_path / "filters.json"
    path.write_text('["1.2.3.4", "1.2.3.4"]')
    assert ReportingFilterLoader(path).excluded_ips() == ["1.2.3.4"]


def test_reporting_filter_sql_fragment(tmp_path):
    path = tmp_path / "filters.json"
    path.write_text('["1.2.3.4"]')
    clause, params = ReportingFilterLoader(path).sql_fragment("client_ip")
    assert "client_ip NOT IN (?)" in clause
    assert params == ("1.2.3.4",)


def test_udemy_csv_parses_values():
    rows = parse_udemy_csv(b"Order ID,Purchase Date,Course,Coupon Code,Currency,Gross Amount,Net Amount (Instructor Share)\n1,2026-01-02,My Course,SAVE,USD,$10.00,$5.50\n")
    assert rows[0] == ("1", "2026-01-02T00:00:00", "my-course", "SAVE", "USD", 10.0, 5.5)


def test_udemy_csv_skips_missing_order_id():
    rows = parse_udemy_csv(b"Order ID,Purchase Date,Course\n,2026-01-02,My Course\n")
    assert rows == []


def test_udemy_csv_skips_invalid_date():
    rows = parse_udemy_csv(b"Order ID,Purchase Date,Course\n1,not-a-date,My Course\n")
    assert rows == []
