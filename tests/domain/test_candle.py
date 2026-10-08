from src.domain.models.candle import Candle


def make_candle(**overrides):
    data = {
        "timestamp": 1000,
        "open": 100.0,
        "high": 110.0,
        "low": 90.0,
        "close": 105.0,
        "volume": 1000.0,
        "quote_volume": 100000.0,
        "trades": 500,
        "buy_volume": 400.0,
        "buy_quote_volume": 40000.0,
    }

    data.update(overrides)

    return Candle(**data)


def test_candle_creation():
    candle = make_candle()

    assert candle.timestamp == 1000
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 90.0
    assert candle.close == 105.0
    assert candle.volume == 1000.0
    assert candle.quote_volume == 100000.0
    assert candle.trades == 500


def test_candle_is_immutable():
    candle = make_candle()

    try:
        candle.close = 200.0
        assert False
    except AttributeError:
        pass


def test_invalid_timestamp():
    try:
        make_candle(timestamp=-1)
        assert False
    except ValueError:
        pass


def test_invalid_open_negative():
    try:
        make_candle(open=-1.0)
        assert False
    except ValueError:
        pass


def test_invalid_high_negative():
    try:
        make_candle(high=-1.0)
        assert False
    except ValueError:
        pass


def test_invalid_low_negative():
    try:
        make_candle(low=-1.0)
        assert False
    except ValueError:
        pass


def test_invalid_close_negative():
    try:
        make_candle(close=-1.0)
        assert False
    except ValueError:
        pass


def test_invalid_open_above_high():
    try:
        make_candle(open=120.0)
        assert False
    except ValueError:
        pass


def test_invalid_open_below_low():
    try:
        make_candle(open=80.0)
        assert False
    except ValueError:
        pass


def test_invalid_high_low():
    try:
        make_candle(high=80.0, low=90.0)
        assert False
    except ValueError:
        pass


def test_invalid_close_above_high():
    try:
        make_candle(close=120.0)
        assert False
    except ValueError:
        pass


def test_invalid_close_below_low():
    try:
        make_candle(close=80.0)
        assert False
    except ValueError:
        pass


def test_negative_volume():
    try:
        make_candle(volume=-1.0)
        assert False
    except ValueError:
        pass


def test_negative_quote_volume():
    try:
        make_candle(quote_volume=-1.0)
        assert False
    except ValueError:
        pass


def test_negative_trades():
    try:
        make_candle(trades=-1)
        assert False
    except ValueError:
        pass


def test_negative_buy_volume():
    try:
        make_candle(buy_volume=-1.0)
        assert False
    except ValueError:
        pass


def test_buy_volume_cannot_exceed_volume():
    try:
        make_candle(buy_volume=1001.0)
        assert False
    except ValueError:
        pass


def test_negative_buy_quote_volume():
    try:
        make_candle(buy_quote_volume=-1.0)
        assert False
    except ValueError:
        pass


def test_buy_quote_volume_cannot_exceed_quote_volume():
    try:
        make_candle(buy_quote_volume=100001.0)
        assert False
    except ValueError:
        pass


def test_from_api():
    candle = Candle.from_api({
        "timestamp": "1000",
        "open": "100",
        "high": "110",
        "low": "90",
        "close": "105",
        "volume": "1000",
        "quote_volume": "100000",
        "trades": "500",
        "buy_volume": "400",
        "buy_quote_volume": "40000",
    })

    assert candle.timestamp == 1000
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 90.0
    assert candle.close == 105.0
    assert candle.volume == 1000.0
    assert candle.quote_volume == 100000.0
    assert candle.trades == 500
    assert candle.buy_volume == 400.0
    assert candle.buy_quote_volume == 40000.0


def test_from_dict():
    source = {
        "timestamp": "1000",
        "open": "100",
        "high": "110",
        "low": "90",
        "close": "105",
        "volume": "1000",
        "quote_volume": "100000",
        "trades": "500",
        "buy_volume": "400",
        "buy_quote_volume": "40000",
    }

    candle = Candle.from_dict(source)

    assert candle.timestamp == 1000
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 90.0
    assert candle.close == 105.0
    assert candle.volume == 1000.0
    assert candle.quote_volume == 100000.0
    assert candle.trades == 500
    assert candle.buy_volume == 400.0
    assert candle.buy_quote_volume == 40000.0


def test_to_dict():
    candle = make_candle()

    data = candle.to_dict()

    assert data == {
        "timestamp": 1000,
        "open": 100.0,
        "high": 110.0,
        "low": 90.0,
        "close": 105.0,
        "volume": 1000.0,
        "quote_volume": 100000.0,
        "trades": 500,
        "buy_volume": 400.0,
        "buy_quote_volume": 40000.0,
    }


def test_to_tuple():
    candle = make_candle()

    assert candle.to_tuple() == (
        1000,
        100.0,
        110.0,
        90.0,
        105.0,
        1000.0,
        100000.0,
        500,
        400.0,
        40000.0,
    )


def test_repr():
    candle = make_candle()

    text = repr(candle)

    assert text == (
        "Candle("
        "time=1000, "
        "open=100.0, "
        "high=110.0, "
        "low=90.0, "
        "close=105.0"
        ")"
    )


def test_from_dict_round_trip():
    original = make_candle()

    restored = Candle.from_dict(original.to_dict())

    assert restored == original


def test_to_tuple_field_order():
    candle = make_candle()

    assert candle.to_tuple() == (
        candle.timestamp,
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume,
        candle.quote_volume,
        candle.trades,
        candle.buy_volume,
        candle.buy_quote_volume,
    )
