"""
Falcon AI - download funding rates and futures metrics (resumable)

Fetches, from data.binance.vision, for each symbol:
  - monthly funding-rate files
  - daily metrics files (open interest, long/short ratios, taker buy/sell ratio)
into data/history/derivatives.db. Files already stored are skipped, so the tool
can be stopped and started again at any time. A summary of the coverage is
printed at the end.

Usage: python tools/download_derivatives.py [SYMBOLS]
       python tools/download_derivatives.py BTCUSDT,ETHUSDT
"""

import datetime
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.derivatives import (  # noqa: E402
    DerivativesError,
    DerivativesStore,
    fetch_zip_csv,
    funding_url,
    metrics_url,
    parse_funding,
    parse_metrics,
)

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]

FUNDING_START = (2019, 9)
METRICS_START = {"BTCUSDT": datetime.date(2020, 9, 1), "ETHUSDT": datetime.date(2021, 12, 1)}
DEFAULT_METRICS_START = datetime.date(2020, 9, 1)

WORKERS = 6
RETRIES = 3
RECENT_DAYS = 3          # a 404 on a very recent day is not final


def tasks_for(symbol, store, today):

    out = []
    year, month = FUNDING_START

    while (year, month) < (today.year, today.month):
        tag = f"{year}-{month:02d}"
        if not store.done("funding", symbol, tag):
            out.append(("funding", symbol, tag, funding_url(symbol, tag)))
        month += 1
        if month == 13:
            year, month = year + 1, 1

    day = METRICS_START.get(symbol, DEFAULT_METRICS_START)

    while day < today:
        tag = day.isoformat()
        if not store.done("metrics", symbol, tag):
            out.append(("metrics", symbol, tag, metrics_url(symbol, tag)))
        day += datetime.timedelta(days=1)

    return out


def work(task):
    """Download and parse one file. Returns (task, status, parsed)."""

    kind, symbol, tag, url = task
    last = "error"

    for attempt in range(RETRIES):

        try:
            rows = fetch_zip_csv(url)

            if rows is None:
                return task, "missing", None

            parsed = parse_funding(rows) if kind == "funding" else parse_metrics(rows, symbol)

            return task, "ok", parsed

        except DerivativesError as error:
            return task, f"invalid: {error}", None
        except Exception as error:
            last = f"{type(error).__name__}"
            time.sleep(1.5 * (attempt + 1))

    return task, f"failed: {last}", None


def main():

    today = datetime.date.today()
    started = time.time()

    with DerivativesStore() as store:

        tasks = []

        for symbol in SYMBOLS:
            tasks.extend(tasks_for(symbol, store, today))

        print(f"{len(tasks)} files to fetch for {','.join(SYMBOLS)} ({WORKERS} at a time)")

        stored = missing = 0
        problems = []

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:

            futures = [pool.submit(work, t) for t in tasks]

            for number, future in enumerate(as_completed(futures), 1):

                (kind, symbol, tag, _), status, parsed = future.result()

                if status == "ok":
                    if kind == "funding":
                        store.add_funding(symbol, parsed)
                    else:
                        store.add_metrics(symbol, parsed)
                    store.mark(kind, symbol, tag, len(parsed))
                    stored += 1

                elif status == "missing":
                    recent = kind == "metrics" and (today - datetime.date.fromisoformat(tag)).days <= RECENT_DAYS
                    if not recent:
                        store.mark(kind, symbol, tag, -1)
                    missing += 1

                else:
                    problems.append((kind, symbol, tag, status))

                if number % 100 == 0:
                    store.commit()
                    print(f"  {number}/{len(tasks)} done, {time.time() - started:.0f}s")

            store.commit()

        print()
        print(f"stored {stored}, missing {missing}, problems {len(problems)}, {time.time() - started:.0f}s")

        for problem in problems[:10]:
            print("  problem:", problem)

        print()
        print("=" * 70)

        for symbol in SYMBOLS:

            s = store.summary(symbol)

            def when(ms):
                return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M") if ms else "-"

            print(symbol)
            print(f"  metrics: {s['metric_rows']} rows over {s['days']} days, {when(s['metric_first'])} .. {when(s['metric_last'])}")
            print(f"           timestamps off the 5-minute grid: {s['off_grid']}")
            print(f"           days without exactly 288 rows: {len(s['short_days'])}")
            for day, count in s["short_days"][:5]:
                print(f"             {datetime.date.fromordinal(day + 719163).isoformat()}: {count} rows")
            print(f"  funding: {s['funding_rows']} rows, {when(s['funding_first'])} .. {when(s['funding_last'])}, intervals (hours): {s['intervals']}")
            print(f"  files that do not exist: {s['missing_files']}")

        print("=" * 70)
        print("DONE" if not problems else "DONE WITH PROBLEMS - run again to retry them")


main()
