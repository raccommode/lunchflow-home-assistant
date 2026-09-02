"""Asynchronous client for the Lunch Flow Personal API."""

from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientSession

from .const import LUNCHFLOW_API_URL
from .models import (
    Balance,
    HoldingsSummary,
    LunchFlowAccount,
    LunchFlowTransaction,
    as_decimal,
)


class LunchFlowApiError(Exception):
    """Base exception raised by the Lunch Flow API client."""


class LunchFlowAuthenticationError(LunchFlowApiError):
    """The Lunch Flow API rejected the API key."""


class LunchFlowConnectionError(LunchFlowApiError):
    """The Lunch Flow API could not be reached."""


class LunchFlowResponseError(LunchFlowApiError):
    """The Lunch Flow API returned an invalid or unsuccessful response."""


class LunchFlowUnsupportedError(LunchFlowApiError):
    """The requested endpoint is not supported for this account."""


class LunchFlowApiClient:
    """Small client for the Lunch Flow Personal API."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        *,
        base_url: str = LUNCHFLOW_API_URL,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def async_get_accounts(self) -> list[LunchFlowAccount]:
        """Return every account exposed by the API destination."""
        payload = await self._async_request("/accounts")
        accounts = payload.get("accounts")
        if not isinstance(accounts, list):
            raise LunchFlowResponseError("The accounts response is missing 'accounts'")
        return [account for account in accounts if isinstance(account, dict)]

    async def async_get_balance(self, account_id: int | str) -> Balance:
        """Return the current balance for an account."""
        payload = await self._async_request(
            f"/accounts/{quote(str(account_id), safe='')}/balance"
        )
        balance = payload.get("balance")
        if not isinstance(balance, dict):
            raise LunchFlowResponseError("The balance response is missing 'balance'")
        currency = balance.get("currency")
        if not isinstance(currency, str) or not currency:
            raise LunchFlowResponseError("The balance response has no currency")
        try:
            amount = as_decimal(balance.get("amount"))
        except ValueError as err:
            raise LunchFlowResponseError(
                "The balance response has an invalid amount"
            ) from err
        return Balance(amount=amount, currency=currency.upper())

    async def async_get_transactions(
        self,
        account_id: int | str,
        *,
        date_from: date,
        date_to: date,
        include_pending: bool,
    ) -> list[LunchFlowTransaction]:
        """Return transactions for an account and date range."""
        payload = await self._async_request(
            f"/accounts/{quote(str(account_id), safe='')}/transactions",
            params={
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "include_pending": str(include_pending).lower(),
            },
        )
        transactions = payload.get("transactions")
        if not isinstance(transactions, list):
            raise LunchFlowResponseError(
                "The transactions response is missing 'transactions'"
            )
        return [item for item in transactions if isinstance(item, dict)]

    async def async_get_holdings(self, account_id: int | str) -> HoldingsSummary:
        """Return an investment holdings summary for an account."""
        payload = await self._async_request(
            f"/accounts/{quote(str(account_id), safe='')}/holdings",
            unsupported_statuses={404, 501},
        )
        holdings = payload.get("holdings")
        currency = payload.get("currency")
        if not isinstance(holdings, list):
            raise LunchFlowResponseError("The holdings response is missing 'holdings'")
        if not isinstance(currency, str) or not currency:
            raise LunchFlowResponseError("The holdings response has no currency")
        try:
            total_value = as_decimal(payload.get("totalValue"))
        except ValueError as err:
            raise LunchFlowResponseError(
                "The holdings response has an invalid total value"
            ) from err
        return HoldingsSummary(
            total_value=total_value,
            currency=currency.upper(),
            count=len(holdings),
        )

    async def _async_request(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        unsupported_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request and validate its response."""
        try:
            async with self._session.get(
                f"{self._base_url}{path}",
                headers={"x-api-key": self._api_key, "Accept": "application/json"},
                params=params,
            ) as response:
                if response.status in (401, 403):
                    raise LunchFlowAuthenticationError("Invalid Lunch Flow API key")
                if unsupported_statuses and response.status in unsupported_statuses:
                    raise LunchFlowUnsupportedError(
                        "This endpoint is not supported for the account"
                    )
                if response.status >= 400:
                    raise LunchFlowResponseError(
                        f"Lunch Flow API request failed with HTTP {response.status}"
                    )
                try:
                    payload = await response.json(content_type=None)
                except (TypeError, ValueError) as err:
                    raise LunchFlowResponseError(
                        "Lunch Flow API returned invalid JSON"
                    ) from err
        except LunchFlowApiError:
            raise
        except ClientError as err:
            raise LunchFlowConnectionError("Unable to connect to Lunch Flow") from err

        if not isinstance(payload, dict):
            raise LunchFlowResponseError("Lunch Flow API returned an invalid response")
        return payload
