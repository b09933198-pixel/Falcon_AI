# Falcon_AI Findings Ledger

Every experiment is recorded here: hypothesis, criteria fixed BEFORE the run,
result, verdict. A rejected hypothesis stays in this file. Nothing is deleted.

## F-001 - Does market-structure trend predict the next price move?

Date: 2026-10-10
Hypothesis: after a BULLISH market-structure state (HH + HL) price rises more
than after a BEARISH state (LH + LL).
Structure definition: swing detector v1.1 + structure tracker v1.0, swing
strengths 3, 5, 8, 12. Swings are used only after they are confirmed.
Data: Binance spot 1h candles, BTCUSDT and ETHUSDT, 2021-01 to 2026-09
(about 50,000 candles each; data gaps are never crossed).
Method: forward return from the next open to the close after 4 and 24 candles;
significance by circular-shift test (1000 shifts); no fees, no slippage.
Criteria fixed before the run:
  1. p < 0.0063 in a run (0.05 / 8 tests)
  2. same strength and horizon: same sign and p < 0.05 on the other asset
  3. difference positive in at least 70 % of years
  4. long/short edge larger than round-trip costs (Toobit fees to be confirmed)
Result: no combination passes. p-values 0.37-0.95 on BTCUSDT and 0.29-0.93 on
ETHUSDT. The sign of the difference changes between strengths and assets.
Verdict: REJECTED in this form.
Detection limit (approximate): about 7 bp at 4 candles, about 30-50 bp at 24.
Not covered: other timeframes (4h, 1d), other structure definitions, events
such as liquidity sweeps, prediction of volatility instead of direction,
Toobit's own data.
Results: research/results/structure_edge_BTCUSDT_1h.txt
         research/results/structure_edge_ETHUSDT_1h.txt

## F-002 - Is volatility predictable, and does market structure add to it?

Date: 2026-10-10
Status: PRE-REGISTERED. The criteria below were fixed and committed BEFORE the first run.
Questions:
  V-1   Do past volatility and the time of day predict the volatility of the
        next 24 candles out of sample?
  F-002 Does a market-structure feature add information beyond that baseline?
Data: Binance spot 1h candles, BTCUSDT and ETHUSDT, 2021-01 to 2026-09
(segments of at least 400 candles; gaps are never crossed).
Target: ln(mean of ln(high/low) over the next 24 candles).
Baseline regressors (known at the close): ln(mean ln(high/low) over the last
24 candles), the same over the last 168 candles, time of day (sin/cos, 2 harmonics).
Structure features (swings used only after confirmation; strengths 5 and 12):
  leg      ln(size of the latest swing leg / close)
  age      ln(1 + candles since the latest swing was confirmed)
  ranging  1 when market structure is RANGING, else 0
Method: out-of-sample = fit on the first 70 % of rows, score on the last 30 %.
  Incremental information = correlation between the baseline-residuals of the
  feature and of the target, tested with a circular-shift test (1000 shifts).
Criteria:
  V-1: out-of-sample R2 >= 0.10 on BTCUSDT and on ETHUSDT.
  F-002: a (feature, strength) combination passes only if ALL hold:
    C1  p < 0.0083 (0.05 / 6 tests) on one asset, and the same sign with
        p < 0.05 on the other asset
    C2  the sign holds in at least 70 % of usable years (>= 3 years with
        >= 500 rows each) on both assets
    C3  adding the feature raises out-of-sample R2 by at least 0.005 on both assets
Tool validation (synthetic data, before the real run): constant volatility ->
  baseline R2 about 0 and nothing passes; GARCH volatility -> baseline
  out-of-sample R2 0.36-0.43 and nothing passes; a planted structure effect ->
  only the planted feature passes; about 7 % false positives at p < 0.05
  over 180 null tests.
Result (run 2026-10-11, criteria unchanged after seeing it):
  V-1 PASSED. Out-of-sample R2 0.401 (BTCUSDT) and 0.441 (ETHUSDT); in-sample
  0.605 / 0.647. Next-24-candle volatility is forecastable from past volatility
  and time of day.
  F-002 REJECTED. No (feature, strength) combination passed. Closest: age
  (candles since the last confirmed swing): positive and significant on both
  assets at both strengths (p = 0.0010, the floor with 1000 shifts), same sign
  in 6/6 years on both, but out-of-sample gain only +0.0014 to +0.0027, below
  the 0.005 bar (C3 failed). Real-looking but economically negligible; it may
  reflect nonlinearity missed by the linear baseline rather than structure.
  Not promoted. leg and ranging fail C1.
  Limits: R2 is of log mean range, not profit; no fees; Binance spot data.
  Raw output: research/results/structure_vol_1h.txt

## F-003 - Is the volatility forecaster good enough for risk use?

Date: 2026-10-11
Status: PRE-REGISTERED. The criteria below were fixed and committed BEFORE the first run.
Question: does the forecaster in src/analysis/volatility/forecaster.py (past
volatility over 24 and 168 candles + time of day -> average candle range of the
next 24 candles, least squares in log space) hold up walk-forward, and are its
expected value and 90 % upper bound trustworthy enough to size stops and positions?
Data: Binance spot 1h candles, BTCUSDT and ETHUSDT (segments of at least 400 candles).
Method: walk-forward. Expanding training window, at least 2 years before the
  first test row, refit every 90 days, scored only on rows after the window.
  Training rows whose target period reaches into the test period are purged.
  Naive references: ln(mean range of the last 24 candles) and an EWMA with a
  24-candle half-life, each shifted by its mean training error.
Criteria (ALL must hold on BOTH assets):
  W1  model MSE <= 0.97 x the best naive MSE
  W2  calibration slope of realised on predicted (log space) within 0.90 .. 1.10
  W3  decile resolution: realised range of the top predicted decile >= 1.5 x the
      bottom decile, and at least 8 of 9 decile steps rising
  W4  model beats the best naive in >= 75 % of test years (>= 3 years, >= 2000 rows each)
  W5  the 90 % upper bound holds between 86 % and 94 % of the time
Disclosures:
  - V-1 results (out-of-sample R2 about 0.40) were known when these criteria were
    set, so W1 is expected to pass; W2-W5 measure calibration, the upper bound and
    yearly stability, which V-1 did not.
  - W3's ratio was lowered from 2.0 to 1.5 after a synthetic control showed
    ratios of 1.8-2.0. 2.0 was an arbitrary number; 1.5 means stop distances
    can differ by half between quiet and wild markets, enough to size on.
    This was done before any real-data run of this test.
Tool validation (synthetic data): constant volatility -> fails W2 and W3;
  GARCH volatility, three seeds -> passes all five.
Result: pending.
