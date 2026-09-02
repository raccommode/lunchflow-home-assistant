"""Base entity for Lunch Flow."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LUNCHFLOW_URL
from .coordinator import LunchFlowDataUpdateCoordinator
from .models import AccountSnapshot


class LunchFlowEntity(CoordinatorEntity[LunchFlowDataUpdateCoordinator]):
    """Base class for entities tied to a Lunch Flow account."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LunchFlowDataUpdateCoordinator, account_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, context=account_id)
        self.account_id = account_id

    @property
    def snapshot(self) -> AccountSnapshot:
        """Return the current account snapshot."""
        return self.coordinator.data[self.account_id]

    @property
    def available(self) -> bool:
        """Return whether the account is present in the latest update."""
        return super().available and self.account_id in self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the bank account."""
        account = self.snapshot.account
        institution = account.get("institution_name") or "Lunch Flow"
        return DeviceInfo(
            identifiers={(DOMAIN, self.account_id)},
            name=account.get("name") or f"Account {self.account_id}",
            manufacturer=institution,
            model=account.get("provider") or "Bank account",
            configuration_url=LUNCHFLOW_URL,
        )
