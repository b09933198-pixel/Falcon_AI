# ADR-009

## Title

Indicator Hierarchy

---

## Status

Accepted

---

## Context

Indicators have different responsibilities.

Trend indicators.

Oscillators.

Volume indicators.

Liquidity indicators.

Keeping all indicators under a single base class reduces scalability.

---

## Decision

Falcon AI introduces a hierarchy.

Indicator

↓

TrendIndicator

Oscillator

VolumeIndicator

LiquidityIndicator

ProbabilityIndicator

---

## Consequences

Clear architecture.

Better extensibility.

Reduced coupling.

Future AI integration becomes easier.