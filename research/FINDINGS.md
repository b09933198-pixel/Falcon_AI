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
Result (run 2026-10-11, criteria unchanged after seeing it):
  F-003 PASSED: all five criteria on both assets (BTCUSDT / ETHUSDT).
  W1 model/best-naive MSE ratio 0.874 / 0.907 (needs <= 0.97).
  W2 calibration slope 0.906 / 0.934 (needs 0.90-1.10; BTC is close to the edge).
  W3 top/bottom decile realised range 2.83 / 3.01, 9 of 9 rising steps (the
     original 2.0 bar would also have passed).
  W4 model beat the best naive in 4/4 test years on both assets (2023-2026).
  W5 the 90 % upper bound held 89.7 % / 89.7 %.
  Reading: usable as an INPUT for stop distance, position size and no-trade
  filters; the decile spread is real. Single forecasts are noisy (log-scale MSE
  about 0.10-0.13, roughly +-40 %), and the forecast is slightly over-dispersed
  (slope below 1: low deciles under-predicted, top decile over-predicted).
  Limits: 1h only; test period 2023-2026; candle range is not the same thing as
  stop-out risk; no fees; Binance spot data, not Toobit.
  Raw output: research/results/vol_forecast_1h.txt

## F-004 - Do simple price-action signals carry a directional edge?

Date: 2026-10-11
Status: PRE-REGISTERED. The criteria below were fixed and committed BEFORE the first run.
Question: do seven rule-based price-action signals predict direction well enough
to beat trading costs?
Data: Binance spot 1h candles, BTCUSDT and ETHUSDT, 2021-01 to 2026-09
(segments of at least 400 candles; gaps are never crossed).
Convention: decision at the close of candle i, entry at the open of i+1, exit at
the close of i+hold; returns in bp, before fees. Swings only after confirmation.
Variants (all two-sided: the sign of the mean edge shows the direction that works):
  S1  liquidity sweep, strength 5: a candle trades through the latest confirmed
      swing low (high) and closes back above (below) it -> long (short); each
      swing counts once; hold 24 candles
  S2  the same with strength 12
  S3  session Asia: long from the open at 00:00 UTC to the close at 08:00 (hold 8)
  S4  session Europe: 08:00 - 16:00 UTC (hold 8)
  S5  session US: 16:00 - 24:00 UTC (hold 8)
  S6  compression breakout: mean candle range of the last 24 candles within the
      lowest 20 % of its last 720 values at i-1, and candle i closes beyond the
      high (long) or low (short) of the previous 24 candles; hold 24
  S7  pullback against the 4h structure trend (4h bars, strength 3, completed
      bars only; 1h strength 5): 4h BULLISH while 1h BEARISH -> long, the mirror
      -> short; hold 24
Significance: block sign-flip test, weekly blocks, 2000 flips (two-sided).
Criteria (a variant passes only if ALL hold):
  C0  at least 200 events on each asset
  C1  p < 0.0071 (0.05 / 7) on one asset and the same sign with p < 0.05 on the other
  C2  the sign holds in >= 70 % of usable years (>= 3 years with >= 20 events) on both assets
  C3  the mean edge in its own direction is >= 12 bp on both assets
Disclosures:
  - The 12 bp round-trip cost is a PLACEHOLDER; the real Toobit fees are not
    confirmed yet. A higher real cost makes C3 stricter, never looser.
  - Prediction before the run: most likely nothing passes.
Tool validation (synthetic data): no effect, 30 seeds x 4 rules -> 7 of 120 tests
  (5.8 %) at p < 0.05 (5 % expected); a planted drift after the signal is
  detected for breakout and pullback in 5 of 5 seeds and for sweep in 3 of 5;
  a signal that peeks at the future is caught.
Result (run 2026-10-12, criteria unchanged after seeing it):
  F-004 REJECTED: none of the seven variants passed; every variant failed C1.
  Smallest p across the 14 tests: 0.037 (S6 compression breakout on BTCUSDT,
  edge +26.6 bp, 6/6 years positive), but ETHUSDT gave +10.4 bp with p = 0.58.
  Consistent with chance over 14 tests; not promoted.
  S1/S2 sweeps: edges -1.3/-1.9 bp (strength 5) and +5.4/+8.8 bp (strength 12),
  p 0.58-0.87. S3-S5 sessions: edges 0.2-9.7 bp, p 0.07-0.96 (largest: US
  session on ETHUSDT, +9.7 bp, p = 0.067, BTCUSDT +5.3 bp, p = 0.16).
  S7 pullback vs 4h trend: +10.9 bp (BTC, p = 0.43) and -3.3 bp (ETH, p = 0.84).
  Limits: 1h only; before fees; the 12 bp cost is a placeholder; two assets.
  Raw output: research/results/price_action_1h.txt

### F-005 verdict (2026-10-13): REJECTED — no confirmed candidate

Run: `python tools/check_positioning.py BTCUSDT,ETHUSDT 2000`, output in research/results/positioning_1h.txt.
Criteria applied exactly as pre-registered; nothing changed after the run.

- D1, D2, D3, D4, D5, D7 failed C1 (no p < 0.05/7 with a same-sign p < 0.05 on the other asset).
  D4 (futures taker flow) and D5 (spot taker-buy share) are near 0 bp on both assets.
- D6 (global long/short account ratio, hold 24h) passed discovery C0-C3: BTC -51.3 bp (p=0.0005, years 5/5),
  ETH -53.1 bp (p=0.0055, years 4/4), i.e. contrarian to the crowd. Hold-out: BTC -25.4 bp (p=0.23),
  ETH +7.6 bp (p=0.79). ETH's sign flipped, so C4 failed. Not confirmed.

Reading: D6 is neither established nor excluded. It was 1 of 7 variants, in the third family of direction
tests (cumulative multiplicity not corrected); the hold-out is ~1 year of heavily overlapping 24h windows;
hit rate < 50% with a large mean edge suggests a few large moves drive it. It is NOT to be used for any
product claim.
Only valid follow-up: ONE new pre-registered hypothesis (contrarian to the crowd ratio extreme, hold 24h)
evaluated on data arriving after 2026-10-13, with a pre-fixed minimum number of months and events.
Direction research on price and positioning data is paused; next product direction: risk/context analyst
built on the validated volatility forecaster (F-003).

### F-005 pre-registration (text committed AFTER the run — disclosure)

DISCLOSURE: the planned order (commit the pre-registration, then run) was NOT followed. The single real run
happened first; this entry was committed afterwards (2026-10-13). What supports that nothing was tuned: the
criteria below were fixed in the header and constants of tools/check_positioning.py (md5 537f5a25, verified on
the phone before the run); the run was the first and only one on real data; no criterion was changed. This
evidence lives in the conversation, not in git history. The verdict above is negative, so post-hoc bias could
not have produced a false positive.

Question: do funding, open interest, long/short ratios, taker buy/sell flow or spot taker-buy share predict
direction of BTCUSDT/ETHUSDT 1h by more than costs?
Convention: decision at close of candle i, entry at open of i+1, exit at close of i+horizon, bp before fees.
A 5-min metrics row stamped T is usable only when T + 5 min <= decision time; staleness 30 min (metrics),
9 h (funding); percentile window 2160 h (>= 1000 valid), mid-rank ties.
Variants: D1 funding top/bottom 10% (h24); D2 OI 24h change top 20% x sign of past 24h return (h24);
D3 same, bottom 20% (h24); D4 mean ln taker buy/sell ratio 4h top/bottom 10% (h4); D5 spot taker-buy share 4h
top/bottom 10% (h4); D6 ln global long/short account ratio top/bottom 10% (h24); D7 ln top-trader ratio
top/bottom 10% (h24).
Split: discovery = holding period ended by 2025-10-01; hold-out only for variants passing C0-C3.
Criteria: block sign-flip (weekly blocks, 2000 flips). C0 >= 200 events per asset; C1 p < 0.05/7 on one asset and
same sign p < 0.05 on the other; C2 sign in >= 70% of usable years (>= 3 years with >= 20 events), both assets;
C3 |edge| >= 12 bp (placeholder cost) on both, same sign; C4 hold-out same sign on both and |edge| >= 6 bp.
Caveats: 12 bp is a placeholder; third family of direction tests, cumulative multiplicity not corrected.
Tool validation (synthetic, sandbox): null data -> nothing passes; planted taker-flow effect -> D4 passes C0-C4.

---

## F-006 — Risk / context analyst: are the adverse-excursion quantiles calibrated?

**Status:** PRE-REGISTERED (written and committed BEFORE any code or real run, 2026-10-13)

**Question.** Do the q50 / q80 / q95 adverse-excursion quantiles (docs/RISK_ANALYST_SPEC.md) have the stated
coverage out of sample, and does the risk level carry information, on BTCUSDT and ETHUSDT 1h?

**Method.** Walk-forward as F-003. Target E as defined in the spec. Model: F-003 expected range times the
empirical quantile of E / expected_range on training data. Baseline B: the unconditional empirical quantile
of E over the trailing 365 days. Coverage = share of events with E <= predicted quantile.

**Criteria (fixed; all must hold for the product claim):**
- R1 pooled out-of-sample coverage on both assets: q50 in [47%, 53%], q80 in [77%, 83%], q95 in [92%, 98%].
- R2 coverage by risk level (levels with >= 300 events): within +-6 pp of nominal for q80 and q95, both assets.
- R3 by calendar year (years with >= 1000 events): q95 coverage in [90%, 99%], both assets.
- R4 median realized E strictly increases low < normal < high < extreme, both assets.
- R5 pinball loss at q80 and q95 is lower than baseline B on both assets.

**Disclosures.** No direction claim, so no multiple-testing family: one model, one set of criteria. Overlapping
24h windows make events dependent, so coverage tolerances are wide enough for that and are not significance
tests. Coverage is measured on the same data F-003 was developed on (2023-2026 walk-forward); fresh forward
data must be accumulated before real use. Prior: R1/R4/R5 likely hold (F-003 W-criteria passed); R2/R3
are the real risk (regime shifts).
**Verdict:** pending.

### F-006 verdict (2026-10-16): NOT VALIDATED (R2 failed on BTC)

Run: `python tools/check_excursion.py BTCUSDT,ETHUSDT 1h` (tool committed in 2131c87 BEFORE the run), output in
research/results/excursion_1h.txt. Criteria applied exactly as pre-registered.

- R1 pooled coverage ok on both: BTC q50/q80/q95 = 48.4/78.6/95.1%, ETH 50.5/79.7/94.5%.
- R2 by risk level: BTC FAIL (low level q80 coverage 72.3%, extreme level q80 87.5%, tolerance +-6 pp);
  ETH ok but at the edge (low 74.5%, high 85.3%, extreme 85.8% for q80).
- R3 by year ok (q95 coverage 93.0-96.5% BTC, 93.5-95.1% ETH).
- R4 monotone medians ok on both (BTC low 175 -> extreme 408 bp; ETH 226 -> 509 bp).
- R5 beats baseline B ok on both at q80 and q95.

Reading: the single global ratio multiplier does not hold across risk levels: quantiles are too narrow in calm
regimes (q80 coverage 72-75% in the low level on both assets) and too wide in wild regimes. q95 stayed within
91.4-97.5% in every level. The BTC extreme-level miss is probably noise (1326 overlapping events ~ 55
independent windows); the low-level miss is not (both assets). The product claim "calibrated within every
risk level" is NOT established; the pooled claim and the q95 level claim hold on this data.
Next: F-007, ratio quantiles estimated per risk level on training data only. Designed AFTER seeing F-006 on
the same data (disclosed); criteria to be fixed and committed before any code; forward data needed before use.

---

## F-007 — Risk sheet v2: excursion ratio quantiles per risk level

**Status:** PRE-REGISTERED (written and committed BEFORE any code or run, 2026-10-16)

**Why this exists.** F-006 failed R2 on BTC: one global multiplier E/expected_range gave q80 coverage of
72-75% in the low risk level and 85-88% in the high/extreme levels (both assets). F-007 estimates the ratio
quantiles separately per risk level.

**DISCLOSURE: designed AFTER seeing F-006 results on the same 2023-2026 data.** The idea (condition the ratio
on the risk level) comes from that failure, so a pass here is weaker evidence than a clean pre-registered
pass. Compensations: it adds no tuned parameter (four per-level quantile sets estimated on training rows only),
all F-006 thresholds are kept unchanged, and R6 below is stricter. Forward data is still required before use.

**Change vs F-006 (nothing else changes):**
- Risk level of a row = trailing rank (window 8760 rows, >= 2000 valid) of the predicted ln(expected range):
  low < 0.25, normal < 0.75, high < 0.95, extreme >= 0.95.
- Training: ratio quantiles q50/q80/q95 of E / expected_range per level, from purged training rows that have a
  defined rank; a level with < 300 training rows falls back to the global ratio quantiles.
- Test rows use their own level (rank is causal). Walk-forward, purge, refit schedule, baseline B: as F-006.

**Criteria (fixed):** R1-R5 exactly as in F-006 (same thresholds, both assets), plus
- R6 R2 holds separately in each half of the test period (decisions before 2025-01-01 and from 2025-01-01),
  on both assets, for every level with >= 300 events in that half (+-6 pp for q80 and q95).

**Verdict rule:** all of R1-R6 on both assets. A fail is recorded; the criteria are not loosened.
**Prior:** R2 likely improves (it is what the change targets); R6 is the real risk because half-period
cells are smaller and noisier. If F-007 fails, the honest product is q95 + risk level only (see F-006 reading).
**Verdict:** pending.

### F-007 verdict (2026-10-16): PASSED R1-R6 on both assets (conditional)

Run: `python tools/check_excursion_v2.py BTCUSDT,ETHUSDT 1h` (tool committed in b3367c1 BEFORE the run, criteria
in fe51359), output in research/results/excursion_v2_1h.txt. Criteria applied exactly as pre-registered.

- R1 pooled coverage ok: BTC q50/q80/q95 = 47.3/77.7/94.8%, ETH 50.0/79.1/94.4% (BTC q50 and q80 sit at the lower edge).
- R2 by risk level ok (worst gap: ETH extreme q80 84.1%, 4.1 pp; BTC extreme q95 92.2%).
- R3 by year ok (q95 coverage BTC 93.4-96.9%, ETH 93.4-96.0%).
- R4 monotone medians ok (BTC low 175 -> extreme 406 bp; ETH 226 -> 507 bp).
- R5 beats baseline B at q80 and q95 on both assets.
- R6 both halves ok (BTC before 2025: q80 coverage ~75% in low/normal/high, gap up to 5.1 pp of the allowed 6;
  from 2025: ~80%).

Reading: weaker evidence than a clean pass, because F-007 was designed after F-006 failed on the same data.
q95 is the reliable number (91.9-97.8% in every level/half cell, both assets). q80 was ~5 pp optimistic on BTC
in 2023-24 and not afterwards, so it must be presented with that caveat. This is calibration of a risk range, not
a direction claim. Forward data is required before real use: the next step is a forward log that stores every
published risk sheet and its realised outcome, with a monthly calibration report.

---

## F-008 — Forward test of the risk sheet (live, out-of-sample)

**Status:** PRE-REGISTERED (written and committed BEFORE any code or any forward sheet, 2026-10-17)

**Question.** Does the F-007 risk sheet (docs/RISK_ANALYST_SPEC.md; per-level ratio quantiles) keep its
calibration on data that did not exist when the model was designed?

**Design.**
- Every hourly close, for BTCUSDT and ETHUSDT 1h, the tool stores one sheet: decision time, expected range,
  q50/q80/q95 of E, trailing rank and risk level, model id (code commit + fit date). Sheets are written to an
  append-only log BEFORE their outcome exists; the outcome E is filled in only when the 24 following candles are
  complete and contiguous. Sheets whose window crosses a data gap are marked void, never repaired.
- Model: the F-007 code frozen at a recorded commit, fitted on all history up to the start date, refitted every
  90 days on data before the refit date (purge of 24 candles). No parameter, threshold or code change during the
  test; a bug fix restarts the test and is disclosed.
- Baseline B: trailing 365-day unconditional quantile of E, as in F-006/F-007.

**Evaluation date.** Not before 120 days AND >= 2000 completed sheets per asset after the start. The monthly
report before that is descriptive only and decides nothing.

**Criteria (fixed; all on both assets, completed sheets only):**
- F1 pooled q95 coverage in [90%, 99%]
- F2 pooled q80 coverage in [72%, 88%]
- F3 pooled q50 coverage in [40%, 60%]
- F4 for every risk level with >= 300 completed sheets: q95 coverage >= 89%
- F5 pinball loss at q80 and q95 lower than baseline B

**Disclosures.** Hourly sheets overlap (24h windows), so 120 days is roughly 120 independent windows: the
standard error of q95 coverage is about 2 pp and of q80 about 3.6 pp. The tolerances are therefore wider than in
F-006/F-007 and can only expose GROSS miscalibration; a pass does not prove fine calibration, and a pass says
nothing about direction. F-007 itself was designed after F-006 on the same history (disclosed there), which is
the reason a forward test is required. Prior: F1 likely holds (q95 was the stable number); F2 is the most likely
to fail (q80 was ~5 pp optimistic on BTC in 2023-24).
**Verdict:** pending (earliest evaluation date: 120 days after the first forward sheet).

### F-008 amendment (2026-10-17): data sources — written before any sheet existed

F-008 did not name the data source. Facts found afterwards: the live Binance endpoints are not reachable from the
author's location (api.binance.com: no answer; data-api.binance.vision: HTTP 451, restricted location); only the
data.binance.vision archives are. Live candles therefore come from Toobit spot market data
(https://api.toobit.com/quote/v1/klines, BTCUSDT and ETHUSDT, 1h, COMPLETED candles only; the forming candle is
dropped). The model is fitted on Binance spot history (archives, through 2026-09-30) and later refits use stored
Toobit candles after that date; sheets, their risk-level history after 2026-09-30 and their outcomes are measured
on Toobit candles. So F-008 additionally tests transfer from Binance-trained parameters to Toobit prices. This is a
clarification of an unspecified item, not a change to any criterion F1-F5, the evaluation date or the freeze rule.
Integrity rules in code (src/forward/store.py): candles are never overwritten (mismatches are counted), a sheet whose
outcome is already knowable is refused as late, a sheet is written once, an outcome window with a hole makes the
sheet void. Tool for the daily run and the report follow in the next commit; no sheet exists before that.

### F-008 amendment 2 (2026-10-17): batch logging — written before any sheet existed

Sheets are published by a daily batch (tools/forward_log.py), not in real time. A run publishes one sheet for each of
the last 24 closed candles. A sheet can therefore be created up to 23 hours after its decision close, when part of its
outcome window is already observable to the logger. Why this does not change the sheet values: a sheet is computed
only from candles up to its own decision (tested: tests/validation/test_forward.py,
test_a_sheet_never_uses_anything_after_its_decision), and all 24 hours of each run are logged, so no sheet is selected.
Why it is still weaker than real-time logging: the logger could in principle have chosen which hours to log. Compensations:
sheets whose full outcome window is already closed are refused (never backfilled); a sheet is written once and never
edited; the sheet table is exported to the repository and committed after each run, so the git history timestamps when
each sheet existed. Hours in days without a run are simply missing (not backfilled); the report must show the logged
share of hours. No criterion F1-F5, evaluation date or freeze rule changes.

### F-008 amendment 3 (2026-10-17): report definitions — written before any outcome existed

The criteria text left three points open; the report (tools/forward_report.py) fixes them as follows, before any
sheet has an outcome. No threshold, date or freeze rule changes.
- "120 days" = from the first sheet's decision to the decision of the newest COMPLETED sheet.
- F1-F5 are judged on each asset separately, pooled over risk levels, and must hold on BOTH assets. F4 applies per
  asset to every level with >= 300 completed sheets.
- Baseline B for F5 is computed on the merged candles (archive + stored Toobit candles) with the same rule as
  F-006/F-007: trailing 8760 rows of E whose outcome was already known at the decision time. A completed sheet whose
  decision time is not among those rows is excluded from F5 and counted in the report. The report also recomputes
  every outcome from the stored candles and prints any difference.
- Before the evaluation date the report prints "DESCRIPTIVE ONLY" and no verdict.

## F-009 — Strategy lab: rule-based direction strategies, Toobit futures costs

**Status:** PRE-REGISTERED (written and committed BEFORE any strategy code and before any hold-out result, 2026-10-18)

**Question.** Does any of the pre-listed rule-based strategies have a direction edge on BTCUSDT/ETHUSDT 1h that
survives realistic futures costs on data that was never used to build it?

**Strategies this round (8, fixed):** S01 trendline break, S05 double top / double bottom, S10 RSI, S12 EMA cross,
S13 support/resistance, S14 Donchian breakout, S15 volatility squeeze breakout, S16 liquidity sweep.
Not tested this round (need a separate registration with their own test count): trendline touch, V pattern,
head-and-shoulders, flags, falling/rising wedges, cup and handle, Fibonacci retracement.
Each strategy is ONE exact rule with textbook default parameters (RSI 14, EMA 20/50, Donchian 20, Bollinger 20/2,
zigzag pivots for patterns). The rule document (docs/STRATEGIES_F009.md) is committed in its own commit BEFORE the
hold-out run. No parameter is tuned on any data. A rule that cannot be made exact is dropped from the list before the run
and reported as "not testable", never changed afterwards.

**Data.** Binance spot 1h archive, BTCUSDT and ETHUSDT. Development part: up to 2024-12-31 23:00 UTC, used only to
check that code runs (unit tests on synthetic data; no performance number is computed on it). Hold-out:
2025-01-01 00:00 to 2026-09-30 23:00 UTC, seen exactly ONCE by one run of all strategies; every result, passing or
failing, is stored in research/results/ and reported.

**Trades.** Signal at a candle close, entry at the next open, long and short, no overlapping trades per strategy and
symbol. Costs: taker fee 0.06% per side (author's Toobit rate), slippage 0.02% per side (assumption), funding from the
stored funding history. Result is also printed at 0.5x and 2x costs as sensitivity; the gate uses the base case.

**Gate A (fixed 1:1):** stop = target = 2 x ATR(14) at entry, timeout 48 candles at market.
**Gate B (natural):** the strategy's own stop and target as written in its rule text.

**Test unit:** strategy x gate, BTC and ETH pooled, long and short pooled. M = 2 x 8 = 16 tests,
alpha = 0.05 / 16 (one-sided).

**Pass conditions (all, both gates):**
- at least 200 trades on the hold-out;
- win rate >= 60%;
- mean net R per trade > 0 after costs;
- one-sided test against break-even gives p < alpha (A: exact binomial test of the win rate against the cost-adjusted
  break-even win rate; B: one-sided t-test of the mean net R).
A strategy that fails any condition is never shown and never sends a signal. Fewer than 200 trades = "unproven", not "failed".

**After a pass:** 120-day live forward test under the F-008 integrity rules (logged before the outcome, exported to git).
Telegram signals carry the hold-out win rate and the live count; if the live result later violates the gate, the strategy
is switched off and the reason is published.

**Disclosures.** Costs make the break-even win rate of gate A roughly 60% (1h stop about 0.8% of price, round-trip cost
0.16%); with 200 trades and alpha = 0.05/16 a win rate of roughly 67-69% is needed. Prior: most likely no strategy
passes; zero passes is a valid result and means no signal is sent. Trades overlap in time, so p-values are somewhat
optimistic. Slippage is an assumption. Hold-out is Binance spot, live data is Toobit. The author chose to cut the list
to 8 strategies and the 60% rule; the effect of the cut on required win rate is small.
**Verdict:** pending.

### F-009 verdict (2026-10-20): NOT VALIDATED — no strategy passed

One look at the hold-out, run on committed code (commit bdc05b3): 1h, BTCUSDT + ETHUSDT, 2025-01-01 00:00 to
2026-09-30 23:00 UTC, M = 16, alpha = 0.05/16, costs taker 0.06% + slippage 0.02% per side plus funding.
Result: PASSED: none. Under the registered rule no strategy x gate sends a signal.
Full table (all 16 rows, sensitivity at 0.5x and 2x costs, skipped counters): research/results/f009_holdout_1h.txt;
every trade: research/results/f009_trades_1h.csv.
Seen in the screen output: double top / bottom under gate B had 150 trades (below the 200 minimum) and is "unproven",
not "failed"; every other row is FAILED or unproven in the file. No criterion, rule or parameter was changed before or
after the run. The hold-out has been seen; a second look at 1h needs a new registration.
