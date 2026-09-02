"""Tests for the Lunch Flow config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lunchflow.api import LunchFlowAuthenticationError
from custom_components.lunchflow.const import DOMAIN


async def test_user_flow_creates_entry(hass) -> None:
    with (
        patch(
            "custom_components.lunchflow.config_flow.LunchFlowApiClient.async_get_accounts",
            return_value=[{"id": 42}],
        ),
        patch("custom_components.lunchflow.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "  valid-key  "}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lunch Flow"
    assert result["data"] == {CONF_API_KEY: "valid-key"}


async def test_user_flow_rejects_invalid_key(hass) -> None:
    with patch(
        "custom_components.lunchflow.config_flow.LunchFlowApiClient.async_get_accounts",
        side_effect=LunchFlowAuthenticationError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "bad-key"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_second_entry_is_aborted(hass) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_API_KEY: "existing"},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
