"""
Falcon AI

Trading Account

Version: 1.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Account:

    balance: float

    equity: float

    free_margin: float

    leverage: float

    currency: str = "USD"

    def as_dict(self):

        return {

            "balance": self.balance,

            "equity": self.equity,

            "free_margin": self.free_margin,

            "leverage": self.leverage,

            "currency": self.currency,

        }