"""Daily routine: log sheets, export CSV, send risk sheets to Telegram, optionally commit and push.

  python tools/daily.py            # log + export + Telegram
  python tools/daily.py --git      # also commit and push research/forward
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

SHEET_START = "برگه‌ی ریسک"
SHEET_END = "جهت قیمت پیش‌بینی نمی‌شود"
SYMBOL_LINE = re.compile(r"^(\w+): candles")


def extract_sheets(text):
    sheets, cur = [], None
    for line in text.splitlines():
        if cur is None and SHEET_START in line:
            cur = [line.strip()]
        elif cur is not None:
            cur.append(line.rstrip())
            if SHEET_END in line:
                sheets.append("\n".join(cur).strip())
                cur = None
    return sheets


def extract_summary(text):
    out, symbol = [], None
    for line in text.splitlines():
        m = SYMBOL_LINE.match(line.strip())
        if m:
            symbol = m.group(1)
        elif line.strip().startswith("sheets:") and symbol:
            out.append("%s %s" % (symbol, line.strip()))
    return out


def build_message(text, now):
    sheets = extract_sheets(text)
    head = "Falcon | %s UTC" % now.strftime("%Y-%m-%d %H:%M")
    parts = [head] + extract_summary(text)
    return "\n".join(parts) + "\n\n" + "\n\n".join(sheets), len(sheets)


def run(args):
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def safe_send(bot, text):
    """Telegram problems must never stop data logging or the git commit."""
    try:
        bot.send_message(text)
    except Exception as e:
        print("Telegram send failed (data is still saved):", e)


def main(argv=None, bot=None, runner=run, now=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--git", action="store_true")
    args = ap.parse_args(argv)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if bot is None:
        from src.notify.telegram import Telegram, load_credentials
        token, chat = load_credentials()
        bot = Telegram(token, chat) if token and chat else None
    code, log = runner(["tools/forward_log.py"])
    ok = code == 0 and "DONE" in log
    code2, log2 = runner(["tools/export_forward.py"]) if ok else (1, "")
    if not ok or code2 != 0:
        msg = "Falcon: daily run FAILED\n" + (log if not ok else log2)[-1500:]
        print(msg)
        if bot:
            safe_send(bot, msg)
        return 1
    text, n = build_message(log, now)
    print(text)
    if bot:
        if n == 0:
            text = "Falcon: run finished but no risk sheet was found in the output.\n" + log[-1500:]
        safe_send(bot, text)
    if args.git:
        for cmd in (["add", "research/forward"],
                    ["commit", "-q", "-m", "Forward sheets %s" % now.strftime("%Y-%m-%d")]):
            subprocess.run(["git"] + cmd, cwd=ROOT)
        for _ in range(2):
            if subprocess.run(["timeout", "180", "git", "push"], cwd=ROOT).returncode == 0:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
