"""
Falcon AI

Volatility

Validated volatility forecasting for the risk layer: expected range, an upper
bound for stop distance, position size and no-trade filters. Nothing in this
package generates trade direction.
"""

from .forecaster import (
    BASE_FEATURES,
    VolatilityError,
    VolatilityForecast,
    VolatilityForecaster,
    VolatilityTable,
    build_table,
)

__all__ = [
    "BASE_FEATURES",
    "VolatilityError",
    "VolatilityForecast",
    "VolatilityForecaster",
    "VolatilityTable",
    "build_table",
]
