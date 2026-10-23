import pytest

from src.lab.carry import (DAY_MS, CarryParams, CarryTrade, annual_return, by_year, judge,
                           simulate_carry, trade_returns, trailing_daily)

H8 = 8 * 3_600_000

P = CarryParams(entry_window_days=7, entry_daily_rate=0.00045, exit_window_days=3, exit_daily_rate=0.00015,
                max_hold_days=90, round_trip_cost=0.004, capital_factor=2.0)

RULES = {"min_trades": 60, "min_annual_return": 0.08, "min_annual_return_2x_costs": 0.05, "min_year_trades": 5,
         "min_positive_year_share": 0.7, "bad_trade_loss": 0.005, "max_bad_trade_share": 0.10}


def events(rates):
    return [k * H8 for k in range(len(rates))], list(rates)


def test_trailing_daily_window_is_open_closed():
    times, rates = events([0.001] * 6)
    out = trailing_daily(times, rates, 1)             # window (t - 1 day, t] holds 3 events
    assert out[0] == pytest.approx(0.001)
    assert out[2] == pytest.approx(0.003)
    assert out[5] == pytest.approx(0.003)


def test_no_trade_when_funding_is_low():
    times, rates = events([0.0001] * 200)             # 0.0003 per day < 0.00045
    assert simulate_carry("X", times, rates, P) == []


def test_enter_after_warmup_exit_on_rate_and_funding_sum():
    # 0.0002 per event for events 0..60, then 0. D7 reaches 0.0006 at event 21 (full 7-day window): entry there.
    # D3 falls to 0.000133 at event 67 (two non-zero events left in the window of nine): exit there.
    rates = [0.0002] * 61 + [0.0] * 40
    times, rates = events(rates)
    trades = simulate_carry("X", times, rates, P)
    assert len(trades) == 1
    t = trades[0]
    assert t.entry_ms == 21 * H8 and t.exit_ms == 67 * H8 and t.reason == "rate"
    assert t.funding == pytest.approx(39 * 0.0002)    # events 22..60 collected, 61..67 are zero


def test_no_entry_before_a_full_window():
    times, rates = events([0.01] * 21)                # events 0..20 span 6.67 days < 7
    assert simulate_carry("X", times, rates, P) == []


def test_max_hold_exit():
    p = CarryParams(7, 0.00045, 3, 0.00015, 10, 0.004, 2.0)
    times, rates = events([0.0002] * 200)
    t = simulate_carry("X", times, rates, p)[0]
    assert t.reason == "max_hold" and t.exit_ms - t.entry_ms >= 10 * DAY_MS
    assert (t.exit_ms - t.entry_ms) < 10 * DAY_MS + H8


def test_end_of_data_exit_and_reentry_after_exit():
    times, rates = events([0.0002] * 40)
    t = simulate_carry("X", times, rates, P)
    assert len(t) == 1 and t[0].reason == "end" and t[0].exit_ms == 39 * H8
    rates2 = [0.0002] * 61 + [0.0] * 20 + [0.0002] * 60
    times2, rates2 = events(rates2)
    trades = simulate_carry("X", times2, rates2, P)
    assert len(trades) == 2 and trades[1].entry_ms > trades[0].exit_ms


def test_rejects_unsorted_times():
    with pytest.raises(ValueError):
        simulate_carry("X", [0, 0], [0.0, 0.0], P)


def test_returns_and_annual_math():
    t = CarryTrade("X", 0, 30 * DAY_MS, 0.01, "rate")          # 1% funding in 30 days, cost 0.4%
    assert trade_returns([t], P) == [pytest.approx(0.003)]      # (0.01 - 0.004) / 2
    assert annual_return([t], P) == pytest.approx(0.003 / 30 * 365)
    assert trade_returns([t], P, 2.0) == [pytest.approx(0.001)]  # (0.01 - 0.008) / 2


def test_judge_pass_and_each_failure():
    day = DAY_MS
    base = 1_577_836_800_000                                   # 2020-01-01
    good = [CarryTrade("X", base + i * 60 * day, base + i * 60 * day + 30 * day, 0.03, "rate") for i in range(70)]
    result = judge(good, P, RULES)
    assert result["passed"] is True
    assert by_year(good, P)

    few = judge(good[:10], P, RULES)
    assert few["passed"] is False and few["checks"][0][2] is False

    low = [CarryTrade("X", base + i * 60 * day, base + i * 60 * day + 30 * day, 0.0045, "rate") for i in range(70)]
    assert judge(low, P, RULES)["checks"][1][2] is False

    bad = good[:60] + [CarryTrade("X", base, base + 30 * day, -0.05, "rate") for _ in range(10)]
    assert judge(bad, P, RULES)["checks"][4][2] is False
