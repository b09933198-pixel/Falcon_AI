"""Falcon AI - compare Toobit vs Binance 1h candles (stdlib only, read-only)."""

import io
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
import zipfile

TOOBIT = "https://api.toobit.com/quote/v1/klines"
VISION = "https://data.binance.vision/data"
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
MONTHS = ["2026-06", "2026-07", "2026-08"]
HOUR = 3600000


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FalconAI-compare"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def toobit_1h(symbol):
    rows = {}
    end = None
    prev = None
    for _ in range(6):
        params = {"symbol": symbol, "interval": "1h", "limit": 1000}
        if end is not None:
            params["endTime"] = end
        page = json.loads(get(TOOBIT + "?" + urllib.parse.urlencode(params)))
        if not page:
            break
        for r in page:
            rows[int(r[0])] = tuple(float(x) for x in (r[1], r[2], r[3], r[4], r[5]))
        oldest = min(int(r[0]) for r in page)
        if prev is not None and oldest >= prev:
            break
        prev = oldest
        end = oldest - 1
        time.sleep(0.3)
    return rows


def vision_month(market, symbol, month):
    folder = "futures/um" if market == "futures" else "spot"
    url = f"{VISION}/{folder}/monthly/klines/{symbol}/1h/{symbol}-1h-{month}.zip"
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    rows = {}
    for line in z.read(z.namelist()[0]).decode().splitlines():
        p = line.split(",")
        if not p[0].isdigit():
            continue
        ts = int(p[0])
        if ts > 10**14:
            ts //= 1000
        rows[ts] = tuple(float(x) for x in (p[1], p[2], p[3], p[4], p[5]))
    return rows


def pct(a, b):
    return abs(a - b) / b * 100.0


def p95(values):
    return sorted(values)[int(0.95 * (len(values) - 1))]


def compare(name, tb, bn):
    common = sorted(set(tb) & set(bn))
    print(f"== {name} ==")
    if len(common) < 10:
        print("not enough matching candles:", len(common))
        return
    close_d = [pct(tb[t][3], bn[t][3]) for t in common]
    high_d = [pct(tb[t][1], bn[t][1]) for t in common]
    low_d = [pct(tb[t][2], bn[t][2]) for t in common]
    same = sum(1 for t in common if (tb[t][3] >= tb[t][0]) == (bn[t][3] >= bn[t][0]))
    vol = [tb[t][4] / bn[t][4] for t in common if bn[t][4] > 0]
    tr, br = [], []
    for a, b in zip(common, common[1:]):
        if b - a == HOUR:
            tr.append(tb[b][3] / tb[a][3] - 1)
            br.append(bn[b][3] / bn[a][3] - 1)
    corr = statistics.correlation(tr, br) if len(tr) > 10 else float("nan")
    print(f"matched candles     : {len(common)}")
    print(f"close diff % mean   : {statistics.mean(close_d):.4f}  p95: {p95(close_d):.4f}  max: {max(close_d):.4f}")
    print(f"high diff % mean    : {statistics.mean(high_d):.4f}")
    print(f"low diff % mean     : {statistics.mean(low_d):.4f}")
    print(f"same direction %    : {same / len(common) * 100:.2f}")
    print(f"return correlation  : {corr:.5f}")
    print(f"volume ratio median : {statistics.median(vol):.3f}  (Toobit / Binance)")


def main():
    tb = toobit_1h(SYMBOL)
    print(f"Toobit candles loaded: {len(tb)}")
    for market in ("futures", "spot"):
        bn = {}
        for month in MONTHS:
            try:
                bn.update(vision_month(market, SYMBOL, month))
            except Exception as exc:
                print(f"{market} {month} failed: {exc}")
        compare(market, tb, bn)
    print("DONE")


main()
