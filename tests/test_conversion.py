"""Exercise currency conversion in a real Home Assistant instance with mocked APIs."""

from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lunchflow.const import CONF_TARGET_CURRENCY, DOMAIN
from custom_components.lunchflow.exchange_rates import ExchangeRateError, ExchangeRates
from custom_components.lunchflow.models import Balance, HoldingsSummary

CURRENCIES = {1: "EUR", 2: "USD", 3: "CAD", 4: "BTC"}
RATES = ExchangeRates(
    date(2026, 9, 1), {"EUR": Decimal(1), "USD": Decimal("1.2"), "CAD": Decimal("1.5")}
)


@pytest.fixture
def banking_api():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "custom_components.lunchflow.api.LunchFlowApiClient.async_get_accounts",
                return_value=[
                    {
                        "id": account_id,
                        "name": f"Account {currency}",
                        "currency": currency,
                        "provider": "snaptrade" if account_id == 1 else "gocardless",
                    }
                    for account_id, currency in CURRENCIES.items()
                ],
            )
        )
        stack.enter_context(
            patch(
                "custom_components.lunchflow.api.LunchFlowApiClient.async_get_balance",
                side_effect=lambda account_id: Balance(
                    Decimal(100), CURRENCIES[account_id]
                ),
            )
        )
        stack.enter_context(
            patch(
                "custom_components.lunchflow.api.LunchFlowApiClient.async_get_transactions",
                side_effect=lambda account_id, **kwargs: (
                    [
                        {
                            "id": "tx-1",
                            "amount": -12,
                            "currency": "USD",
                            "date": "2026-08-30",
                            "merchant": "Cafe",
                            "isPending": True,
                        }
                    ]
                    if account_id != 4
                    else []
                ),
            )
        )
        stack.enter_context(
            patch(
                "custom_components.lunchflow.api.LunchFlowApiClient.async_get_holdings",
                return_value=HoldingsSummary(Decimal(200), "USD", 2),
            )
        )
        yield stack.enter_context(
            patch(
                "custom_components.lunchflow.exchange_rates.ExchangeRateClient.async_get_rates",
                return_value=RATES,
            )
        )


async def setup(hass, target=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={CONF_TARGET_CURRENCY: target} if target else {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def states(hass, entry):
    return {
        entity.unique_id: hass.states.get(entity.entity_id)
        for entity in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
    }


async def set_target(hass, entry, target):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET_CURRENCY: target}
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize("target", ["CAD", "EUR", "USD"])
async def test_three_currency_aggregation(hass, banking_api, target):
    entry = await setup(hass, target)
    result = states(hass, entry)
    total = Decimal(0)
    suffix = target.lower()

    for account_id, currency in CURRENCIES.items():
        original = result[f"{account_id}_balance"]
        assert original.state == "100"
        assert original.attributes["unit_of_measurement"] == currency
        converted = result[f"{account_id}_balance_converted_{suffix}"]
        assert converted.attributes["unit_of_measurement"] == target
        if currency == "BTC":
            assert converted.state == "unavailable"
            continue
        rate = RATES.rate(currency, target)
        assert float(converted.state) == pytest.approx(float(100 * rate))
        assert converted.attributes["original_amount"] == 100
        assert converted.attributes["original_currency"] == currency
        assert converted.attributes["exchange_rate"] == pytest.approx(float(rate))
        total += Decimal(converted.state)
    assert float(total) == pytest.approx(
        float(
            sum(
                100 * RATES.rate(currency, target) for currency in ("EUR", "USD", "CAD")
            )
        )
    )

    # Transaction and holdings currencies are independent of the account balance.
    transaction = result[f"1_last_transaction_converted_{suffix}"]
    assert float(transaction.state) == pytest.approx(
        float(-12 * RATES.rate("USD", target))
    )
    assert transaction.attributes["original_currency"] == "USD"
    assert transaction.attributes["merchant"] == "Cafe"
    assert transaction.attributes["pending"] is True
    holdings = result[f"1_holdings_value_converted_{suffix}"]
    assert float(holdings.state) == pytest.approx(
        float(200 * RATES.rate("USD", target))
    )
    assert holdings.attributes["holding_count"] == 2
    assert result["4_last_transaction_converted_" + suffix].state == "unknown"
    banking_api.assert_awaited_once()


async def test_default_does_not_request_rates(hass, banking_api):
    entry = await setup(hass)
    assert not any("_converted_" in key for key in states(hass, entry))
    banking_api.assert_not_awaited()


@pytest.mark.parametrize("target", ["CAD", "EUR", "USD"])
async def test_home_assistant_sum_helper(hass, banking_api, target):
    """The real aggregation helper accepts all converted account currencies."""
    entry = await setup(hass, target)
    result = states(hass, entry)
    entity_ids = [
        result[f"{account_id}_balance_converted_{target.lower()}"].entity_id
        for account_id in (1, 2, 3)
    ]
    flow = await hass.config_entries.flow.async_init(
        "min_max", context={"source": "user"}
    )
    flow = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        {
            "name": "Combined balances",
            "entity_ids": entity_ids,
            "type": "sum",
            "round_digits": 2,
        },
    )
    assert flow["type"] == "create_entry"
    await hass.async_block_till_done()
    combined = hass.states.get("sensor.combined_balances")
    assert combined is not None
    assert combined.attributes["unit_of_measurement"] == target
    expected = sum(
        100 * RATES.rate(currency, target) for currency in ("EUR", "USD", "CAD")
    )
    assert float(combined.state) == pytest.approx(round(float(expected), 2))


async def test_fx_outage_keeps_original_and_same_currency_sensors(hass, banking_api):
    banking_api.side_effect = ExchangeRateError
    entry = await setup(hass, "CAD")
    result = states(hass, entry)
    assert result["1_balance"].state == "100"
    assert result["1_balance_converted_cad"].state == "unavailable"
    assert result["3_balance_converted_cad"].state == "100"
    assert result["3_balance_converted_cad"].attributes["exchange_rate"] == 1
    assert result["1_holdings_value_converted_cad"].state == "unavailable"
    assert result["1_last_transaction_converted_cad"].state == "unavailable"

    banking_api.side_effect = None
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert states(hass, entry)["1_balance_converted_cad"].state == "150.0"


async def test_rate_only_changes_update_entities(hass, banking_api):
    entry = await setup(hass, "CAD")
    banking_api.return_value = ExchangeRates(
        date(2026, 9, 2), {**RATES.rates, "CAD": Decimal("1.8")}
    )
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    converted = states(hass, entry)["1_balance_converted_cad"]
    assert float(converted.state) == 180
    assert converted.attributes["exchange_rate_date"] == "2026-09-02"
    assert states(hass, entry)["1_balance"].state == "100"


async def test_target_changes_reload_and_keep_histories_separate(hass, banking_api):
    entry = await setup(hass, "CAD")
    cad_entity_id = states(hass, entry)["1_balance_converted_cad"].entity_id
    original_entity_id = states(hass, entry)["1_balance"].entity_id

    await set_target(hass, entry, "USD")
    result = states(hass, entry)
    assert result["1_balance_converted_usd"].attributes["unit_of_measurement"] == "USD"
    assert result["1_balance_converted_usd"].entity_id != cad_entity_id
    assert result["1_balance"].entity_id == original_entity_id
    assert (
        hass.states.get(cad_entity_id) is None
        or hass.states.get(cad_entity_id).state == "unavailable"
    )

    banking_api.reset_mock()
    await set_target(hass, entry, "original")
    banking_api.assert_not_awaited()
    assert states(hass, entry)["1_balance"].state == "100"

    await set_target(hass, entry, "CAD")
    assert states(hass, entry)["1_balance_converted_cad"].entity_id == cad_entity_id
