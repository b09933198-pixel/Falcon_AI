# Candle

## Status

Draft

---

# Purpose

The Candle entity is the core market data object used throughout Falcon_AI.

It represents one immutable OHLCV candle independently of any exchange.

---

# Design Goals

- Immutable
- Lightweight
- Exchange-Agnostic
- Strongly Typed
- Self Validating
- Serializable
- High Performance

---

# Fields

timestamp

open

high

low

close

volume

quote_volume

trades

buy_volume

buy_quote_volume

---

# Validation Rules

timestamp >= 0

open >= 0

high >= low

low <= close <= high

volume >= 0

quote_volume >= 0

trades >= 0

buy_volume >= 0

buy_quote_volume >= 0

---

# Factory Methods

from_api()

from_dict()

---

# Export Methods

to_dict()

to_tuple()

---

# Representation

repr()

---

# Thread Safety

Immutable

---

# Performance

Uses:

- dataclass
- slots
- frozen

---

# Dependencies

None

This entity belongs to the Domain layer.

It must never import:

- requests
- api
- pandas
- numpy
- exchange libraries

---

# Used By

Infrastructure

Indicators

Analysis

AI

Storage

Testing