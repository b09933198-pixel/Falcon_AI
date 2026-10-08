# Candle

## Status

Frozen — Foundation v1

---

## Purpose

The `Candle` entity is the core market data object used throughout
Falcon AI.

It represents one immutable OHLCV market candle independently of any
exchange or infrastructure implementation.

---

## Domain Responsibility

`Candle` belongs to the Core Domain layer.

It must remain independent from:

- Exchanges
- API clients
- HTTP libraries
- pandas
- numpy
- Storage
- Infrastructure concerns

The entity may only represent and validate market data.

---

## Design Goals

- Immutable
- Lightweight
- Exchange-Agnostic
- Strongly Typed
- Self Validating
- Serializable
- High Performance

---

## Fields

| Field | Type | Description |
|---|---|---|
| timestamp | int | Candle timestamp |
| open | float | Opening price |
| high | float | Highest price |
| low | float | Lowest price |
| close | float | Closing price |
| volume | float | Base asset volume |
| quote_volume | float | Quote asset volume |
| trades | int | Number of trades |
| buy_volume | float | Buy-side base asset volume |
| buy_quote_volume | float | Buy-side quote asset volume |

---

## Validation Rules

The entity must enforce the following invariants.

### Timestamp

```text
timestamp >= 0
