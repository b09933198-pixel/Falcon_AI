"""
Falcon AI

Strategy Lab

Statistics for the F-009 gates (standard library only)

Version: 1.0.0
"""

from __future__ import annotations

import math
from typing import Sequence


def binom_sf(k: int, n: int, p: float) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, p)."""

    if k <= 0:
        return 1.0

    if k > n:
        return 0.0

    if p <= 0.0:
        return 0.0

    if p >= 1.0:
        return 1.0

    log_p, log_q = math.log(p), math.log(1.0 - p)
    terms = [
        math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * log_p + (n - j) * log_q
        for j in range(k, n + 1)
    ]
    top = max(terms)

    return min(1.0, math.exp(top) * sum(math.exp(t - top) for t in terms))


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the incomplete beta function (modified Lentz)."""

    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap

    if abs(d) < tiny:
        d = tiny

    d = 1.0 / d
    h = d

    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < 1e-14:
            break

    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""

    if x <= 0.0:
        return 0.0

    if x >= 1.0:
        return 1.0

    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    )

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a

    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """P(T >= t) for Student's t with df degrees of freedom."""

    tail = 0.5 * betainc(df / 2.0, 0.5, df / (df + t * t))

    return tail if t >= 0 else 1.0 - tail


def mean_sd(values: Sequence[float]):

    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0

    return mean, math.sqrt(var)


def t_test_positive(values: Sequence[float]) -> float:
    """One-sided p-value for H0: mean <= 0."""

    n = len(values)

    if n < 2:
        return 1.0

    mean, sd = mean_sd(values)

    if sd == 0.0:
        return 0.0 if mean > 0 else 1.0

    return t_sf(mean / (sd / math.sqrt(n)), n - 1)
