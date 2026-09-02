"""The Lunch Flow integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import LunchFlowDataUpdateCoordinator


@dataclass(slots=True)
class LunchFlowRuntimeData:
    """Runtime data for a Lunch Flow config entry."""

    coordinator: LunchFlowDataUpdateCoordinator


LunchFlowConfigEntry = ConfigEntry[LunchFlowRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: LunchFlowConfigEntry) -> bool:
    """Set up Lunch Flow from a config entry."""
    coordinator = LunchFlowDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = LunchFlowRuntimeData(coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LunchFlowConfigEntry) -> bool:
    """Unload a Lunch Flow config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: LunchFlowConfigEntry
) -> None:
    """Reload Lunch Flow when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
