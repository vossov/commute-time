"""De coordinator: één route, alleen binnen het venster opgevraagd.

Per ronde hoogstens twee verzoeken bij TomTom:

  1. vertrek nu — de reistijd met het verkeer van dit moment, de wegen, de
     files en de alternatieven;
  2. aankomst op tijd — alleen als er vandaag een aankomsttijd is die nog
     niet voorbij is. TomTom rekent terug (`arriveAt`) en zegt wanneer je
     moet vertrekken, met het verkeer dat hij voor dat moment verwacht.

Buiten het venster gaat er niets de deur uit: de coordinator slaapt tot het
volgende venster begint (hooguit een uur per keer).

Adressen worden één keer per dag opgezocht (zie adressen.py). Een venster van
06:30 tot 09:30 met een aankomsttijd van 08:30 kost per dag 60 verzoeken,
gemeten met een simulatie van een hele dag (tests/test_coordinator.py): 36
rondes met een routeverzoek, 23 met ook een aankomstberekening (die stopt
zodra de streeftijd voorbij is) en één opzoeking per adres. Ligt de
aankomsttijd aan het eind van het venster, dan zijn het er hoogstens 73. Het
gratis plan staat er 2.500 per dag toe.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import rooster, uitvoer
from .adressen import Zoeker, lijst_via
from .const import (
    CONF_ALTERNATIVES,
    CONF_API_KEY,
    CONF_AVOID,
    CONF_DESTINATION,
    CONF_MARGIN_MINUTES,
    CONF_SCAN_MINUTES,
    CONF_START,
    CONF_STOP_MINUTES,
    CONF_TRAVEL_MODE,
    CONF_VIA,
    DAGEN,
    DEFAULT_SCHEDULE,
    DOMAIN,
    MAX_ALTERNATIVES,
    MAX_MARGIN_MINUTES,
    MAX_SCAN_MINUTES,
    MAX_SLAAP_MINUTEN,
    MAX_STOP_MINUTES,
    MAX_TERUGSCHAKEL_MINUTEN,
    MIN_ALTERNATIVES,
    MIN_MARGIN_MINUTES,
    MIN_SCAN_MINUTES,
    MIN_STOP_MINUTES,
    OPTION_DEFAULTS,
    TERUGSCHAKEL_FACTOR,
    VERMIJD,
    VERSION,
    VERVOER,
)
from .tomtom import GeenRoute, TomTomFout, TomTomGeweigerd, TomTomTeVaak, lees_routes, route_url, vraag
from .waze import waze_link

_LOGGER = logging.getLogger(__name__)

# Herkenbaar, met een adres waar te zien is wat dit is — zoals in
# cycling-next-race. Wie zich bij een bron meldt, hoort te zeggen wie hij is.
AGENT = f"HomeAssistant-commute-time/{VERSION} (+https://github.com/vossov/commute-time)"

# Getallen en hun grenzen; zie `_opt`.
_GRENZEN = {
    CONF_MARGIN_MINUTES: (MIN_MARGIN_MINUTES, MAX_MARGIN_MINUTES),
    CONF_STOP_MINUTES: (MIN_STOP_MINUTES, MAX_STOP_MINUTES),
    CONF_ALTERNATIVES: (MIN_ALTERNATIVES, MAX_ALTERNATIVES),
    CONF_SCAN_MINUTES: (MIN_SCAN_MINUTES, MAX_SCAN_MINUTES),
}


def lees_opties(opties: dict[str, Any]) -> dict[str, Any]:
    """De opties zoals de coordinator ze gebruikt, met onzin teruggezet.

    Een waarde buiten de grenzen, een tekst waar een getal hoort of een
    vervoermiddel dat TomTom niet kent valt terug op de standaard. Zo kan
    een kapotte opslag de route niet omver halen.
    """
    uit: dict[str, Any] = {}
    for sleutel, standaard in OPTION_DEFAULTS.items():
        waarde = opties.get(sleutel, standaard)
        if sleutel in _GRENZEN:
            laag, hoog = _GRENZEN[sleutel]
            try:
                waarde = int(waarde)
            except (TypeError, ValueError):
                waarde = standaard
            if not laag <= waarde <= hoog:
                waarde = standaard
        elif sleutel == CONF_TRAVEL_MODE:
            waarde = waarde if waarde in VERVOER else standaard
        elif sleutel == CONF_AVOID:
            waarde = [v for v in (waarde or []) if v in VERMIJD] if isinstance(waarde, list) else []
        else:
            waarde = str(waarde if waarde is not None else standaard).strip()
        uit[sleutel] = waarde
    # het rooster: alleen bekende dagen, en ontbreekt alles dan de standaard
    schema = {dag: opties.get(dag) for dag in DAGEN if isinstance(opties.get(dag), dict)}
    uit["rooster"] = schema if schema else DEFAULT_SCHEDULE
    return uit


class RouteCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Houdt de toestand van één route bij."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.opties = lees_opties(dict(entry.options))
        self._interval = timedelta(minutes=self.opties[CONF_SCAN_MINUTES])
        self._sessie = async_get_clientsession(hass)
        self._zoeker = Zoeker(hass, self._sessie, self.opties[CONF_API_KEY], AGENT)
        # gaat op True als TomTom een route met tussenstops en alternatieven
        # weigert; zie `_routes_nu`
        self._zonder_alternatieven = False
        self._laatste_fout: str | None = None
        # het teruggeschakelde interval in seconden, of None als alles loopt.
        # Apart bijgehouden en niet uit `update_interval` afgeleid: dat staat
        # na de slaap buiten het venster op "tijd tot het venster begint"
        self._terugschakeling_s: float | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=self._interval,
            config_entry=entry,
        )

    # ── een ronde ────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        nu = dt_util.now()
        plan = rooster.plan_nu(self.opties["rooster"], nu)
        if plan is None:
            volgende = rooster.volgende_begin(self.opties["rooster"], nu)
            self.update_interval = uitvoer.volgende_ronde(
                nu, volgende, timedelta(minutes=MAX_SLAAP_MINUTEN)
            )
            # een nieuw venster begint schoon, ook na een weigering gisteren
            self._terugschakeling_s = None
            return uitvoer.buiten_venster(self.entry.title, nu, volgende)

        try:
            data = await self._bereken(nu, plan)
        except (TomTomGeweigerd, TomTomTeVaak) as err:
            self._terugschakelen()
            self._meld(str(err))
            return uitvoer.fout(self.entry.title, nu, plan, str(err))
        except TomTomFout as err:
            self._terugschakeling_s = None
            self.update_interval = self._interval
            self._meld(str(err))
            return uitvoer.fout(self.entry.title, nu, plan, str(err))

        if self._terugschakeling_s is not None:
            _LOGGER.info("%s: TomTom antwoordt weer; terug naar het gewone ritme", self.entry.title)
        self._terugschakeling_s = None
        self.update_interval = self._interval
        self._laatste_fout = None
        return data

    async def _bereken(self, nu, plan) -> dict[str, Any]:
        o = self.opties
        invoer = [o[CONF_START], *lijst_via(o[CONF_VIA]), o[CONF_DESTINATION]]
        punten = [await self._zoeker.vind(tekst, nu) for tekst in invoer]
        coords = [(p.lat, p.lon) for p in punten]

        routes = await self._routes_nu(coords)
        if not routes:
            raise TomTomFout("TomTom gaf geen route terug")

        route_bij_vertrek = None
        if plan.aankomst is not None:
            streef = rooster.streeftijd(plan.aankomst, o[CONF_MARGIN_MINUTES])
            # is de streeftijd al voorbij, dan valt er niets meer terug te
            # rekenen; het oordeel zegt dan "vertrek nu" of "te laat"
            if rooster.seconden_tussen(streef, nu) > 0:
                data, _ = await vraag(
                    self._sessie,
                    route_url(
                        o[CONF_API_KEY], coords, aankomst=streef,
                        vervoer=o[CONF_TRAVEL_MODE], vermijd=o[CONF_AVOID],
                    ),
                    sleutel=o[CONF_API_KEY], agent=AGENT,
                )
                gevonden = lees_routes(data)
                route_bij_vertrek = gevonden[0] if gevonden else None

        stops = len(punten) - 2
        oordeel = rooster.beoordeel(
            nu=nu,
            doel=plan.aankomst,
            reistijd_nu_s=routes[0]["reistijd_s"],
            stoptijd_s=stops * o[CONF_STOP_MINUTES] * 60,
            vertrek_tomtom=route_bij_vertrek["vertrek"] if route_bij_vertrek else None,
        )
        return uitvoer.berekend(
            route=self.entry.title,
            nu=nu,
            plan=plan,
            oordeel=oordeel,
            routes=routes,
            route_bij_vertrek=route_bij_vertrek,
            punten=[p.als_dict() for p in punten],
            waze=[
                waze_link(p.lat, p.lon, vermijd=o[CONF_AVOID], vervoer=o[CONF_TRAVEL_MODE])
                for p in punten[1:]
            ],
            marge_min=o[CONF_MARGIN_MINUTES],
            stoptijd_min=o[CONF_STOP_MINUTES],
        )

    async def _routes_nu(self, coords) -> list[dict[str, Any]]:
        """De berekening met vertrek nu, met alternatieven als het kan.

        Of TomTom alternatieven geeft bij een route met tussenstops, zegt de
        documentatie niet. Weigert hij met een 400, dan nog één keer zonder;
        lukt dat wel, dan blijft het voor deze route zo tot een herstart.
        """
        o = self.opties
        alternatieven = 0 if self._zonder_alternatieven else o[CONF_ALTERNATIVES]

        async def _vraag(n: int) -> list[dict[str, Any]]:
            data, _ = await vraag(
                self._sessie,
                route_url(
                    o[CONF_API_KEY], coords, alternatieven=n,
                    vervoer=o[CONF_TRAVEL_MODE], vermijd=o[CONF_AVOID],
                ),
                sleutel=o[CONF_API_KEY], agent=AGENT,
            )
            return lees_routes(data)

        try:
            return await _vraag(alternatieven)
        except GeenRoute:
            if alternatieven == 0 or len(coords) <= 2:
                raise
            routes = await _vraag(0)
            _LOGGER.info(
                "%s: TomTom weigert alternatieven bij deze tussenstops; verder zonder",
                self.entry.title,
            )
            self._zonder_alternatieven = True
            return routes

    # ── als TomTom weigert ───────────────────────────────────────────

    def _terugschakelen(self) -> None:
        """Het interval oprekken; harder vragen maakt een weigering erger.

        Telt door vanaf het gewone ritme en niet vanaf `update_interval`. Dat
        laatste stond na de slaap buiten het venster op de tijd tot het
        venster begon, en dan sprong een weigering in de eerste ronde van de
        ochtend meteen naar een uur in plaats van naar drie keer het ritme.
        """
        huidig = self._terugschakeling_s or self._interval.total_seconds()
        nieuw = min(MAX_TERUGSCHAKEL_MINUTEN * 60, huidig * TERUGSCHAKEL_FACTOR)
        self._terugschakeling_s = nieuw
        self.update_interval = timedelta(seconds=nieuw)

    def _meld(self, melding: str) -> None:
        """Eén waarschuwing per soort fout, daarna op debug.

        Een sleutel die geweigerd wordt blijft dat de hele ochtend; elke vijf
        minuten dezelfde waarschuwing helpt niemand.
        """
        if melding != self._laatste_fout:
            _LOGGER.warning("%s: %s", self.entry.title, melding)
            self._laatste_fout = melding
        else:
            _LOGGER.debug("%s: %s", self.entry.title, melding)
