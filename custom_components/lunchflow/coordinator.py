"""Data update coordinator for Lunch Flow."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    LunchFlowApiClient,
    LunchFlowApiError,
    LunchFlowAuthenticationError,
    LunchFlowUnsupportedError,
)
from .const import (
    CONF_API_KEY,
    CONF_INCLUDE_PENDING,
    CONF_TARGET_CURRENCY,
    CONF_TRANSACTION_DAYS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_INCLUDE_PENDING,
    DEFAULT_TARGET_CURRENCY,
    DEFAULT_TRANSACTION_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SUPPORTED_HOLDINGS_PROVIDERS,
)
from .exchange_rates import ExchangeRateClient, ExchangeRateError
from .models import AccountSnapshot, LunchFlowAccount

_LOGGER = logging.getLogger(__name__)


class LunchFlowDataUpdateCoordinator(DataUpdateCoordinator[dict[str, AccountSnapshot]]):
    """Fetch Lunch Flow data shared by all entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.api = LunchFlowApiClient(
            aiohttp_client.async_get_clientsession(hass), entry.data[CONF_API_KEY]
        )
        self.target_currency = entry.options.get(
            CONF_TARGET_CURRENCY, DEFAULT_TARGET_CURRENCY
        )
        self.exchange_rate_client = ExchangeRateClient(
            aiohttp_client.async_get_clientsession(hass)
        )
        self._include_pending = entry.options.get(
            CONF_INCLUDE_PENDING, DEFAULT_INCLUDE_PENDING
        )
        self._transaction_days = entry.options.get(
            CONF_TRANSACTION_DAYS, DEFAULT_TRANSACTION_DAYS
        )
        update_minutes = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_minutes),
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, AccountSnapshot]:
        """Fetch accounts and their latest financial data."""
        try:
            async with asyncio.timeout(30):
                accounts = await self.api.async_get_accounts()
                snapshots = await asyncio.gather(
                    *(self._async_get_account_snapshot(account) for account in accounts)
                )
        except LunchFlowAuthenticationError as err:
            raise ConfigEntryAuthFailed("Lunch Flow rejected the API key") from err
        except (LunchFlowApiError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with Lunch Flow: {err}") from err

        if self.target_currency != DEFAULT_TARGET_CURRENCY and snapshots:
            try:
                rates = await self.exchange_rate_client.async_get_rates()
            except ExchangeRateError:
                # A separate service outage must not hide original banking data.
                rates = None
                _LOGGER.warning(
                    "No recent exchange rates; "
                    "affected converted sensors are unavailable"
                )
            # Include rates in coordinator equality so FX-only changes update sensors.
            snapshots = [
                replace(snapshot, exchange_rates=rates) for snapshot in snapshots
            ]

        return {
            str(snapshot.account["id"]): snapshot
            for snapshot in snapshots
            if "id" in snapshot.account
        }

    async def _async_get_account_snapshot(
        self, account: LunchFlowAccount
    ) -> AccountSnapshot:
        """Fetch all supported data for one account."""
        account_id = account.get("id")
        if account_id is None:
            raise LunchFlowApiError("Lunch Flow returned an account without an ID")

        today = dt_util.now().date()
        balance, transactions = await asyncio.gather(
            self.api.async_get_balance(account_id),
            self.api.async_get_transactions(
                account_id,
                date_from=today - timedelta(days=self._transaction_days),
                date_to=today,
                include_pending=self._include_pending,
            ),
        )

        holdings = None
        provider = str(account.get("provider", "")).lower()
        if provider in SUPPORTED_HOLDINGS_PROVIDERS:
            try:
                holdings = await self.api.async_get_holdings(account_id)
            except LunchFlowUnsupportedError:
                _LOGGER.debug("Holdings are not available for account %s", account_id)

        return AccountSnapshot(
            account=account,
            balance=balance,
            transactions=tuple(transactions),
            holdings=holdings,
        )
