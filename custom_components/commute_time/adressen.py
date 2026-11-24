"""Van wat je intypt naar een punt op de kaart.

Drie soorten invoer, in deze volgorde geprobeerd:

  1. een entiteit — `zone.home`, `person.wil`, `device_tracker.auto`. Home
     Assistant weet zelf waar die is (`find_coordinates`), dus TomTom hoeft
     er niets voor te doen. Een persoon zonder locatie is een fout, geen
     reden om naar een adres te gaan zoeken.
  2. een coördinaat — `52.0907, 5.1214`.
  3. een adres — opgezocht bij TomTom.

Wat TomTom vindt wordt **niet** opgeslagen in de instellingen, alleen wat
je intypte. TomTom's voorwaarden staan achter een inlog en zijn hier niet
gelezen; een concurrent schrijft dat TomTom opslag verbiedt en caching
alleen toestaat zolang de `Cache-Control` van het antwoord dat zegt. Dus:
in het geheugen, hooguit tot middernacht, en korter als TomTom dat vraagt.
Dat kost één verzoek per adres per dag.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .const import MAX_VIA
from .rooster import plus, seconden_tussen
from .tomtom import AdresNietGevonden, bewaartijd_s, geocode_url, lees_geocode, vraag

ENTITEIT = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
COORDINAAT = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


def is_entiteit(tekst: str) -> bool:
    return bool(ENTITEIT.match(str(tekst).strip()))


def lees_coordinaat(tekst: str | None) -> tuple[float, float] | None:
    """`52.09,5.12` → (52.09, 5.12); alles wat geen geldige plek is → None."""
    if not tekst:
        return None
    gevonden = COORDINAAT.match(str(tekst))
    if not gevonden:
        return None
    lat, lon = float(gevonden.group(1)), float(gevonden.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def lijst_via(tekst: str | None) -> list[str]:
    """Tussenstops: één per regel, of gescheiden door een puntkomma.

    Geen komma als scheiding — die staat in vrijwel elk adres.
    """
    if not tekst:
        return []
    delen = re.split(r"[\n;]", str(tekst))
    return [d.strip() for d in delen if d.strip()][:MAX_VIA]


@dataclass
class Punt:
    """Een plek op de route, met wat er gevonden is."""

    invoer: str
    lat: float
    lon: float
    gevonden: str
    soort: str  # "entiteit", "coordinaat" of "adres"

    @property
    def naam(self) -> str:
        """Hoe de kaart hem noemt: wat je intypte, behalve bij een entiteit."""
        return self.gevonden if self.soort == "entiteit" else self.invoer

    def als_dict(self) -> dict[str, Any]:
        return {
            "invoer": self.invoer,
            "gevonden": self.gevonden,
            "soort": self.soort,
            "naam": self.naam,
        }


class EntiteitZonderLocatie(AdresNietGevonden):
    """Een entiteit die (nu) geen locatie heeft."""


class Zoeker:
    """Zoekt punten op, met een dagcache voor adressen.

    `hass` is er alleen voor de entiteiten en de voorkeurslocatie; zonder
    hass (in tests) werken coördinaten en adressen gewoon.
    """

    def __init__(self, hass: Any, sessie: Any, sleutel: str, agent: str) -> None:
        self._hass = hass
        self._sessie = sessie
        self._sleutel = sleutel
        self._agent = agent
        self._cache: dict[str, tuple[Punt, datetime]] = {}

    async def vind(self, tekst: str, nu: datetime | None = None) -> Punt:
        tekst = str(tekst).strip()
        if is_entiteit(tekst):
            return self._entiteit(tekst)
        plek = lees_coordinaat(tekst)
        if plek is not None:
            return Punt(tekst, plek[0], plek[1], tekst, "coordinaat")
        if nu is not None:
            bewaard = self._cache.get(tekst)
            if bewaard is not None and seconden_tussen(bewaard[1], nu) > 0:
                return bewaard[0]
        return await self._adres(tekst, nu)

    def _entiteit(self, entiteit: str) -> Punt:
        from homeassistant.helpers.location import find_coordinates

        uitkomst = find_coordinates(self._hass, entiteit)
        plek = lees_coordinaat(uitkomst)
        if plek is None:
            raise EntiteitZonderLocatie(f"{entiteit} heeft nu geen locatie", "geen_locatie", entiteit=entiteit)
        staat = self._hass.states.get(entiteit) if self._hass else None
        naam = staat.name if staat is not None and getattr(staat, "name", None) else entiteit
        return Punt(entiteit, plek[0], plek[1], naam, "entiteit")

    async def _adres(self, tekst: str, nu: datetime | None) -> Punt:
        lat = lon = None
        if self._hass is not None:
            lat, lon = self._hass.config.latitude, self._hass.config.longitude
        data, headers = await vraag(
            self._sessie,
            geocode_url(self._sleutel, tekst, lat=lat, lon=lon),
            sleutel=self._sleutel,
            agent=self._agent,
        )
        gevonden = lees_geocode(data)
        if gevonden is None:
            raise AdresNietGevonden(f"TomTom vindt geen adres bij “{tekst}”", "geen_adres", adres=tekst)
        punt = Punt(tekst, gevonden["lat"], gevonden["lon"], gevonden["adres"] or tekst, "adres")
        if nu is not None:
            tot = bewaren_tot(nu, headers)
            if tot is not None:
                self._cache[tekst] = (punt, tot)
        return punt


def bewaren_tot(nu: datetime, headers: dict[str, str]) -> datetime | None:
    """Tot wanneer een gevonden adres in het geheugen mag blijven.

    Tot middernacht, of korter als `Cache-Control` dat zegt. `no-store` of
    `max-age=0` betekent: niet bewaren, dan wordt elke ronde opnieuw gezocht.
    """
    middernacht = (nu + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    kop = next((v for k, v in headers.items() if k.lower() == "cache-control"), None)
    seconden = bewaartijd_s(kop)
    if seconden == 0:
        return None
    if seconden is None:
        return middernacht
    verloopt = plus(nu, seconden)
    return verloopt if seconden_tussen(middernacht, verloopt) > 0 else middernacht
