"""Send text to your Telegram chat.

  some_command | python tools/telegram_push.py            (stdin as message)
  python tools/telegram_push.py --file path [--caption C]  (send as document)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.notify.telegram import Telegram, TelegramError, load_credentials


def main(argv=None, stdin=None, bot=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--caption", default="")
    args = ap.parse_args(argv)
    if bot is None:
        token, chat = load_credentials()
        if not token or not chat:
            print("Telegram not configured: run tools/telegram_setup.py first.")
            return 1
        bot = Telegram(token, chat)
    try:
        if args.file:
            bot.send_document(args.file, args.caption)
        else:
            text = (stdin or sys.stdin).read().strip()
            if not text:
                print("Nothing to send (empty input).")
                return 1
            bot.send_message(text)
    except TelegramError as e:
        print("Telegram error:", e)
        return 1
    print("Sent to Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
