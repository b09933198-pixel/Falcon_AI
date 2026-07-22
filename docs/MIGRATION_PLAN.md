# MIGRATION PLAN

Version: 1.0

Status: Active

---

# Purpose

This document tracks all temporary compatibility layers and legacy components.

No legacy component may be removed until its replacement is fully validated.

---

# Legacy Components

## 1. src/models

Status:
Legacy Compatibility Layer

Replacement:

src/domain/models

Removal Condition:

No remaining imports from src.models.

Target Version:

2.0

---

## 2. src/indicators

Status:

Legacy Indicator Layer

Replacement:

src/analysis/indicators

Removal Condition:

All indicators migrated.

All tests passing.

Target Version:

2.0

---

# Migration Rules

- Never remove legacy code before migration completes.
- Every migration must preserve compatibility.
- Every migration requires testing.
- Every removal must be documented in CHANGELOG.

---

# Current Progress

Models

Enterprise Complete

Legacy Active

Indicators

Enterprise Active

Legacy Active

Migration Status

In Progress

---

Approved

Falcon AI Architecture