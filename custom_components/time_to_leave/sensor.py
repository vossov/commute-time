"""De sensoren van één route.

  * Reistijd — minuten met het verkeer van nu. Draagt alle attributen die de
    kaart leest. Buiten het venster en bij een fout: onbekend, want een
    getal van uren geleden zou er hetzelfde uitzien als een getal van nu.
  * Vertrektijd — een tijdstip, alleen als er vandaag een aankomsttijd is.
    Daar kun je een automatisering aan hangen ("tien minuten voor
    vertrek een melding").

De attributen gaan niet naar de recorder (`MATCH_ALL`, zoals cycling-next-race
sinds 0.31.4): files en alternatieven van een ochtend terugzoeken heeft
geen zin, en het zou bij elke ronde de database laten groeien. De reistijd
zelf blijft in de historie, met langetermijnstatistiek.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRON, DOMAIN, NAME, VERSION
from .coordinator import RouteCoordinator

# De statussen waarbij er een vertrektijd hoort te zijn.
MET_VERTREK = ("vertrek_om", "vertrek_nu", "te_laat")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RouteCoordinator = entry.runtime_data
    async_add_entities([ReistijdSensor(coordinator), VertrektijdSensor(coordinator)])


class _RouteEntiteit(CoordinatorEntity, SensorEntity):
    """Gedeeld: één apparaat per route, met de route als naam."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RouteCoordinator, soort: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_translation_key = soort
        self._attr_unique_id = f"{entry.entry_id}_{soort}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=NAME,
            model=f"route via {BRON}",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}


class ReistijdSensor(_RouteEntiteit):
    """Minuten rijden als je nu vertrekt."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:car-clock"
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, coordinator: RouteCoordinator) -> None:
        super().__init__(coordinator, "reistijd")

    @property
    def native_value(self) -> int | None:
        waarde = self._data.get("reistijd_min")
        return waarde if isinstance(waarde, int) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self._data)


class VertrektijdSensor(_RouteEntiteit):
    """Wanneer je weg moet om op tijd te zijn."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator: RouteCoordinator) -> None:
        super().__init__(coordinator, "vertrektijd")

    @property
    def native_value(self) -> datetime | None:
        if self._data.get("status") not in MET_VERTREK:
            return None
        waarde = self._data.get("vertrek")
        if not isinstance(waarde, str):
            return None
        try:
            return datetime.fromisoformat(waarde)
        except ValueError:
            return None
