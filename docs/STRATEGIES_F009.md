# F-009 strategy rules (frozen before the hold-out run)

All rules are written in CANDLES, not in hours, so they work on any timeframe. The timeframe is a setting, not code.
Nothing here is tuned. Parameters are textbook defaults. A rule that cannot be implemented exactly as written is
dropped before the run and reported as "not testable"; it is never changed afterwards.

## Common definitions

- Candle i = the candle that just closed. Only candles up to i are used. Entry at open of candle i+1.
- ATR(14): Wilder smoothing of true range (true range = max(high-low, |high-prev close|, |low-prev close|)).
- Pivot high at k: high[k] is strictly greater than the 5 highs before and the 5 highs after; it is known
  (confirmed) only at candle k+5. Pivot low is symmetric.
- No signal before candle index 200 of a series. Signals need ATR > 0.
- If a long and a short signal appear on the same candle, both are ignored.
- One trade at a time per strategy, symbol and timeframe. Signals during a trade are ignored. After an exit at
  candle j, the earliest new entry is the open of candle j+1.
- Stop and target are checked on each candle's high/low starting with the entry candle. If both are inside the same
  candle, the stop is assumed to be hit first. A stop or target is filled at its price (costs are charged separately).
- Timeout: exit at the close of the candle number `timeout` after entry.
- Costs per trade (as fractions of entry price): taker fee 0.06% per side, slippage 0.02% per side, plus funding
  paid or received while the trade is open. Net R = (price result - costs) / stop distance.

## Gate A (fixed 1:1)

stop = target = 2 x ATR(14) at candle i; timeout 48 candles.

## Gate B (natural), common part

Each strategy names a structural stop level. The stop distance (entry to that level) is clipped to the range
[1 x ATR, 4 x ATR]. Unless the strategy says otherwise, target = 2 x stop distance and timeout = 96 candles.

## S01 Trendline break

- Rising line: through the last two confirmed pivot lows P1 then P2 with low(P2) > low(P1). Falling line: through the
  last two confirmed pivot highs with high(P2) < high(P1).
- A line is valid if P2 is at most 100 candles before i and no close after P2 has been beyond the line.
- Short when close[i] < rising line value at i and close[i-1] >= its value at i-1.
  Long when close[i] > falling line value at i and close[i-1] <= its value at i-1.
- Gate B stop level: for a long, the lowest low of the last 10 candles; for a short, the highest high of the last 10.

## S05 Double top / double bottom

- Double top: two confirmed pivot highs H1 then H2, 10 to 100 candles apart, |H1 - H2| <= 0.5 x ATR(14)[i]. Neckline N
  = lowest low between them; depth = max(H1,H2) - N must be >= 2 x ATR(14)[i].
- Short when close[i] < N and close[i-1] >= N, within 50 candles after H2 was confirmed.
- Double bottom is the mirror image and gives a long (neckline = highest high between the two lows).
- Gate B stop level: the higher of H1, H2 (short) or the lower of the two lows (long). Target = depth measured from
  the neckline (measured move). Timeout 96.

## S10 RSI

- RSI(14), Wilder smoothing.
- Long when RSI[i-1] < 30 and RSI[i] >= 30. Short when RSI[i-1] > 70 and RSI[i] <= 70.
- Gate B: stop = 2 x ATR(14) (no clipping); exit at the close of the first candle where RSI has reached 50 (long: RSI >= 50,
  short: RSI <= 50), or at the stop, or at timeout 48.

## S12 EMA cross

- EMA(20) and EMA(50), alpha = 2/(n+1), seeded with the simple average of the first n closes.
- Long when EMA20 crosses above EMA50 at close[i]; short on the opposite cross.
- Gate B: stop = 2 x ATR(14) (no clipping); exit at the close of the candle where the opposite cross happens, or at
  the stop, or at timeout 200.

## S13 Support / resistance bounce

- Levels from confirmed pivots of the last 200 candles. Pivot lows within 0.25 x ATR(14)[i] of each other form one
  support cluster, pivot highs form resistance clusters. A level needs at least 3 pivots; its price is their mean.
- Use the level nearest to close[i].
- Long: support level S, low[i] <= S + 0.1 x ATR, low[i] >= S - 0.5 x ATR, close[i] > S and close[i] > open[i].
  Short: resistance level R, high[i] >= R - 0.1 x ATR, high[i] <= R + 0.5 x ATR, close[i] < R and close[i] < open[i].
- Gate B stop level: level -/+ 0.5 x ATR (below support for a long, above resistance for a short).

## S14 Donchian breakout

- Long when close[i] > highest high of candles i-20..i-1. Short when close[i] < lowest low of candles i-20..i-1.
- Gate B stop level: lowest low (long) or highest high (short) of the last 10 candles up to i.

## S15 Volatility squeeze breakout

- Bollinger(20, 2): mid = SMA(20) of closes, bands = mid +/- 2 population standard deviations,
  bandwidth BW = (upper - lower) / mid.
- Candle k is in a squeeze if BW[k] is at or below the 20th percentile of BW over candles k-119..k.
- Long when candle i-1 is in a squeeze and close[i] > upper band[i]. Short when candle i-1 is in a squeeze and
  close[i] < lower band[i].
- Gate B stop level: the middle band (SMA 20) at i.

## S16 Liquidity sweep

- H = highest high of candles i-20..i-1, L = lowest low of candles i-20..i-1.
- Short when high[i] > H + 0.1 x ATR and close[i] < H. Long when low[i] < L - 0.1 x ATR and close[i] > L.
- Gate B stop level: the sweep extreme (high[i] for a short, low[i] for a long).

## Timeframes

The rules above do not mention time. The set of timeframes comes from a settings file, so changing it needs no code
change. F-009 as registered is the 1h hold-out round only. Every additional timeframe is a new set of tests: it
gets its own registration (own M, own alpha, its own single look at its own hold-out) before it is run. Higher
timeframes are built from the 1h archive; 15m needs its own archive download. Round-trip costs are a larger share
of the stop on short timeframes, so the break-even win rate of gate A rises on them.
