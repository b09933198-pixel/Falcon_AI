import datetime

import importlib.util
import os

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools", "daily.py")
_spec = importlib.util.spec_from_file_location("falcon_daily", _p)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_message, extract_sheets, extract_summary, main = (
    _mod.build_message, _mod.extract_sheets, _mod.extract_summary, _mod.main)

LOG = """forward run at 2026-10-21 09:36 UTC, symbols BTCUSDT,ETHUSDT

======================================================================
BTCUSDT: candles +25 (mismatches 0), newest closed candle 2026-10-21 08:00 UTC
  sheets: added 24, already there 0, refused late 0, no history 0
  outcomes: filled 24, void 0, still open 24

برگه‌ی ریسک BTCUSDT (1h)
زمان: 2026-10-21 09:00 UTC | قیمت: 83,248
• با احتمال 95٪ بیشتر از 4.82٪ (حدود 4,010) نمی‌شود
جهت قیمت پیش‌بینی نمی‌شود. عدد ۹۵٪ معتبرتر از ۸۰٪ است.

======================================================================
ETHUSDT: candles +25 (mismatches 0), newest closed candle 2026-10-21 08:00 UTC
  sheets: added 24, already there 0, refused late 0, no history 0

برگه‌ی ریسک ETHUSDT (1h)
زمان: 2026-10-21 09:00 UTC | قیمت: 2,454
جهت قیمت پیش‌بینی نمی‌شود. عدد ۹۵٪ معتبرتر از ۸۰٪ است.

DONE
"""
NOW = datetime.datetime(2026, 10, 21, 9, 40)


class Bot:
    def __init__(self):
        self.sent = []

    def send_message(self, t):
        self.sent.append(t)


def test_extract_sheets_and_summary():
    s = extract_sheets(LOG)
    assert len(s) == 2 and s[0].startswith("برگه‌ی ریسک BTCUSDT") and "ETHUSDT" in s[1]
    assert "candles" not in s[0] and "outcomes" not in s[0]
    sm = extract_summary(LOG)
    assert sm[0].startswith("BTCUSDT sheets: added 24") and len(sm) == 2


def test_build_message():
    text, n = build_message(LOG, NOW)
    assert n == 2 and text.startswith("Falcon | 2026-10-21 09:40 UTC")


def test_main_success_sends_message():
    bot = Bot()
    calls = []

    def runner(a):
        calls.append(a[0])
        return 0, LOG
    assert main([], bot, runner, NOW) == 0
    assert calls == ["tools/forward_log.py", "tools/export_forward.py"]
    assert len(bot.sent) == 1 and "برگه‌ی ریسک BTCUSDT" in bot.sent[0]


def test_main_failure_alerts_and_stops():
    bot = Bot()
    calls = []

    def runner(a):
        calls.append(a[0])
        return 1, "boom"
    assert main([], bot, runner, NOW) == 1
    assert calls == ["tools/forward_log.py"]
    assert bot.sent[0].startswith("Falcon: daily run FAILED")


def test_missing_done_marker_is_failure():
    bot = Bot()
    assert main([], bot, lambda a: (0, "no marker"), NOW) == 1


def test_telegram_failure_is_not_fatal():
    class Broken:
        def send_message(self, t):
            raise RuntimeError("no route")
    assert main([], Broken(), lambda a: (0, LOG), NOW) == 0
