import importlib.util
import os
import pathlib
import uuid
from datetime import datetime, timezone

import pytest

from src.notify.commands import HELP_FA, parse_command

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

SHEET_LOG = """BTCUSDT: candles +25
  sheets: added 1
برگه‌ی ریسک BTCUSDT (1h)
زمان: 2026-10-24 12:00 UTC | قیمت: 83,248
جهت قیمت پیش‌بینی نمی‌شود. عدد ۹۵٪ معتبرتر از ۸۰٪ است.

DONE
"""


def load_tool():
    path = pathlib.Path(__file__).resolve().parents[2] / "tools" / "telegram_bot.py"
    spec = importlib.util.spec_from_file_location("tb_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bot:
    def __init__(self, updates, chat_id="42"):
        self.updates = updates
        self.chat_id = chat_id
        self.sent = []
        self.docs = []
        self.offsets = []

    def get_updates(self, offset=None):
        self.offsets.append(offset)
        return self.updates

    def send_message(self, text):
        self.sent.append(text)

    def send_document(self, path, caption=""):
        self.docs.append(os.path.basename(path))


def upd(uid, text, chat=42):
    return {"update_id": uid, "message": {"chat": {"id": chat}, "text": text}}


def test_parse_command():
    assert parse_command("/Sheet@falcon_bot now") == "sheet"
    assert parse_command("  /help") == "help"
    assert parse_command("سلام") is None and parse_command("") is None and parse_command(None) is None
    assert parse_command("/") is None


def test_ignores_other_chats_and_plain_text_but_advances_offset(tmp_path):
    tool = load_tool()
    bot = Bot([upd(10, "/help", chat=999), upd(11, "hello"), upd(12, "/help")])
    off = tmp_path / "off"
    assert tool.main([], bot, lambda a: "", NOW, str(off), str(tmp_path / "log"), str(tmp_path)) == 0
    assert bot.sent == [HELP_FA]
    assert off.read_text() == "13"
    bot2 = Bot([])
    tool.main([], bot2, lambda a: "", NOW, str(off), str(tmp_path / "log"), str(tmp_path))
    assert bot2.offsets == [13]


def test_sheet_report_carry_use_the_right_tools(tmp_path):
    tool = load_tool()
    calls = []

    def runner(args):
        calls.append(args[0])
        return SHEET_LOG if "forward_log" in args[0] else "OUTPUT " + args[0]
    bot = Bot([upd(1, "/sheet"), upd(2, "/report"), upd(3, "/carry")])
    tool.main([], bot, runner, NOW, str(tmp_path / "off"), str(tmp_path / "log"), str(tmp_path))
    assert calls == ["tools/forward_log.py", "tools/forward_report.py", "tools/carry_monitor.py"]
    assert "برگه‌ی ریسک BTCUSDT" in bot.sent[0] and "candles" not in bot.sent[0]
    assert bot.sent[1] == "OUTPUT tools/forward_report.py" and bot.sent[2] == "OUTPUT tools/carry_monitor.py"


def test_status_reads_last_forward_run_line(tmp_path):
    tool = load_tool()
    log = tmp_path / "log"
    log.write_text("forward run at 2026-10-23 09:36 UTC, symbols A\nx\nforward run at 2026-10-24 06:00 UTC, symbols A\n")
    bot = Bot([upd(1, "/status")])
    tool.main([], bot, lambda a: "", NOW, str(tmp_path / "off"), str(log), str(tmp_path))
    assert "2026-10-24 06:00 UTC" in bot.sent[0] and "2026-10-23" not in bot.sent[0]
    bot2 = Bot([upd(2, "/status")])
    tool.main([], bot2, lambda a: "", NOW, str(tmp_path / "off2"), str(tmp_path / "missing"), str(tmp_path))
    assert "پیدا نشد" in bot2.sent[0]


def test_excel_sends_csv_files(tmp_path):
    tool = load_tool()
    folder = tmp_path / "research" / "forward"
    folder.mkdir(parents=True)
    (folder / "sheets_BTCUSDT_1h.csv").write_text("a\n")
    (folder / "sheets_ETHUSDT_1h.csv").write_text("a\n")
    bot = Bot([upd(1, "/excel")])
    tool.main([], bot, lambda a: "", NOW, str(tmp_path / "off"), str(tmp_path / "log"), str(tmp_path))
    assert bot.docs == ["sheets_BTCUSDT_1h.csv", "sheets_ETHUSDT_1h.csv"]
    bot2 = Bot([upd(2, "/excel")])
    tool.main([], bot2, lambda a: "", NOW, str(tmp_path / "off2"), str(tmp_path / "log"), str(tmp_path / "empty"))
    assert "فایلی پیدا نشد" in bot2.sent[0]


def test_runner_error_is_reported_and_offset_still_advances(tmp_path):
    tool = load_tool()

    def boom(args):
        raise RuntimeError("x")
    bot = Bot([upd(5, "/carry")])
    off = tmp_path / "off"
    assert tool.main([], bot, boom, NOW, str(off), str(tmp_path / "log"), str(tmp_path)) == 0
    assert "خطا در اجرای /carry" in bot.sent[0] and off.read_text() == "6"


def test_telegram_failure_returns_error_without_touching_offset(tmp_path):
    tool = load_tool()
    from src.notify.telegram import TelegramError

    class Down(Bot):
        def get_updates(self, offset=None):
            raise TelegramError("down")
    off = tmp_path / "off"
    assert tool.main([], Down([]), lambda a: "", NOW, str(off), str(tmp_path / "log"), str(tmp_path)) == 1
    assert not off.exists()
