# Risk / Context Analyst — product spec v1 (2026-10-13)

Purpose: tell the user, at every hourly close, how big a move against any position can be over the next 24 hours.
It makes NO claim about direction and executes nothing.

## Output (per symbol, 1h, each candle close)
- expected_range: expected mean candle range over the next 24 candles (% of price), from the validated
  volatility forecaster (F-003).
- risk_level: percentile of ln(expected_range) within the trailing 365 days:
  low (< 25%), normal (25-75%), high (75-95%), extreme (>= 95%).
- adverse_excursion quantiles q50 / q80 / q95 (% of price): the largest distance, in either direction, between
  the next candle's open and any high/low during the next 24 candles. Estimated as
  expected_range x empirical quantile of (E / expected_range) from training data only.
- Intended reading: "with 95% probability price will not move further than q95 from the entry in the next
  24 hours" -> stop distance and position size are chosen by the user against that number.

## Not in v1
Direction, entries, trade execution, other timeframes (configurable later), AI explanation text (later layer).

## Definitions
E = max(max(high[i+1..i+24]) - open[i+1], open[i+1] - min(low[i+1..i+24])) / open[i+1]
Decision at the close of candle i; windows never cross data gaps; walk-forward exactly as F-003
(expanding window, 2y minimum, refit every 90 days, purge by timestamp).
