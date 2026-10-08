# Falcon_AI Constitution

Status: DRAFT v1 (rebuilt from the Master Document, Oct 8 2026)
Rule: if this file conflicts with the repository, the repository is the truth and this file must be updated.

---

## 1. Identity

Falcon_AI is an Intelligent Trading Analysis System (ITAS) for Toobit.
It is NOT a simple signal bot, NOT an indicator collection, NOT a toy project.

Default scope: BTCUSDT and ETHUSDT. Timeframe roles: direction (1D/4h), structure (1h), entry (15m).
Symbols and timeframes are configuration, never hard-coded. Adding or removing either must need no code change.
A new symbol or timeframe becomes live-eligible only after it passes validation (backtest + forward test).

## 2. Destination

- Input: market data -> multi-layer analysis.
- Output: explainable analysis delivered to Telegram (plus local logs).
- Every output states: the decision, the evidence, and the uncertainty.
- The system does NOT execute trades. Execution is out of scope unless approved later by a full ADR.
- Results and outcomes are recorded (Excel/CSV) so the system can be reviewed and improved.

## 3. Principles (non-negotiable)

1. Quality over speed. Slow and reliable beats fast and fragile.
2. No idea enters the project automatically. Every proposal is reviewed: criticize, fix, accept or reject.
3. The rule is above people. Neither the owner nor the assistant may bypass an approved rule.
4. Both owner and assistant are guardians of the project goal and of quality.
5. No false certainty. Output must reflect probability, evidence and doubt honestly.
6. Simple but powerful. Power must never become uncontrollable complexity.
7. Every capability has a cost (code, tests, maintenance). Add only what earns its place.
8. One indicator is never enough. Conclusions need combined evidence.
9. Every important change is reversible (compare with the previous version, rollback possible).
10. Architectural decisions are recorded (ADR).

## 4. Measurement rules

- No probability, confidence or score may enter the system without measurement on historical data.
- Every experiment must have no lookahead bias and must include fees and slippage.
- Success is judged on data, stability and testing, never on a single good result.
- Versions of the system must be comparable, to know whether a change truly helped.
- No algorithm or score guarantees profit.

## 5. Session rules

1. Start from the real repository state, never from memory or guesswork.
2. Get the full traceback before diagnosing any error. Never guess the cause.
3. Before any change, state which layer it touches and which decision it relates to.
4. Run a minimal run/test after every change.
5. Every session ends with commit AND push.
6. Update the single status file and the relevant ADR if the change is important.
7. After stabilization, pick ONE next step only. No parallel paths.
8. Status percentages come from test results, not from hand-written claims.

## 6. Gate (checklist before adding anything)

PROPOSED, the original Gate questions were lost. Confirm or replace:

1. What concrete problem does this solve?
2. Which layer owns it, and does it respect the layer boundaries?
3. How will it be tested and measured?
4. What is its cost, and is there a simpler way?

An item that fails any question does not enter the project.

## 7. Path

Phase 0: Recovery. Rebuild docs, recover lost tests/datasets, fix status files.
Phase 1: Stabilization + vertical slice. Candle fetch -> storage -> indicators -> analysis -> output, end to end.
Phase 2: Backtesting/validation (moved earlier than the original plan, needs approval).
Phase 3: Analysis engine and scoring, calibrated by measurement.
Phase 4: Explainability + Telegram output.
Phase 5: Logging/learning (record analyses, outcomes).
Phase 6: Periodic review cycles (compare versions, change logic only with evidence).

## 8. Out of scope until approved

Automatic trade execution, capital allocation advice, guaranteed-profit claims.
