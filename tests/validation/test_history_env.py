import importlib.util
import os
import pathlib
import uuid

KEYS = ("FALCON_HISTORY_DB", "FALCON_HISTORY_START", "FALCON_HISTORY_END")


def load(monkeypatch, env):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    path = pathlib.Path(__file__).resolve().parents[2] / "tools" / "download_history.py"
    spec = importlib.util.spec_from_file_location("dh_" + uuid.uuid4().hex, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_defaults_unchanged(monkeypatch):
    m = load(monkeypatch, {})
    months = list(m.months())
    assert months[0] == "2021-01"
    assert m.DB_PATH == os.path.join("data", "history", "history.db")


def test_env_overrides(monkeypatch):
    m = load(monkeypatch, {"FALCON_HISTORY_DB": "x/old.db",
                           "FALCON_HISTORY_START": "2017-08",
                           "FALCON_HISTORY_END": "2020-12"})
    months = list(m.months())
    assert months[0] == "2017-08" and months[-1] == "2020-12" and len(months) == 41
    assert m.DB_PATH == "x/old.db"
