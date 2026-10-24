"""Funding-opportunity monitor (F-013 rule) on live Toobit funding history.

  python tools/carry_monitor.py              # print
  python tools/carry_monitor.py --telegram   # also send when the set of open symbols changed
  python tools/carry_monitor.py --force      # also send now, changed or not

Not a directional signal and not an instruction to trade.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from src.lab.carry_monitor import daily_average, is_open, parse_history, render_fa  # noqa: E402

URL = "https://api.toobit.com/api/v1/futures/historyFundingRate?symbol={symbol}&limit=80"
STATE = os.path.join(os.path.expanduser("~"), ".falcon_carry_state.json")


def fetch(symbol, opener=None):
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    url = URL.format(symbol=f"{base}-SWAP-USDT")
    with (opener or urllib.request.urlopen)(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv=None, opener=None, bot=None, now=None, state_path=STATE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "carry_f013.json"))
    ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)

    now = now or datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    rows = []

    for symbol in config["symbols"]:
        try:
            times, rates = parse_history(fetch(symbol, opener))
        except Exception as error:
            print(f"{symbol}: no data ({type(error).__name__})")
            rows.append((symbol[:-4], None, None, False))
            continue
        d_in = daily_average(times, rates, now_ms, config["entry_window_days"])
        d_out = daily_average(times, rates, now_ms, config["exit_window_days"])
        rows.append((symbol[:-4], d_in, d_out, is_open(d_in, config["entry_daily_rate"])))

    text = render_fa(now.strftime("%Y-%m-%d %H:%M"), rows, config["entry_daily_rate"], config["entry_window_days"])
    print(text)

    if args.telegram or args.force:
        current = sorted(r[0] for r in rows if r[3])
        try:
            with open(state_path, encoding="utf-8") as handle:
                previous = json.load(handle)
        except Exception:
            previous = []
        if args.force or current != previous:
            if bot is None:
                from src.notify.telegram import Telegram, load_credentials
                token, chat = load_credentials()
                bot = Telegram(token, chat) if token and chat else None
            try:
                if bot is None:
                    raise RuntimeError("Telegram not configured")
                bot.send_message(text)
                with open(state_path, "w", encoding="utf-8") as handle:
                    json.dump(current, handle)
            except Exception as error:
                print("Telegram send failed:", error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
