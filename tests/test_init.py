"""Integration setup tests for Lunch Flow."""

from decimal import Decimal
from unittest.mock import patch

from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lunchflow.const import DOMAIN
from custom_components.lunchflow.models import Balance, HoldingsSummary


async def test_setup_creates_account_sensors(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_API_KEY: "valid-key"},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.lunchflow.api.LunchFlowApiClient.async_get_accounts",
            return_value=[
                {
                    "id": 42,
                    "name": "Checking",
                    "institution_name": "Example Bank",
                    "provider": "snaptrade",
                    "currency": "CAD",
                    "status": "ACTIVE",
                }
            ],
        ),
        patch(
            "custom_components.lunchflow.api.LunchFlowApiClient.async_get_balance",
            return_value=Balance(amount=Decimal("1234.56"), currency="CAD"),
        ),
        patch(
            "custom_components.lunchflow.api.LunchFlowApiClient.async_get_transactions",
            return_value=[
                {
                    "id": "tx-1",
                    "accountId": 42,
                    "amount": -12.34,
                    "currency": "CAD",
                    "date": "2026-09-01",
                    "merchant": "Cafe",
                    "description": "Lunch",
                    "isPending": False,
                }
            ],
        ),
        patch(
            "custom_components.lunchflow.api.LunchFlowApiClient.async_get_holdings",
            return_value=HoldingsSummary(
                total_value=Decimal("750"), currency="CAD", count=2
            ),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    lunchflow_entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    states_by_unique_id = {
        entity.unique_id: hass.states.get(entity.entity_id)
        for entity in lunchflow_entities
    }

    assert set(states_by_unique_id) == {
        "42_balance",
        "42_holdings_value",
        "42_last_transaction",
        "42_transaction_count",
    }
    assert states_by_unique_id["42_balance"].state == "1234.56"
    assert states_by_unique_id["42_transaction_count"].state == "1"
    assert states_by_unique_id["42_last_transaction"].attributes["merchant"] == "Cafe"
    assert states_by_unique_id["42_holdings_value"].attributes["holding_count"] == 2

    assert await hass.config_entries.async_unload(entry.entry_id)
