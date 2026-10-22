from types import SimpleNamespace as C

from src.lab.runner import drop_off_grid

H = 3_600_000


def test_drops_shifted_candles_and_keeps_order():
    cs = [C(timestamp=t) for t in (0, H, H + 1000, 2 * H, 2 * H + 99, 3 * H)]
    assert [c.timestamp for c in drop_off_grid(cs, H)] == [0, H, 2 * H, 3 * H]


def test_clean_series_is_unchanged():
    cs = [C(timestamp=i * H) for i in range(5)]
    assert drop_off_grid(cs, H) == cs
