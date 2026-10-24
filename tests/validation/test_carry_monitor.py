import importlib.util
import json
import os
import pathlib
import sys
import uuid
from datetime import datetime, timezone

import pytest

from src.lab.carry_monitor import DAY_MS, daily_average, is_open, parse_history, render_fa

H8 = 8 * 3_600_000
NOW = 1_800_000_000_000

SAMPLE = [{"id": "1", "symbol": "BTC-SWAP-USDT", "settleTime": "1792828800000", "settleRate": "0.00003538", "period": "8H"},
          {"id": "2", "symbol": "BTC-SWAP-USDT", "settleTime": "1792800000000", "settleRate": "0.00003926", "period": "8H"},
          {"id": "3", "symbol": "BTC-SWAP-USDT", "settleTime": "bad", "settleRate": "0.1"}]


def events(rate, count, end=NOW):
    return [end - k * H8 for k in range(count - 1, -1, -1)], [rate] * count


def test_parse_history_sorts_and_skips_bad_rows():
    times, rates = parse_history(SAMPLE)
    assert times == [1792800000000, 1792828800000]
    assert rates == [pytest.approx(0.00003926), pytest.approx(0.00003538)]
    with pytest.raises(ValueError):
        parse_history({"x": 1})


def test_daily_average_window_and_coverage():
    times, rates = events(0.0002, 30)                      # 10 days of 8h events at 0.0002
    assert daily_average(times, rates, NOW, 7) == pytest.approx(21 * 0.0002 / 7)
    assert daily_average(times, rates, NOW, 3) == pytest.approx(9 * 0.0002 / 3)
    short_t, short_r = events(0.0002, 10)                  # only 3.3 days of history
    assert daily_average(short_t, short_r, NOW, 7) is None
    assert daily_average([], [], NOW, 7) is None


def test_is_open_uses_the_registered_threshold():
    assert is_open(0.00045, 0.00045) is True
    assert is_open(0.00044, 0.00045) is False
    assert is_open(None, 0.00045) is False


def test_render_fa_lists_open_symbols_and_warnings():
    text = render_fa("2026-10-24 12:00", [("BTC", 0.0001, 0.0001, False), ("DOGE", 0.0007, 0.0006, True), ("DOT", None, None, False)],
                     0.00045, 7)
    assert "فرصت فعال: DOGE" in text and "DOT: داده‌ی کافی نیست" in text and "هشدارها" in text
    assert text.index("DOGE:") < text.index("BTC:")
    assert "فرصت فعال: ندارد" in render_fa("t", [("BTC", 0.0001, 0.0001, False)], 0.00045, 7)


def load_tool():
    path = pathlib.Path(__file__).resolve().parents[2] / "tools" / "carry_monitor.py"
    spec = importlib.util.spec_from_file_location("cm_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Bot:
    def __init__(self):
        self.sent = []

    def send_message(self, text):
        self.sent.append(text)


def test_tool_sends_only_on_change(tmp_path):
    tool = load_tool()
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"symbols": ["AAAUSDT", "BBBUSDT"], "entry_window_days": 7, "entry_daily_rate": 0.00045,
                               "exit_window_days": 3}))
    now = datetime.fromtimestamp(NOW / 1000, tz=timezone.utc)

    def make(rate_a):
        def opener(url, timeout=None):
            rate = rate_a if "AAA-" in url else 0.0001
            times, rates = events(rate, 40)
            return Resp([{"settleTime": str(t), "settleRate": str(r)} for t, r in zip(times, rates)])
        return opener

    state = str(tmp_path / "state.json")
    bot = Bot()
    assert tool.main(["--config", str(cfg), "--telegram"], make(0.0002), bot, now, state) == 0
    assert len(bot.sent) == 1 and "فرصت فعال: AAA" in bot.sent[0]          # AAA: 0.0006 per day >= 0.00045
    tool.main(["--config", str(cfg), "--telegram"], make(0.0002), bot, now, state)
    assert len(bot.sent) == 1                                                # no change, no message
    tool.main(["--config", str(cfg), "--telegram"], make(0.0001), bot, now, state)
    assert len(bot.sent) == 2 and "فرصت فعال: ندارد" in bot.sent[1]        # changed: closed
    tool.main(["--config", str(cfg), "--force"], make(0.0001), bot, now, state)
    assert len(bot.sent) == 3                                                # forced
