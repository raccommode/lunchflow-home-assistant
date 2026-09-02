"""Tests for the Lunch Flow API client."""

from datetime import date
from decimal import Decimal

import pytest

from custom_components.lunchflow.api import (
    LunchFlowApiClient,
    LunchFlowAuthenticationError,
    LunchFlowResponseError,
    LunchFlowUnsupportedError,
)


class FakeResponse:
    """Minimal aiohttp response context manager."""

    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def json(self, *, content_type=None):
        return self.payload


class FakeSession:
    """Minimal aiohttp session that records GET requests."""

    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_get_accounts_uses_api_key_header() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "accounts": [
                    {
                        "id": 42,
                        "name": "Checking",
                        "institution_name": "Example Bank",
                        "currency": "cad",
                    }
                ],
                "total": 1,
            },
        )
    )
    client = LunchFlowApiClient(session, "secret", base_url="https://example.test/v1")

    accounts = await client.async_get_accounts()

    assert accounts[0]["id"] == 42
    assert session.calls == [
        (
            "https://example.test/v1/accounts",
            {
                "headers": {"x-api-key": "secret", "Accept": "application/json"},
                "params": None,
            },
        )
    ]


@pytest.mark.asyncio
async def test_balance_is_normalized() -> None:
    session = FakeSession(
        FakeResponse(200, {"balance": {"amount": 1234.56, "currency": "cad"}})
    )
    client = LunchFlowApiClient(session, "secret")

    balance = await client.async_get_balance("account/one")

    assert balance.amount == Decimal("1234.56")
    assert balance.currency == "CAD"
    assert session.calls[0][0].endswith("/accounts/account%2Fone/balance")


@pytest.mark.asyncio
async def test_transactions_send_documented_filters() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "transactions": [
                    {
                        "id": "tx-1",
                        "amount": -12.34,
                        "currency": "CAD",
                        "date": "2026-09-01",
                    }
                ],
                "total": 1,
            },
        )
    )
    client = LunchFlowApiClient(session, "secret")

    transactions = await client.async_get_transactions(
        42,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 9, 2),
        include_pending=True,
    )

    assert transactions[0]["id"] == "tx-1"
    assert session.calls[0][1]["params"] == {
        "from": "2026-08-01",
        "to": "2026-09-02",
        "include_pending": "true",
    }


@pytest.mark.asyncio
async def test_holdings_are_summarized() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "holdings": [{"value": 500}, {"value": 250}],
                "totalValue": 750,
                "currency": "usd",
            },
        )
    )
    client = LunchFlowApiClient(session, "secret")

    holdings = await client.async_get_holdings(42)

    assert holdings.total_value == Decimal("750")
    assert holdings.currency == "USD"
    assert holdings.count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_authentication_errors(status: int) -> None:
    client = LunchFlowApiClient(FakeSession(FakeResponse(status, {})), "bad")

    with pytest.raises(LunchFlowAuthenticationError):
        await client.async_get_accounts()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 501])
async def test_unsupported_holdings(status: int) -> None:
    client = LunchFlowApiClient(FakeSession(FakeResponse(status, {})), "secret")

    with pytest.raises(LunchFlowUnsupportedError):
        await client.async_get_holdings(42)


@pytest.mark.asyncio
async def test_invalid_response_is_rejected() -> None:
    client = LunchFlowApiClient(FakeSession(FakeResponse(200, [])), "secret")

    with pytest.raises(LunchFlowResponseError):
        await client.async_get_accounts()
