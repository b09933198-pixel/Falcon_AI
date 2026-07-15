# ADR-009

## Title

Automatic Rule Discovery

## Status

Accepted

## Context

Manual rule registration becomes difficult as the number of Rules grows.

## Decision

Probability Rules are automatically discovered using Python Reflection.

## Consequences

- Zero manual registration
- Fully Open/Closed architecture
- Easier extension
- Cleaner Probability Engine