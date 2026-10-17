"""
Tests for the sheet-log CSV export.
"""

import csv
import io

from src.forward.export import COLUMNS, sheets_csv

HOUR = 3_600_000


def row(decision, outcome=None, void=0):
    return {
        "decision_open_ms": decision, "created_ms": decision + 5 * HOUR, "model_id": "BTCUSDT-1h-20261017",
        "expected": 0.0048123456789, "q50": 0.0185, "q80": 0.0319, "q95": 0.0539, "rank": 0.21, "level": "low",
        "outcome": outcome, "outcome_ms": None if outcome is None else decision + 30 * HOUR, "void": void,
    }


def parse(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_header_rows_and_sorting():
    text = sheets_csv("BTCUSDT", "1h", [row(1792188000000), row(1792184400000)])
    lines = text.splitlines()
    assert lines[0] == ",".join(COLUMNS)
    rows = parse(text)
    assert [r["decision_open_ms"] for r in rows] == ["1792184400000", "1792188000000"]
    assert rows[1]["decision_utc"] == "2026-10-16 22:00" and rows[1]["created_utc"] == "2026-10-17 03:00"
    assert rows[0]["symbol"] == "BTCUSDT" and rows[0]["interval"] == "1h" and rows[0]["level"] == "low"


def test_floats_round_trip_exactly_and_missing_values_are_empty():
    rows = parse(sheets_csv("BTCUSDT", "1h", [row(1792184400000), row(1792188000000, outcome=0.0234567891234)]))
    assert float(rows[0]["expected"]) == 0.0048123456789 and float(rows[0]["q95"]) == 0.0539
    assert rows[0]["outcome"] == "" and rows[0]["outcome_ms"] == "" and rows[0]["void"] == "0"
    assert float(rows[1]["outcome"]) == 0.0234567891234 and rows[1]["void"] == "0"


def test_void_rows_and_empty_log():
    rows = parse(sheets_csv("ETHUSDT", "1h", [row(1792184400000, void=1)]))
    assert rows[0]["void"] == "1" and rows[0]["outcome"] == ""
    assert sheets_csv("ETHUSDT", "1h", []) == ",".join(COLUMNS) + "\n"


def test_export_is_deterministic():
    data = [row(1792188000000), row(1792184400000, outcome=0.02)]
    assert sheets_csv("BTCUSDT", "1h", data) == sheets_csv("BTCUSDT", "1h", list(reversed(data)))
