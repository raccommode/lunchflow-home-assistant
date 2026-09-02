"""Data models for Lunch Flow."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict

from .exchange_rates import ExchangeRates


class LunchFlowAccount(TypedDict, total=False):
    """A Lunch Flow bank account."""

    id: int | str
    connection_id: int | str
    name: str
    institution_name: str
    institution_logo: str
    provider: str
    currency: str
    status: str


class LunchFlowTransaction(TypedDict, total=False):
    """A Lunch Flow transaction."""

    id: str
    accountId: int | str
    amount: int | float | str
    currency: str
    date: str
    merchant: str
    description: str
    isPending: bool


class LunchFlowHolding(TypedDict, total=False):
    """A Lunch Flow investment holding."""

    security: dict[str, Any]
    quantity: int | float
    price: int | float
    value: int | float
    costBasis: int | float
    currency: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Balance:
    """A normalized account balance."""

    amount: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class HoldingsSummary:
    """A normalized investment holdings summary."""

    total_value: Decimal
    currency: str
    count: int


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Current data for one Lunch Flow account."""

    account: LunchFlowAccount
    balance: Balance
    transactions: tuple[LunchFlowTransaction, ...]
    holdings: HoldingsSummary | None
    exchange_rates: ExchangeRates | None = None


def as_decimal(value: object) -> Decimal:
    """Convert an API numeric value to Decimal without binary float artifacts."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as err:
        raise ValueError(f"Invalid numeric value: {value!r}") from err
