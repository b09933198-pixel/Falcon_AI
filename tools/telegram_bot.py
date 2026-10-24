"""Answers Telegram commands once and exits (run by cron every few minutes).

Only the chat saved by tools/telegram_setup.py is answered; every other chat is ignored.
"""

import glob
import importlib.util
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from src.notify.commands import HELP_FA, parse_command  # noqa: E402
from src.notify.telegram import Telegram, TelegramError, load_credentials  # noqa: E402

HOME = os.path.expanduser("~")
OFFSET = os.path.join(HOME, ".falcon_tg_offset")
LOG = os.path.join(HOME, "falcon_cron.log")


def run_tool(args, timeout=150):
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return (p.stdout or "") + (p.stderr or "")


def load_daily():
    spec = importlib.util.spec_from_file_location("falcon_daily_tool", os.path.join(ROOT, "tools", "daily.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def status_text(log_path, now):
    last = None
    try:
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("forward run at"):
                    last = line.strip()
    except OSError:
        pass
    return f"فالکون فعال است | {now:%Y-%m-%d %H:%M} UTC\nآخرین اجرای ثبت: " + (last or "در لاگ پیدا نشد")


def reply(command, bot, runner, log_path, now, root):
    if command in ("start", "help"):
        bot.send_message(HELP_FA)
    elif command == "sheet":
        sheets = load_daily().extract_sheets(runner(["tools/forward_log.py"]))
        bot.send_message("\n\n".join(sheets) if sheets else "برگه‌ای پیدا نشد؛ لاگ را بررسی کنید.")
    elif command == "report":
        bot.send_message(runner(["tools/forward_report.py"]).strip() or "گزارشی تولید نشد.")
    elif command == "carry":
        bot.send_message(runner(["tools/carry_monitor.py"]).strip() or "مانیتور خروجی نداد.")
    elif command == "status":
        bot.send_message(status_text(log_path, now))
    elif command == "excel":
        files = sorted(glob.glob(os.path.join(root, "research", "forward", "**", "*.csv"), recursive=True))
        if not files:
            bot.send_message("فایلی پیدا نشد؛ ابتدا ثبت روزانه را اجرا کنید.")
        failed = []
        for path in files:
            for attempt in (1, 2):
                try:
                    bot.send_document(path, os.path.basename(path))
                    break
                except TelegramError:
                    if attempt == 2:
                        failed.append(os.path.basename(path))
        if failed:
            bot.send_message("ارسال این فایل‌ها ناموفق بود: " + ", ".join(failed) + " (دوباره /excel بزنید)")
    else:
        bot.send_message(HELP_FA)


def main(argv=None, bot=None, runner=run_tool, now=None, offset_path=OFFSET, log_path=LOG, root=ROOT):
    now = now or datetime.now(timezone.utc)

    if bot is None:
        token, chat = load_credentials()
        if not token or not chat:
            print("Telegram not configured: run tools/telegram_setup.py first.")
            return 1
        bot = Telegram(token, chat)

    try:
        with open(offset_path, encoding="utf-8") as handle:
            offset = int(handle.read().strip())
    except (OSError, ValueError):
        offset = None

    try:
        updates = bot.get_updates(offset)
    except TelegramError as error:
        print("Telegram error:", error)
        return 1

    last = None
    for update in updates:
        last = update["update_id"]
        message = update.get("message") or {}
        if str(message.get("chat", {}).get("id")) != str(bot.chat_id):
            continue
        command = parse_command(message.get("text"))
        if command is None:
            continue
        try:
            reply(command, bot, runner, log_path, now, root)
        except Exception as error:
            try:
                bot.send_message(f"خطا در اجرای /{command}: {type(error).__name__}")
            except Exception:
                pass

    if last is not None:
        with open(offset_path, "w", encoding="utf-8") as handle:
            handle.write(str(last + 1))

    return 0


if __name__ == "__main__":
    sys.exit(main())
