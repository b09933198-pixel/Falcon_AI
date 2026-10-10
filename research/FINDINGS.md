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
