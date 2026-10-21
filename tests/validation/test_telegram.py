import io
import json
import urllib.error

import pytest

from src.notify.telegram import (Telegram, TelegramError, find_chat_id,
                                 load_credentials, save_chat_id, split_text)


class FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make(payload, calls):
    def opener(req, timeout=None):
        calls.append(req)
        return FakeResp(payload)
    return opener


def test_send_message_builds_request():
    calls = []
    bot = Telegram("TOK", "42", opener=make({"ok": True, "result": {}}, calls))
    bot.send_message("hello")
    assert calls[0].full_url == "https://api.telegram.org/botTOK/sendMessage"
    assert b"chat_id=42" in calls[0].data and b"text=hello" in calls[0].data


def test_long_text_is_split():
    calls = []
    bot = Telegram("T", "1", opener=make({"ok": True, "result": {}}, calls))
    bot.send_message("\n".join(["x" * 100] * 100))
    assert len(calls) >= 3
    assert all(len(p) <= 4000 for p in split_text("a" * 9000))


def test_error_never_contains_token():
    def opener(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, io.BytesIO(b""))
    bot = Telegram("SECRET123", "1", opener=opener)
    with pytest.raises(TelegramError) as e:
        bot.send_message("x")
    assert "SECRET123" not in str(e.value) and "401" in str(e.value)


def test_refused_payload_raises():
    bot = Telegram("T", "1", opener=make({"ok": False, "description": "bad"}, []))
    with pytest.raises(TelegramError):
        bot.call("getMe")


def test_missing_token_or_chat():
    with pytest.raises(TelegramError):
        Telegram("")
    with pytest.raises(TelegramError):
        Telegram("T", opener=make({"ok": True, "result": {}}, [])).send_message("x")


def test_find_chat_id():
    ups = [{"message": {"chat": {"id": 7}}}, {"message": {"chat": {"id": 9}}}]
    assert find_chat_id(ups) == 9
    assert find_chat_id([]) is None


def test_credentials_file_and_env(tmp_path):
    p = tmp_path / "cred"
    p.write_text("TOKEN=abc\n")
    assert load_credentials(str(p), env={}) == ("abc", None)
    save_chat_id(123, str(p))
    assert load_credentials(str(p), env={}) == ("abc", "123")
    assert load_credentials(str(p), env={"FALCON_TG_TOKEN": "e"}) == ("e", "123")


def test_send_document_multipart(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("a,b\n1,2\n")
    calls = []
    bot = Telegram("T", "5", opener=make({"ok": True, "result": {}}, calls))
    bot.send_document(str(f), "cap")
    assert b"filename=\"a.csv\"" in calls[0].data and b"1,2" in calls[0].data
    assert calls[0].get_header("Content-type").startswith("multipart/form-data")
