"""Commute Time — rijtijd en vertrektijd voor je routes, op je dashboard.

Instellen gaat via de gebruikersinterface (Instellingen → Apparaten &
Services → Integratie toevoegen), één keer per route. De Lovelace-kaart wordt
hier geregistreerd, zodat je zelf niets aan resources hoeft toe te voegen.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KAART_BESTAND, KAART_URL, VERSION
from .coordinator import RouteCoordinator

if TYPE_CHECKING:  # alleen voor de typecontrole; de tests stubben HA niet zo diep
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
_KAART_GEREGISTREERD = f"{DOMAIN}_kaart_geregistreerd"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Meld de kaart aan zodra de component geladen is.

    Home Assistant zet de verwijzing naar de kaart in de HTML van een pagina
    op het moment dat die wordt opgevraagd. Een pagina die geladen wordt
    vóórdat de verwijzing er is, krijgt hem niet, en toont
    "Configuratiefout" tot je de pagina helemaal opnieuw laadt. Daarom hier
    en niet pas bij de config entry: dat scheelt het hele opstarten van de
    routes, inclusief het eerste verzoek bij TomTom. Zoals bij Stars.
    """
    await _registreer_kaart(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet één route op na toevoegen of na een herstart."""
    # vangnet: is het aanmelden hierboven mislukt, dan gebeurt het alsnog
    await _registreer_kaart(hass)

    coordinator = RouteCoordinator(hass, entry)
    # Bewust `async_refresh` en niet `async_config_entry_first_refresh`. Die
    # laatste gooit ConfigEntryNotReady als de eerste ronde mislukt, en dan
    # staat er een entiteit met `restored: true` zonder enige aanwijzing
    # waarom — zie cycling-next-race. Een route die niet laadt omdat TomTom
    # even hapert helpt niemand; de coordinator probeert het zelf opnieuw.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim op bij verwijderen of herladen.

    Het statische pad en de scriptverwijzing blijven staan: Home Assistant
    kan die pas bij een herstart weer kwijt.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad zodra de opties zijn gewijzigd, zodat ze meteen gelden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _registreer_kaart(hass: HomeAssistant) -> None:
    """Serveer de kaart en laat de frontend hem laden.

    Faalt dit, dan draait de integratie gewoon door: de sensoren zijn
    bruikbaar zonder de kaart.
    """
    if hass.data.get(_KAART_GEREGISTREERD):
        return

    pad = Path(__file__).parent / "www" / KAART_BESTAND
    if not await hass.async_add_executor_job(pad.is_file):
        _LOGGER.warning("Kaartbestand niet gevonden op %s", pad)
        return

    try:
        # `cache_headers=True`: de browser mag de kaart bewaren, want de `?v=`
        # hieronder verandert bij elke versie en is dus een ander adres
        await hass.http.async_register_static_paths(
            [StaticPathConfig(KAART_URL, str(pad), True)]
        )
        add_extra_js_url(hass, f"{KAART_URL}?v={VERSION}")
    except Exception as err:  # noqa: BLE001 — een kaart mag de sensor nooit tegenhouden
        _LOGGER.warning("Kaart registreren mislukt: %s", err)
        return

    hass.data[_KAART_GEREGISTREERD] = True
    _LOGGER.info("Lovelace-kaart aangemeld op %s?v=%s", KAART_URL, VERSION)
