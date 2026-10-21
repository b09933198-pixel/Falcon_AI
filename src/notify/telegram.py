"""Minimal Telegram Bot API client (standard library only).

The token is read from the environment (FALCON_TG_TOKEN) or from the file
~/.falcon_telegram (lines TOKEN=... and CHAT_ID=...). It is never written to
the repository and never included in an error message.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

CRED_FILE = os.path.join(os.path.expanduser("~"), ".falcon_telegram")
MAX_LEN = 4000


class TelegramError(Exception):
    pass


def read_file(path=CRED_FILE):
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    out[k.strip()] = v.strip()
    return out


def load_credentials(path=CRED_FILE, env=None):
    env = os.environ if env is None else env
    data = read_file(path)
    token = env.get("FALCON_TG_TOKEN") or data.get("TOKEN")
    chat = env.get("FALCON_TG_CHAT") or data.get("CHAT_ID")
    return token, chat


def save_chat_id(chat_id, path=CRED_FILE):
    data = read_file(path)
    data["CHAT_ID"] = str(chat_id)
    with open(path, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write("%s=%s\n" % (k, v))
    os.chmod(path, 0o600)


def split_text(text, limit=MAX_LEN):
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + 1 + len(line) > limit:
            parts.append(cur)
            cur = line
        else:
            cur = line if not cur else cur + "\n" + line
    if cur:
        parts.append(cur)
    return parts or [""]


class Telegram:
    def __init__(self, token, chat_id=None, opener=None, timeout=30):
        if not token:
            raise TelegramError("token is missing")
        self._token = token
        self.chat_id = chat_id
        self._open = opener or urllib.request.urlopen
        self._timeout = timeout

    def _url(self, method):
        return "https://api.telegram.org/bot%s/%s" % (self._token, method)

    def _do(self, request, method):
        try:
            with self._open(request, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise TelegramError("%s failed: HTTP %s" % (method, e.code)) from None
        except Exception as e:
            raise TelegramError("%s failed: %s" % (method, type(e).__name__)) from None
        if not payload.get("ok"):
            raise TelegramError("%s refused: %s" % (method, payload.get("description", "?")))
        return payload["result"]

    def call(self, method, params=None):
        body = urllib.parse.urlencode(params or {}).encode("utf-8")
        return self._do(urllib.request.Request(self._url(method), data=body), method)

    def send_message(self, text, chat_id=None):
        chat = chat_id or self.chat_id
        if not chat:
            raise TelegramError("chat id is missing")
        for part in split_text(text):
            self.call("sendMessage", {"chat_id": chat, "text": part})

    def get_updates(self, offset=None):
        params = {"timeout": 0}
        if offset is not None:
            params["offset"] = offset
        return self.call("getUpdates", params)

    def send_document(self, path, caption="", chat_id=None):
        chat = chat_id or self.chat_id
        if not chat:
            raise TelegramError("chat id is missing")
        boundary = uuid.uuid4().hex
        with open(path, "rb") as f:
            content = f.read()
        parts = []
        for k, v in (("chat_id", chat), ("caption", caption)):
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                          % (boundary, k, v)).encode("utf-8"))
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"document\"; filename=\"%s\"\r\n"
                      "Content-Type: application/octet-stream\r\n\r\n"
                      % (boundary, os.path.basename(path))).encode("utf-8"))
        parts.append(content)
        parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
        req = urllib.request.Request(self._url("sendDocument"), data=b"".join(parts))
        req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
        return self._do(req, "sendDocument")


def find_chat_id(updates):
    for u in reversed(updates):
        msg = u.get("message") or u.get("channel_post")
        if msg and "chat" in msg:
            return msg["chat"]["id"]
    return None
