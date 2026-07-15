# ADR-005

## Title

Mobile Development Environment

---

## Status

Accepted

---

## Context

Falcon_AI is officially developed on Android using:

- Termux
- Python 3.14

Some development tools such as Ruff and recent versions of Mypy require Rust-based compilation, which is not currently practical on Android.

---

## Decision

The project maintains two dependency profiles.

### Mobile

requirements-mobile.txt

Used for:

- Android
- Termux

Contains only pure Python development tools.

---

### Desktop / VPS

requirements-dev.txt

Contains:

- mypy

- ruff

- additional static analysis tools

---

## Consequences

Android development remains lightweight.

Desktop CI performs advanced static analysis.

Core source code remains identical across all platforms.