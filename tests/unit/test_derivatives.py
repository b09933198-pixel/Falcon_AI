"""
Tests for the derivatives data layer (parsing, download guards, storage).

The network is never touched: urlopen is replaced by a fake.
"""

import io
import tempfile
import urllib.error
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from src.data import derivatives as d
from src.data.derivatives import (
    DerivativesError,
    DerivativesStore,
    FUNDING_HEADER,
    METRICS_HEADER,
    fetch_zip_csv,
    parse_funding,
    parse_metrics,
    utc_ms,
)


def raises(call, error=DerivativesError):
    try:
        call()
    except error:
        return True
    return False


def metrics_row(stamp, symbol="BTCUSDT", oi="10.5", taker="1.25"):
    return [stamp, symbol, oi, "1000.0", "1.1", "1.2", "1.3", taker]


# ---------------- time ----------------

def test_utc_ms_known_values():
    assert utc_ms("1970-01-02 00:00:00") == 86_400_000
    assert utc_ms("2021-01-01 00:00:00") == 1_609_459_200_000
    assert utc_ms("2021-01-01 00:05:00") == 1_609_459_500_000
    assert raises(lambda: utc_ms("2021-01-01"))
    assert raises(lambda: utc_ms("not a date"))


# ---------------- funding ----------------

def test_parse_funding_reads_rows_in_file_order():
    rows = [FUNDING_HEADER, ["1785571200000", "8", "0.0001"], ["1785542400001", "8", "-0.00002"]]
    assert parse_funding(rows) == [(1785571200000, 8, 0.0001), (1785542400001, 8, -0.00002)]


def test_parse_funding_rejects_bad_input():
    good = ["1", "8", "0.1"]
    assert raises(lambda: parse_funding([]))
    assert raises(lambda: parse_funding([["a", "b", "c"], good]))
    assert raises(lambda: parse_funding([FUNDING_HEADER, ["1", "8"]]))
    assert raises(lambda: parse_funding([FUNDING_HEADER, ["x", "8", "0.1"]]))
    assert raises(lambda: parse_funding([FUNDING_HEADER, ["1", "8", ""]]))
    assert raises(lambda: parse_funding([FUNDING_HEADER, ["1", "8", "nan"]]))
    assert raises(lambda: parse_funding([FUNDING_HEADER, ["1", "0", "0.1"]]))


# ---------------- metrics ----------------

def test_parse_metrics_keeps_unsorted_rows_and_handles_empty_numbers():
    rows = [
        METRICS_HEADER,
        metrics_row("2026-09-02 01:50:00"),
        metrics_row("2026-09-02 00:30:00", oi=""),
    ]
    out = parse_metrics(rows, "BTCUSDT")
    assert [r[0] for r in out] == [utc_ms("2026-09-02 01:50:00"), utc_ms("2026-09-02 00:30:00")]
    assert out[0][1] == 10.5 and out[1][1] is None
    assert out[0][-1] == 1.25


def test_parse_metrics_rejects_bad_input():
    assert raises(lambda: parse_metrics([], "BTCUSDT"))
    assert raises(lambda: parse_metrics([["x"]], "BTCUSDT"))
    assert raises(lambda: parse_metrics([METRICS_HEADER, metrics_row("2026-09-02 00:00:00", symbol="ETHUSDT")], "BTCUSDT"))
    assert raises(lambda: parse_metrics([METRICS_HEADER, ["2026-09-02 00:00:00", "BTCUSDT", "1"]], "BTCUSDT"))
    assert raises(lambda: parse_metrics([METRICS_HEADER, metrics_row("2026-09-02 00:00:00", oi="abc")], "BTCUSDT"))
    assert raises(lambda: parse_metrics([METRICS_HEADER, metrics_row("bad")], "BTCUSDT"))


# ---------------- download ----------------

def zipped(text, name="data.csv"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def read(self, limit=-1):
        return self._data if limit < 0 else self._data[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@contextmanager
def fake_network(handler):
    with mock.patch.object(d.urllib.request, "urlopen", side_effect=handler):
        yield


def test_fetch_zip_csv_returns_rows_and_none_for_404():
    def handler(url, timeout=0):
        if "missing" in url:
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        return FakeResponse(zipped("a,b\n1,2\n"))

    with fake_network(handler):
        assert fetch_zip_csv("http://x/present.zip") == [["a", "b"], ["1", "2"]]
        assert fetch_zip_csv("http://x/missing.zip") is None


def test_fetch_zip_csv_other_errors_propagate():
    def handler(url, timeout=0):
        raise urllib.error.HTTPError(url, 500, "boom", {}, None)

    with fake_network(handler):
        assert raises(lambda: fetch_zip_csv("http://x/a.zip"), urllib.error.HTTPError)


def test_fetch_zip_csv_guards_against_odd_archives():
    big = zipped("x" * 100)

    with mock.patch.object(d, "MAX_ZIP_BYTES", 50):
        with fake_network(lambda url, timeout=0: FakeResponse(big)):
            assert raises(lambda: fetch_zip_csv("http://x/a.zip"))

    with mock.patch.object(d, "MAX_CSV_BYTES", 10):
        with fake_network(lambda url, timeout=0: FakeResponse(big)):
            assert raises(lambda: fetch_zip_csv("http://x/a.zip"))

    two = io.BytesIO()
    with zipfile.ZipFile(two, "w") as archive:
        archive.writestr("a.csv", "1")
        archive.writestr("b.csv", "2")

    with fake_network(lambda url, timeout=0: FakeResponse(two.getvalue())):
        assert raises(lambda: fetch_zip_csv("http://x/a.zip"))


def test_urls():
    assert d.funding_url("BTCUSDT", "2024-01").endswith("/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2024-01.zip")
    assert d.metrics_url("ETHUSDT", "2024-01-02").endswith("/daily/metrics/ETHUSDT/ETHUSDT-metrics-2024-01-02.zip")


# ---------------- storage ----------------

def test_store_is_idempotent_sorted_and_tracks_downloads():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "sub" / "x.db"

        with DerivativesStore(path) as store:
            rows = parse_metrics(
                [METRICS_HEADER, metrics_row("2021-01-01 00:10:00"), metrics_row("2021-01-01 00:05:00"),
                 metrics_row("2021-01-01 00:07:00")], "BTCUSDT")
            store.add_metrics("BTCUSDT", rows)
            store.add_metrics("BTCUSDT", rows)
            store.add_funding("BTCUSDT", [(2, 8, 0.2), (1, 8, 0.1)])
            store.add_funding("BTCUSDT", [(1, 8, 0.1)])

            assert not store.done("metrics", "BTCUSDT", "2021-01-01")
            store.mark("metrics", "BTCUSDT", "2021-01-01", 3)
            store.mark("funding", "BTCUSDT", "2020-01", -1)
            assert store.done("metrics", "BTCUSDT", "2021-01-01")

        with DerivativesStore(path) as store:
            stamps = [r[0] for r in store.metrics("BTCUSDT")]
            assert stamps == sorted(stamps) and len(stamps) == 3
            assert [r[0] for r in store.funding("BTCUSDT")] == [1, 2]
            assert store.metrics("ETHUSDT") == []

            summary = store.summary("BTCUSDT")
            assert summary["metric_rows"] == 3 and summary["off_grid"] == 1
            assert summary["days"] == 1 and summary["short_days"][0][1] == 3
            assert summary["funding_rows"] == 2 and summary["intervals"] == {8: 2}
            assert summary["missing_files"] == {"funding": 1}


def test_store_replaces_a_row_with_the_same_key():
    with tempfile.TemporaryDirectory() as folder:
        with DerivativesStore(Path(folder) / "x.db") as store:
            store.add_funding("BTCUSDT", [(1, 8, 0.1)])
            store.add_funding("BTCUSDT", [(1, 8, 0.9)])
            assert store.funding("BTCUSDT") == [(1, 8, 0.9)]
