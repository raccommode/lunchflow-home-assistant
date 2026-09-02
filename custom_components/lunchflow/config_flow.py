"""Config flow for Lunch Flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import config_validation as cv

from .api import (
    LunchFlowApiClient,
    LunchFlowApiError,
    LunchFlowAuthenticationError,
)
from .const import (
    CONF_INCLUDE_PENDING,
    CONF_TARGET_CURRENCY,
    CONF_TRANSACTION_DAYS,
    CONF_UPDATE_INTERVAL,
    CURRENCY_OPTIONS,
    DEFAULT_INCLUDE_PENDING,
    DEFAULT_TARGET_CURRENCY,
    DEFAULT_TRANSACTION_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_TRANSACTION_DAYS,
    MAX_UPDATE_INTERVAL,
    MIN_TRANSACTION_DAYS,
    MIN_UPDATE_INTERVAL,
)


def _options_schema(options: dict[str, Any] | None = None) -> vol.Schema:
    """Build the options schema with current values as defaults."""
    current = options or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_TARGET_CURRENCY,
                default=current.get(CONF_TARGET_CURRENCY, DEFAULT_TARGET_CURRENCY),
            ): vol.In(CURRENCY_OPTIONS),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(
                cv.positive_int,
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
            ),
            vol.Required(
                CONF_TRANSACTION_DAYS,
                default=current.get(CONF_TRANSACTION_DAYS, DEFAULT_TRANSACTION_DAYS),
            ): vol.All(
                cv.positive_int,
                vol.Range(min=MIN_TRANSACTION_DAYS, max=MAX_TRANSACTION_DAYS),
            ),
            vol.Required(
                CONF_INCLUDE_PENDING,
                default=current.get(CONF_INCLUDE_PENDING, DEFAULT_INCLUDE_PENDING),
            ): bool,
        }
    )


class LunchFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Lunch Flow config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up Lunch Flow with a Personal API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await self._async_validate_api_key(api_key)
            if error is None:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Lunch Flow",
                    data={CONF_API_KEY: api_key},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after an invalid API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and save a replacement API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await self._async_validate_api_key(api_key)
            if error is None:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_API_KEY: api_key},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def _async_validate_api_key(self, api_key: str) -> str | None:
        """Validate an API key against the accounts endpoint."""
        client = LunchFlowApiClient(
            aiohttp_client.async_get_clientsession(self.hass), api_key.strip()
        )
        try:
            await client.async_get_accounts()
        except LunchFlowAuthenticationError:
            return "invalid_auth"
        except LunchFlowApiError:
            return "cannot_connect"
        except Exception:
            return "unknown"
        return None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LunchFlowOptionsFlow:
        """Return the options flow handler."""
        return LunchFlowOptionsFlow()


class LunchFlowOptionsFlow(OptionsFlow):
    """Handle Lunch Flow polling options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage Lunch Flow options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self.config_entry.options)),
        )
