# ADR-007

## Title

Analysis Engine Structure

---

## Status

Accepted

---

## Context

Indicators are analytical components.

They are not independent modules.

---

## Decision

All indicators belong to:

src/analysis/indicators

Legacy folder:

src/indicators

exists only during migration.

---

## Consequences

Single location

Cleaner architecture

Scalable analysis engine

No duplicated logic