"""One-time setup: finds your chat id after you send /start to the bot, saves it, sends a test message."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.notify.telegram import (Telegram, TelegramError, find_chat_id,
                                 load_credentials, save_chat_id)


def main():
    token, _ = load_credentials()
    if not token:
        print("No token. Create ~/.falcon_telegram first (see instructions).")
        return 1
    bot = Telegram(token)
    try:
        chat = find_chat_id(bot.get_updates())
        if chat is None:
            print("No message found. Open your bot in Telegram, send /start, then run this again.")
            return 1
        save_chat_id(chat)
        bot.send_message("Falcon: connection OK.", chat_id=chat)
    except TelegramError as e:
        print("Error:", e)
        return 1
    print("Done. Chat id saved to ~/.falcon_telegram and a test message was sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
