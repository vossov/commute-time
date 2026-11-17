"""De coordinator als geheel: een ronde binnen en buiten het venster.

De echte `_async_update_data`, met een nep-sessie die de voorbeelden uit
TomTom's documentatie teruggeeft. Zo is te zien hoeveel verzoeken een
ronde kost, wat er in het adres staat, en wat er gebeurt als TomTom weigert.
"""
import asyncio
import json
import types
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ROUTE = (FIXTURES / "tomtom_route_documentatie.json").read_text(encoding="utf-8")
GEOCODE = (FIXTURES / "tomtom_geocode_documentatie.json").read_text(encoding="utf-8")


class _Antwoord:
    def __init__(self, status, tekst, headers):
        self.status, self._tekst, self.headers = status, tekst, headers

    async def text(self):
        return self._tekst

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class NepSessie:
    """Geeft per soort verzoek een vast antwoord en onthoudt elk adres."""

    def __init__(self, route=(200, ROUTE), geocode=(200, GEOCODE), headers=None):
        self.route, self.geocode = route, geocode
        self.headers = headers or {}
        self.adressen: list[str] = []

    def get(self, url, **kwargs):
        url = str(url)
        self.adressen.append(url)
        status, tekst = self.geocode if "/geocode/" in url else self.route
        if callable(status):
            status, tekst = status(url)
        return _Antwoord(status, tekst, self.headers)


def _routes(sessie):
    return [u for u in sessie.adressen if "/calculateRoute/" in u]


def _geocodes(sessie):
    return [u for u in sessie.adressen if "/geocode/" in u]


@pytest.fixture
def maak(coordinator_mod, const, tz, monkeypatch):
    """Een coordinator voor één route, met de klok en de sessie in de hand."""
    import sys

    monkeypatch.setattr(
        sys.modules["homeassistant.helpers.location"], "find_coordinates",
        lambda hass, naam: "52.0907,5.1214" if naam == "zone.home" else None,
    )

    def _maak(sessie, nu, **opties):
        monkeypatch.setattr(coordinator_mod, "async_get_clientsession", lambda hass: sessie)
        monkeypatch.setattr(coordinator_mod.dt_util, "now", lambda: nu)
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(latitude=52.09, longitude=5.12),
            states=types.SimpleNamespace(get=lambda e: types.SimpleNamespace(name="Thuis")),
        )
        entry = types.SimpleNamespace(
            title="Naar werk", entry_id="abc",
            options={
                const.CONF_API_KEY: "SLEUTEL",
                const.CONF_START: "zone.home",
                const.CONF_DESTINATION: "Stationsplein 1, Utrecht",
                **const.DEFAULT_SCHEDULE,
                "tuesday": {"show_from": "06:30:00", "show_until": "09:30:00", "arrive_at": "08:30:00"},
                **opties,
            },
        )
        c = coordinator_mod.RouteCoordinator(hass, entry)
        c.update_interval = c._interval
        return c

    return _maak


def _ronde(c):
    return asyncio.run(c._async_update_data())


def test_een_ronde_met_aankomsttijd_kost_twee_routeverzoeken_en_een_geocode(maak, tz):
    sessie = NepSessie()
    nu = datetime(2026, 11, 17, 7, 34, tzinfo=tz)  # dinsdag
    data = _ronde(maak(sessie, nu))

    assert len(_routes(sessie)) == 2
    # zone.home komt uit Home Assistant, alleen de bestemming gaat naar TomTom
    assert len(_geocodes(sessie)) == 1
    assert "Stationsplein%201%2C%20Utrecht" in _geocodes(sessie)[0]

    # de tweede berekening rekent terug vanaf 08:30 min 5 minuten marge
    tweede = dict(parse_qsl(urlsplit(_routes(sessie)[1]).query))
    assert tweede["arriveAt"] == "2026-11-17T08:25:00+01:00"
    assert "maxAlternatives" not in tweede
    eerste = dict(parse_qsl(urlsplit(_routes(sessie)[0]).query))
    assert eerste["maxAlternatives"] == "2"
    assert "arriveAt" not in eerste

    assert data["in_venster"] is True
    assert data["reistijd_min"] == 3
    assert data["via"] == ["Sample Street", "A10"]
    # het voorbeeld vertrekt in 2015: die tijd is voorbij, en nu weggaan
    # haalt 08:30 ruim
    assert data["status"] == "vertrek_nu"
    assert data["punten"][0] == {"invoer": "zone.home", "gevonden": "Thuis", "soort": "entiteit"}
    assert data["punten"][1]["gevonden"] == "2501 Soquel Dr, Santa Cruz, CA 95065"
    assert data["waze_url"].startswith("https://waze.com/ul?ll=36.988440%2C-121.974820&navigate=yes")


def test_de_sleutel_staat_in_elk_verzoek_maar_nergens_in_de_attributen(maak, tz):
    sessie = NepSessie()
    data = _ronde(maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz)))
    assert all("key=SLEUTEL" in u for u in sessie.adressen)
    assert "SLEUTEL" not in json.dumps(data)


def test_buiten_het_venster_gaat_er_niets_de_deur_uit(maak, tz):
    sessie = NepSessie()
    nu = datetime(2026, 11, 17, 12, 0, tzinfo=tz)
    c = maak(sessie, nu)
    data = _ronde(c)
    assert sessie.adressen == []
    assert data["status"] == "buiten_venster"
    assert data["volgend_venster_tekst"] == "morgen 06:30"
    # en hij slaapt tot dat venster, hooguit een uur per keer
    assert c.update_interval == timedelta(hours=1)


def test_vlak_voor_het_venster_slaapt_hij_precies_tot_het_begin(maak, tz):
    c = maak(NepSessie(), datetime(2026, 11, 17, 6, 20, tzinfo=tz))
    _ronde(c)
    assert c.update_interval == timedelta(minutes=10, seconds=5)


def test_een_adres_wordt_maar_een_keer_per_dag_opgezocht(maak, tz):
    sessie = NepSessie()
    c = maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz))
    _ronde(c)
    _ronde(c)
    assert len(_geocodes(sessie)) == 1
    assert len(_routes(sessie)) == 4


def test_no_store_betekent_elke_ronde_opnieuw_zoeken(maak, tz):
    sessie = NepSessie(headers={"Cache-Control": "no-store"})
    c = maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz))
    _ronde(c)
    _ronde(c)
    assert len(_geocodes(sessie)) == 2


def test_zonder_aankomsttijd_een_routeverzoek(maak, tz, const):
    sessie = NepSessie()
    geen_doel = {"tuesday": {"show_from": "06:30:00", "show_until": "09:30:00", "arrive_at": None}}
    data = _ronde(maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz), **geen_doel))
    assert len(_routes(sessie)) == 1
    assert data["status"] == "geen_doel"
    assert data["vertrek"] is None


def test_een_weigering_wordt_een_melding_en_een_trager_ritme(maak, tz):
    sessie = NepSessie(route=(403, ""))
    c = maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz))
    data = _ronde(c)
    assert data["status"] == "fout"
    assert "403" in data["fout"]
    # het adres lukte, de route niet: de kaart zegt welke dienst weigerde
    assert "Routing API" in data["fout"]
    assert "reistijd_min" not in data
    assert c.update_interval == timedelta(minutes=15)
    _ronde(c)
    assert c.update_interval == timedelta(minutes=45)
    _ronde(c)
    assert c.update_interval == timedelta(minutes=60), "hooguit een uur"

    # TomTom antwoordt weer: terug naar vijf minuten
    sessie.route = (200, ROUTE)
    data = _ronde(c)
    assert data["status"] == "vertrek_nu"
    assert c.update_interval == timedelta(minutes=5)


def test_een_onbekend_adres_wordt_een_melding(maak, tz):
    sessie = NepSessie(geocode=(200, json.dumps({"results": []})))
    data = _ronde(maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz)))
    assert data["status"] == "fout"
    assert "Stationsplein 1, Utrecht" in data["fout"]
    assert _routes(sessie) == []


def test_een_persoon_zonder_locatie_wordt_een_melding(maak, tz, const):
    sessie = NepSessie()
    data = _ronde(maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz), **{const.CONF_START: "person.niemand"}))
    assert data["status"] == "fout"
    assert "person.niemand" in data["fout"]


def test_tussenstops_en_alternatieven_die_tomtom_weigert(maak, tz, const):
    """Weigert TomTom alternatieven bij tussenstops, dan één keer zonder, en
    daarna blijft het zo voor deze route."""
    def route(url):
        params = dict(parse_qsl(urlsplit(url).query))
        return (400, "{}") if "maxAlternatives" in params else (200, ROUTE)

    sessie = NepSessie(route=(route, None))
    c = maak(sessie, datetime(2026, 11, 17, 7, 34, tzinfo=tz),
             **{const.CONF_VIA: "Schoolstraat 1, Utrecht", const.CONF_STOP_MINUTES: 5})
    data = _ronde(c)
    assert data["status"] == "vertrek_nu"
    assert data["stops"] == 1
    # drie punten in het pad: thuis, school, werk
    assert unquote(urlsplit(_routes(sessie)[0]).path).count(":") == 2
    assert len(_routes(sessie)) == 3  # met, zonder, en de aankomstberekening
    _ronde(c)
    assert len(_routes(sessie)) == 5  # nu meteen zonder alternatieven
