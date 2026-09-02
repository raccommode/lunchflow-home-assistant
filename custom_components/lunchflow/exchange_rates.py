"""Public exchange rates; no banking data or credentials leave Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from aiohttp import ClientError, ClientSession, ClientTimeout

RATE_URL = "https://api.frankfurter.dev/v1/latest"
RATE_SOURCE = "Frankfurter (ECB)"
REFRESH_INTERVAL = timedelta(hours=6)
MAX_RATE_AGE = timedelta(days=7)
_LOGGER = logging.getLogger(__name__)


class ExchangeRateError(Exception):
    """Exchange rates could not be retrieved or safely used."""


@dataclass(frozen=True, slots=True)
class ExchangeRates:
    """Rates quoted against EUR for a single reference date."""

    reference_date: date
    rates: dict[str, Decimal]

    def is_fresh(self, today: date) -> bool:
        """Allow weekends and holidays, but never use indefinitely old rates."""
        return timedelta(0) <= today - self.reference_date <= MAX_RATE_AGE

    def rate(self, source: str, target: str) -> Decimal | None:
        """Return units of target currency per one source currency."""
        if source == target:
            return Decimal(1)
        if source not in self.rates or target not in self.rates:
            return None
        return self.rates[target] / self.rates[source]


def parse_rates(payload: object, today: date) -> ExchangeRates:
    """Validate the documented Frankfurter v1 response before converting money."""
    if not isinstance(payload, dict) or payload.get("base") != "EUR":
        raise ExchangeRateError("Invalid exchange-rate base")
    if isinstance(payload.get("amount"), bool) or payload.get("amount") != 1:
        raise ExchangeRateError("Invalid exchange-rate base amount")
    try:
        reference_date = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError) as err:
        raise ExchangeRateError("Invalid exchange-rate date") from err

    raw_rates = payload.get("rates")
    if not isinstance(raw_rates, dict) or not raw_rates:
        raise ExchangeRateError("Missing exchange rates")
    rates = {"EUR": Decimal(1)}
    for currency, value in raw_rates.items():
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isascii()
            or not currency.isalpha()
            or not currency.isupper()
        ):
            raise ExchangeRateError("Invalid exchange-rate currency")
        try:
            rate = Decimal(str(value))
        except ArithmeticError as err:
            raise ExchangeRateError("Invalid exchange-rate value") from err
        if not rate.is_finite() or rate <= 0 or (currency == "EUR" and rate != 1):
            raise ExchangeRateError("Invalid exchange-rate value")
        rates[currency] = rate

    result = ExchangeRates(reference_date, rates)
    if not result.is_fresh(today):
        raise ExchangeRateError("Exchange rates are too old or future-dated")
    return result


class ExchangeRateClient:
    """Fetch and cache one public rate table for all accounts."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize without any Lunch Flow authentication data."""
        self._session = session
        self._cached: ExchangeRates | None = None
        self._fetched_at: datetime | None = None

    async def async_get_rates(self) -> ExchangeRates:
        """Refresh every six hours; use dated cache during a short outage."""
        now = datetime.now(UTC)
        if (
            self._cached is not None
            and self._cached.is_fresh(now.date())
            and self._fetched_at is not None
            and now - self._fetched_at < REFRESH_INTERVAL
        ):
            return self._cached

        try:
            async with self._session.get(
                RATE_URL,
                params={"base": "EUR"},
                headers={"Accept": "application/json"},
                timeout=ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    raise ExchangeRateError(
                        f"Exchange-rate request failed with HTTP {response.status}"
                    )
                payload = await response.json()
            rates = parse_rates(payload, now.date())
        except (ExchangeRateError, ClientError, TimeoutError, ValueError) as err:
            if self._cached is not None and self._cached.is_fresh(now.date()):
                _LOGGER.warning(
                    "Exchange-rate refresh failed; using cached rates dated %s",
                    self._cached.reference_date,
                )
                return self._cached
            raise ExchangeRateError("No recent exchange rates are available") from err

        self._cached = rates
        self._fetched_at = now
        return rates
