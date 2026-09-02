"""Rate validation, caching, and privacy tests."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError

from custom_components.lunchflow.exchange_rates import (
    ExchangeRateClient,
    ExchangeRateError,
    parse_rates,
)

TODAY = date(2026, 9, 2)


def payload():
    return {
        "base": "EUR",
        "amount": 1,
        "date": "2026-09-01",
        "rates": {"USD": 1.2, "CAD": 1.5},
    }


def mock_session(body=None, status=200):
    response = AsyncMock()
    response.status = status
    response.json.return_value = payload() if body is None else body
    response.__aenter__.return_value = response
    session = Mock()
    session.get.return_value = response
    return session, response


def test_cross_rates():
    rates = parse_rates(payload(), TODAY)
    assert rates.rate("EUR", "CAD") == Decimal("1.5")
    assert rates.rate("USD", "CAD") == Decimal("1.25")
    assert rates.rate("CAD", "USD") == Decimal("0.8")
    assert rates.rate("CAD", "CAD") == Decimal(1)
    assert rates.rate("BTC", "CAD") is None
    assert rates.rate("CAD", "BTC") is None
    assert rates.reference_date == date(2026, 9, 1)


@pytest.mark.parametrize(
    "override",
    [
        {"base": "USD"},
        {"amount": 100},
        {"amount": True},
        {"date": "invalid"},
        {"date": None},
        {"date": "2026-09-03"},
        {"date": "2026-08-25"},
        {"rates": []},
        {"rates": {}},
        {"rates": {"USD": 0}},
        {"rates": {"USD": -1}},
        {"rates": {"USD": None}},
        {"rates": {"USD": True}},
        {"rates": {"USD": "NaN"}},
        {"rates": {"USD": "Infinity"}},
        {"rates": {"EUR": 2}},
        {"rates": {"usd": 1.2}},
    ],
)
def test_reject_invalid_rates(override):
    with pytest.raises(ExchangeRateError):
        parse_rates({**payload(), **override}, TODAY)


@pytest.mark.parametrize("body", [None, [], "error"])
def test_reject_invalid_payload(body):
    with pytest.raises(ExchangeRateError):
        parse_rates(body, TODAY)


async def test_cache_and_request_privacy(freezer):
    freezer.move_to("2026-09-02T00:00:00Z")
    session, _ = mock_session()
    client = ExchangeRateClient(session)
    first = await client.async_get_rates()
    freezer.move_to("2026-09-02T05:59:00Z")
    assert await client.async_get_rates() is first
    session.get.assert_called_once()
    kwargs = session.get.call_args.kwargs
    assert kwargs["params"] == {"base": "EUR"}
    assert kwargs["headers"] == {"Accept": "application/json"}
    assert kwargs["timeout"].total == 10
    assert kwargs["allow_redirects"] is False

    freezer.move_to("2026-09-02T06:00:00Z")
    await client.async_get_rates()
    assert session.get.call_count == 2


@pytest.mark.parametrize("status", [301, 403, 429, 500])
async def test_http_failure_without_cache(freezer, status):
    freezer.move_to("2026-09-02T00:00:00Z")
    session, _ = mock_session(status=status)
    with pytest.raises(ExchangeRateError):
        await ExchangeRateClient(session).async_get_rates()


@pytest.mark.parametrize("error", [ClientError(), TimeoutError(), ValueError()])
async def test_transport_or_json_failure_without_cache(freezer, error):
    freezer.move_to("2026-09-02T00:00:00Z")
    session, response = mock_session()
    response.json.side_effect = error
    with pytest.raises(ExchangeRateError):
        await ExchangeRateClient(session).async_get_rates()


async def test_outage_cache_expires_by_reference_date(freezer):
    freezer.move_to("2026-09-02T00:00:00Z")
    session, response = mock_session()
    client = ExchangeRateClient(session)
    first = await client.async_get_rates()
    response.status = 503

    freezer.move_to("2026-09-08T00:00:00Z")
    assert await client.async_get_rates() is first  # Seven days since publication.
    freezer.move_to("2026-09-09T00:00:00Z")
    with pytest.raises(ExchangeRateError):
        await client.async_get_rates()


async def test_weekend_reference_date_is_accepted(freezer):
    freezer.move_to("2026-09-06T00:00:00Z")  # Sunday, with Friday's rates.
    body = {**payload(), "date": "2026-09-04"}
    session, _ = mock_session(body)
    rates = await ExchangeRateClient(session).async_get_rates()
    assert rates.reference_date == date(2026, 9, 4)
