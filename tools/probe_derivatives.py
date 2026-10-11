"""
Falcon AI - probe the Binance USDT-M futures archives (read-only)

Checks, for each symbol, which monthly funding-rate files and which daily
"metrics" files (open interest, long/short ratios, taker buy/sell ratio) exist
on data.binance.vision, then downloads ONE sample of each and prints its
columns and a few rows so the time semantics can be checked before anything is
built on them. Nothing is written to the history database.

Usage: python tools/probe_derivatives.py [SYMBOLS]
       python tools/probe_derivatives.py BTCUSDT,ETHUSDT
"""

import csv
import datetime
import io
import sys
import urllib.error
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/futures/um"
SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
TIMEOUT = 30


def status(url):
    """HTTP status of a HEAD request, or the name of the error."""

    last = "error"

    for _ in range(2):
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except Exception as error:
            last = type(error).__name__

    return last


def fetch_rows(url):
    """Rows (lists of strings) of the first CSV inside a zip."""

    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        data = response.read()

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        name = archive.namelist()[0]
        text = archive.read(name).decode("utf-8")

    return name, list(csv.reader(io.StringIO(text)))


def month_list(first_year, first_month):

    today = datetime.date.today()
    year, month = first_year, first_month
    out = []

    while (year, month) <= (today.year, today.month):
        out.append((year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1

    return out


def summarize(label, found, checked, failures):

    if not found:
        print(f"  {label}: NONE found out of {checked} checked")
        return

    print(f"  {label}: {len(found)} of {checked} found, first {found[0]}, last {found[-1]}")

    if failures:
        print(f"  {label}: non-200 answers other than 404: {failures[:5]}")


def show_sample(title, name, rows):

    print(f"  sample {title}: {name}, {len(rows)} rows")

    for row in rows[:3]:
        print("    " + ",".join(row))

    if len(rows) > 3:
        print("    ...")
        print("    " + ",".join(rows[-1]))


def probe(symbol):

    print("=" * 70)
    print(symbol)

    # funding rate: one file per month
    funding_found, funding_other = [], []
    months = month_list(2019, 9)

    for year, month in months:
        tag = f"{year}-{month:02d}"
        code = status(f"{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{tag}.zip")
        if code == 200:
            funding_found.append(tag)
        elif code != 404:
            funding_other.append((tag, code))

    summarize("funding (monthly)", funding_found, len(months), funding_other)

    if funding_found:
        tag = funding_found[-2] if len(funding_found) > 1 else funding_found[-1]
        url = f"{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{tag}.zip"
        try:
            name, rows = fetch_rows(url)
            show_sample("funding", name, rows)
        except Exception as error:
            print(f"  sample funding failed: {type(error).__name__}: {error}")

    # metrics: one file per day; sample the 2nd day of every month
    metrics_found, metrics_other = [], []
    months = month_list(2020, 1)

    for year, month in months:
        tag = f"{year}-{month:02d}-02"
        code = status(f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{tag}.zip")
        if code == 200:
            metrics_found.append(tag)
        elif code != 404:
            metrics_other.append((tag, code))

    summarize("metrics (daily, sampled on day 2 of each month)", metrics_found, len(months), metrics_other)

    if metrics_found:
        tag = metrics_found[-2] if len(metrics_found) > 1 else metrics_found[-1]
        url = f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{tag}.zip"
        try:
            name, rows = fetch_rows(url)
            show_sample("metrics", name, rows)
        except Exception as error:
            print(f"  sample metrics failed: {type(error).__name__}: {error}")


def main():

    print(f"probe of {BASE} on {datetime.date.today()}")

    for symbol in SYMBOLS:
        probe(symbol)

    print("=" * 70)
    print("DONE")


main()
