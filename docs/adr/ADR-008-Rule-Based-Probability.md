# ADR-008

## Title

Rule-Based Probability Engine

## Status

Accepted

## Context

The Probability Engine must remain independent from indicator logic.

## Decision

Indicator logic is implemented as independent Rules.

ProbabilityEngine executes Rules through RuleRegistry.

## Consequences

- Open/Closed Principle
- Easy extension
- Easier testing
- Enterprise architecture