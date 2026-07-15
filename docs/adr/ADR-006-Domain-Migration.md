# ADR-006

## Title

Core Domain Migration

---

## Status

Accepted

---

## Context

Legacy classes currently exist under:

src/models

New enterprise entities are created under:

src/domain/models

Both implementations must coexist temporarily.

---

## Decision

Migration will be performed incrementally.

No direct replacement is allowed.

Compatibility is required before imports change.

---

## Migration Order

1.

Domain Entity

2.

Compatibility Layer

3.

Update Imports

4.

Run Tests

5.

Remove Legacy

---

## Consequences

Migration remains safe.

No interruption of development.

Architecture remains stable.