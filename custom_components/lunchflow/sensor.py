"""Sensor platform for Lunch Flow."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunchFlowRuntimeData
from .const import DEFAULT_TARGET_CURRENCY
from .coordinator import LunchFlowDataUpdateCoordinator
from .entity import LunchFlowEntity
from .exchange_rates import RATE_SOURCE
from .models import LunchFlowTransaction, as_decimal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LunchFlowRuntimeData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Lunch Flow sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    known_entity_ids: set[str] = set()

    @callback
    def async_add_new_accounts() -> None:
        entities: list[SensorEntity] = []
        for account_id, snapshot in coordinator.data.items():
            candidates = [
                LunchFlowBalanceSensor(coordinator, account_id),
                LunchFlowTransactionCountSensor(coordinator, account_id),
                LunchFlowLastTransactionSensor(coordinator, account_id),
            ]
            if coordinator.target_currency != DEFAULT_TARGET_CURRENCY:
                candidates.extend(
                    (
                        LunchFlowConvertedBalanceSensor(coordinator, account_id),
                        LunchFlowConvertedTransactionSensor(coordinator, account_id),
                    )
                )
            if snapshot.holdings is not None:
                candidates.append(LunchFlowHoldingsSensor(coordinator, account_id))
                if coordinator.target_currency != DEFAULT_TARGET_CURRENCY:
                    candidates.append(
                        LunchFlowConvertedHoldingsSensor(coordinator, account_id)
                    )
            for entity in candidates:
                if entity.unique_id not in known_entity_ids:
                    known_entity_ids.add(entity.unique_id)
                    entities.append(entity)
        if entities:
            async_add_entities(entities)

    async_add_new_accounts()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_accounts))


class LunchFlowBalanceSensor(LunchFlowEntity, SensorEntity):
    """Current account balance."""

    _attr_translation_key = "balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash-multiple"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, account_id)
        self._attr_unique_id = f"{account_id}_balance"

    @property
    def native_value(self) -> Decimal:
        """Return the current balance."""
        return self.snapshot.balance.amount

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the balance currency."""
        return self.snapshot.balance.currency

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return account metadata."""
        account = self.snapshot.account
        return {
            "account_status": account.get("status"),
            "institution": account.get("institution_name"),
            "provider": account.get("provider"),
        }


class LunchFlowTransactionCountSensor(LunchFlowEntity, SensorEntity):
    """Number of transactions returned for the configured date range."""

    _attr_translation_key = "transaction_count"
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize the transaction count sensor."""
        super().__init__(coordinator, account_id)
        self._attr_unique_id = f"{account_id}_transaction_count"

    @property
    def native_value(self) -> int:
        """Return the transaction count."""
        return len(self.snapshot.transactions)


class LunchFlowLastTransactionSensor(LunchFlowEntity, SensorEntity):
    """Amount and details of the latest transaction."""

    _attr_translation_key = "last_transaction"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:bank-transfer"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize the latest transaction sensor."""
        super().__init__(coordinator, account_id)
        self._attr_unique_id = f"{account_id}_last_transaction"

    @property
    def _latest_transaction(self) -> LunchFlowTransaction | None:
        transactions = self.snapshot.transactions
        if not transactions:
            return None
        return max(transactions, key=lambda item: str(item.get("date", "")))

    @property
    def native_value(self) -> Decimal | None:
        """Return the latest transaction amount."""
        transaction = self._latest_transaction
        if transaction is None or "amount" not in transaction:
            return None
        try:
            return as_decimal(transaction["amount"])
        except ValueError:
            return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the transaction currency."""
        transaction = self._latest_transaction
        currency = transaction.get("currency") if transaction else None
        return str(currency or self.snapshot.balance.currency).upper()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details useful in automations."""
        transaction = self._latest_transaction
        if transaction is None:
            return {}
        return {
            "transaction_id": transaction.get("id"),
            "date": transaction.get("date"),
            "merchant": transaction.get("merchant"),
            "description": transaction.get("description"),
            "pending": transaction.get("isPending", False),
        }


class LunchFlowHoldingsSensor(LunchFlowEntity, SensorEntity):
    """Total value of investment holdings."""

    _attr_translation_key = "holdings_value"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:chart-line"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize the holdings sensor."""
        super().__init__(coordinator, account_id)
        self._attr_unique_id = f"{account_id}_holdings_value"

    @property
    def native_value(self) -> Decimal | None:
        """Return the total holdings value."""
        holdings = self.snapshot.holdings
        return holdings.total_value if holdings else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the holdings currency."""
        holdings = self.snapshot.holdings
        return holdings.currency if holdings else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the number of holdings included in the total."""
        holdings = self.snapshot.holdings
        return {"holding_count": holdings.count} if holdings else {}


class ConvertedMonetarySensor:
    """Reuse the original monetary sensor while exposing a separate converted entity."""

    def __init__(
        self, coordinator: LunchFlowDataUpdateCoordinator, account_id: str
    ) -> None:
        """Keep a different history for every target currency."""
        super().__init__(coordinator, account_id)
        self._target_currency = coordinator.target_currency
        self._attr_unique_id += f"_converted_{self._target_currency.lower()}"
        self._attr_translation_placeholders = {"currency": self._target_currency}

    @property
    def _conversion_rate(self) -> Decimal | None:
        """Never assume parity when a rate is missing."""
        source = super().native_unit_of_measurement
        if source == self._target_currency:
            return Decimal(1)
        rates = self.snapshot.exchange_rates
        return rates.rate(source, self._target_currency) if rates and source else None

    @property
    def available(self) -> bool:
        """Unknown transactions stay unknown; missing rates are unavailable."""
        return super().available and (
            super().native_value is None or self._conversion_rate is not None
        )

    @property
    def native_value(self) -> Decimal | None:
        """Convert locally without rounding before aggregation."""
        if not super().available:
            return None
        amount = super().native_value
        rate = self._conversion_rate
        if amount is None or not amount.is_finite() or rate is None:
            return None
        return amount * rate

    @property
    def native_unit_of_measurement(self) -> str:
        """Every converted sensor uses the selected target currency."""
        return self._target_currency

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the original money and reference rate for traceability."""
        if not super().available:
            return {}
        amount = super().native_value
        source = super().native_unit_of_measurement
        rate = self._conversion_rate
        rates = self.snapshot.exchange_rates
        return {
            **super().extra_state_attributes,
            "original_amount": (
                float(amount) if amount is not None and amount.is_finite() else None
            ),
            "original_currency": source,
            "exchange_rate": float(rate) if rate is not None else None,
            "exchange_rate_date": (
                rates.reference_date.isoformat()
                if rates is not None and source != self._target_currency
                else None
            ),
            "exchange_rate_source": (
                "Identity (same currency)"
                if source == self._target_currency
                else RATE_SOURCE
            ),
        }


class LunchFlowConvertedBalanceSensor(ConvertedMonetarySensor, LunchFlowBalanceSensor):
    """Account balance in the selected currency."""

    _attr_translation_key = "converted_balance"


class LunchFlowConvertedTransactionSensor(
    ConvertedMonetarySensor, LunchFlowLastTransactionSensor
):
    """Latest transaction valued at the latest reference rate, not its historic rate."""

    _attr_translation_key = "converted_last_transaction"


class LunchFlowConvertedHoldingsSensor(
    ConvertedMonetarySensor, LunchFlowHoldingsSensor
):
    """Investment value in the selected currency."""

    _attr_translation_key = "converted_holdings_value"
