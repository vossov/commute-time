"""TomTom: adressen opzoeken en routes berekenen.

Hier zit geen Home Assistant in; alles behalve `vraag` is een pure functie
en wordt in tests/test_tomtom.py los gecontroleerd.

Twee diensten, allebei met één sleutel uit het gratis Freemium-plan:

  * Search API, geocode — een ingetypt adres wordt een coördinaat.
  * Routing API, calculateRoute — reistijd met verkeer, de wegen waarover
    de route loopt, de files erop, en met `arriveAt` hoe laat je moet
    vertrekken om op tijd te zijn.

Nagekeken in de documentatie van TomTom op 16 november 2026 (opgeslagen
voorbeelden in tests/fixtures/, met een README over wat daaraan veranderd
is). Niet nagekeken tegen een echt antwoord: daarvoor is een sleutel nodig,
en die is er in de ontwikkelomgeving niet.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode

import aiohttp

_LOGGER = logging.getLogger(__name__)

ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute/{punten}/json"
GEOCODE_URL = "https://api.tomtom.com/search/2/geocode/{zoek}.json"
TIMEOUT_S = 20

# De drie belangrijkste wegen noemen we op de kaart. TomTom nummert ze zelf
# op belang (`importantRoadStretchIndex`, 0 is het belangrijkst) en zegt er
# letterlijk bij dat dat is om er minder te kunnen tonen.
MAX_WEGEN = 3

# Onze sleutels (kleine letters, voor hassfest) naar wat TomTom verwacht.
VERMIJD_TOMTOM = {
    "toll_roads": "tollRoads",
    "motorways": "motorways",
    "ferries": "ferries",
    "unpaved_roads": "unpavedRoads",
}

# `simpleCategory` van een verkeerssectie; meer kent TomTom er niet.
CATEGORIE = {
    "JAM": "file",
    "ROAD_WORK": "werk in uitvoering",
    "ROAD_CLOSURE": "afsluiting",
    "OTHER": "hinder",
}


# Elke code die een TomTomFout kan dragen, met de parameters die erbij horen.
# De kaart heeft voor elke code een zin in elke taal; tests/test_kaart.py faalt
# als er een ontbreekt.
FOUTCODES = {
    "geweigerd": ("dienst", "detail"),
    "te_vaak": (),
    "geen_route": ("detail",),
    "status": ("status",),
    "onverwacht": (),
    "time_out": ("seconden",),
    "onbereikbaar": ("detail",),
    "geen_adres": ("adres",),
    "geen_locatie": ("entiteit",),
    "geen_routes": (),
}


class TomTomFout(Exception):
    """Iets ging mis bij TomTom. De tekst is voor het logboek.

    `code` en `param` zijn voor de kaart: die toont de melding in de taal die
    de gebruiker koos, en kan dat niet met een kant-en-klare zin. De codes
    staan in FOUTCODES; de kaart heeft voor elk een zin (tests/test_kaart.py
    bewaakt dat). Zonder code toont de kaart de tekst zoals hij is.
    """

    def __init__(self, bericht: str, code: str = "", **param: Any) -> None:
        super().__init__(bericht)
        self.code = code
        self.param = {k: v for k, v in param.items() if v not in (None, "")}


class TomTomGeweigerd(TomTomFout):
    """403: sleutel ongeldig, voor dit product niet aangezet, of het
    dagkwotum is op.

    `dienst` zegt welke van onze twee aanroepen TomTom weigerde ("search" of
    "routing"; leeg als dat niet te zien was). Zonder dat is een geweigerde
    sleutel niet uit elkaar te halen van een ontbrekend product, en bleef er
    alleen raden over welke vinkjes in het portaal aan moesten.
    """

    def __init__(self, bericht: str, dienst: str = "", detail: str = "") -> None:
        super().__init__(bericht, "geweigerd", dienst=dienst, detail=detail)
        self.dienst = dienst


class TomTomTeVaak(TomTomFout):
    """429: te veel verzoeken in korte tijd voor deze sleutel."""


class GeenRoute(TomTomFout):
    """400 bij een route: de punten zijn niet over de weg verbonden, of er
    ligt geen weg in de buurt van een van de punten."""


class AdresNietGevonden(TomTomFout):
    """TomTom kent het ingetypte adres niet."""


# ── adressen in een verzoek ──────────────────────────────────────────


def punten_pad(punten: list[tuple[float, float]]) -> str:
    """`lat,lon:lat,lon:…`, zoals calculateRoute het in het pad verwacht."""
    return ":".join(f"{lat:.6f},{lon:.6f}" for lat, lon in punten)


def route_url(
    sleutel: str,
    punten: list[tuple[float, float]],
    *,
    aankomst: datetime | None = None,
    alternatieven: int = 0,
    vervoer: str = "car",
    vermijd: list[str] | tuple[str, ...] = (),
    taal: str = "nl-NL",
) -> str:
    """Het volledige adres voor één routeberekening, al gecodeerd.

    `urlencode` en niet de parameters van aiohttp: een aankomsttijd draagt
    een tijdzone als `+01:00`, en een `+` die niet als `%2B` de deur uit gaat
    leest de server als een spatie. Dan ligt de aankomsttijd een uur naast
    de bedoeling, zonder foutmelding.
    """
    if len(punten) < 2:
        raise ValueError("een route heeft minstens een begin en een eind")
    params: list[tuple[str, str]] = [
        ("key", sleutel),
        # standaard al true, maar het hele idee hangt eraan
        ("traffic", "true"),
        ("routeType", "fastest"),
        ("travelMode", vervoer),
        # zonder de punten van de lijn: die tekenen we niet, en ze maken het
        # antwoord tientallen keren zo groot
        ("routeRepresentation", "summaryOnly"),
        # ook de reistijd zonder verkeer en die volgens het gebruikelijke
        # verkeer op dit uur, zodat de kaart "normaal 31 min" kan zeggen
        ("computeTravelTimeFor", "all"),
        ("sectionType", "traffic"),
        ("sectionType", "importantRoadStretch"),
        ("language", taal),
    ]
    if alternatieven > 0:
        params.append(("maxAlternatives", str(int(alternatieven))))
    for soort in vermijd:
        if soort in VERMIJD_TOMTOM:
            params.append(("avoid", VERMIJD_TOMTOM[soort]))
    if aankomst is not None:
        if aankomst.tzinfo is None:
            # zonder zone neemt TomTom de tijdzone van de bestemming aan; dat
            # klopt meestal, maar we willen niet op "meestal" leunen
            raise ValueError("aankomsttijd zonder tijdzone")
        params.append(("arriveAt", aankomst.isoformat(timespec="seconds")))
    return ROUTE_URL.format(punten=punten_pad(punten)) + "?" + urlencode(params)


def geocode_url(
    sleutel: str,
    zoek: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    taal: str = "nl-NL",
) -> str:
    """Eén adres opzoeken, met een voorkeur voor wat dicht bij huis ligt.

    Geen `countrySet`: wie naar Antwerpen rijdt moet een Belgisch adres
    kunnen intypen. De voorkeur via lat/lon zorgt dat "Stationsplein 1"
    het station in de buurt wordt en niet dat in een andere stad.
    """
    params: list[tuple[str, str]] = [
        ("key", sleutel),
        ("limit", "1"),
        ("language", taal),
    ]
    if lat is not None and lon is not None:
        params += [("lat", f"{lat:.5f}"), ("lon", f"{lon:.5f}")]
    return GEOCODE_URL.format(zoek=quote(zoek.strip(), safe="")) + "?" + urlencode(params)


def zonder_sleutel(tekst: str, sleutel: str) -> str:
    """Een melding met de sleutel eruit. Een foutmelding van aiohttp kan het
    hele adres bevatten, en die belandt in het log en in de attributen."""
    tekst = str(tekst)
    if sleutel:
        tekst = tekst.replace(sleutel, "***")
        tekst = tekst.replace(quote(sleutel, safe=""), "***")
    return tekst


# ── antwoorden lezen ─────────────────────────────────────────────────


def _getal(waarde: Any) -> float | None:
    if isinstance(waarde, bool) or not isinstance(waarde, (int, float)):
        return None
    return float(waarde)


def _tijdstip(waarde: Any) -> datetime | None:
    """`2015-04-02T15:01:57+02:00`; zonder tijdzone tellen we hem niet."""
    if not isinstance(waarde, str) or not waarde:
        return None
    try:
        moment = datetime.fromisoformat(waarde)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


# Kort: de melding staat op de kaart, en de uitleg wat de dienst doet staat in
# het toevoegscherm. Tussen haakjes ging er een tweede (403) achter aan.
DIENSTNAAM = {
    "search": "de Search API",
    "routing": "de Routing API",
}


def dienst_van(url: str) -> str:
    """Welke van onze twee aanroepen een adres is; leeg als het geen van beide is."""
    if "/search/" in url:
        return "search"
    if "/routing/" in url:
        return "routing"
    return ""


def verwerk_antwoord(
    status: int, tekst: str, *, dienst: str = "", sleutel: str = ""
) -> dict[str, Any]:
    """Statuscode en tekst naar JSON, of de passende fout.

    `dienst` en `sleutel` maken van een 403 een melding die zegt welke
    dienst weigerde en wat TomTom er zelf over zegt. De sleutel gaat uit die
    tekst: een foutantwoord kan het adres van het verzoek herhalen.
    """
    detail = zonder_sleutel(_detailmelding(tekst), sleutel)
    if status == 403:
        voor = f" voor {DIENSTNAAM[dienst]}" if dienst in DIENSTNAAM else ""
        raise TomTomGeweigerd(
            f"TomTom weigert de sleutel{voor} (403): ongeldig, voor dit product "
            "niet aangezet, of het dagkwotum is op"
            + (f". {detail}" if detail else ""),
            dienst,
            detail,
        )
    if status == 429:
        raise TomTomTeVaak("TomTom krijgt te veel verzoeken voor deze sleutel (429)", "te_vaak")
    if status == 400:
        raise GeenRoute(detail or "TomTom kan hier geen route tussen leggen (400)", "geen_route", detail=detail)
    if status != 200:
        raise TomTomFout(f"TomTom antwoordde met {status}", "status", status=status)
    try:
        data = json.loads(tekst)
    except ValueError as err:
        raise TomTomFout("TomTom stuurde geen leesbare JSON", "onverwacht") from err
    if not isinstance(data, dict):
        raise TomTomFout("TomTom stuurde een onverwacht antwoord", "onverwacht")
    return data


def _detailmelding(tekst: str) -> str:
    """De `detailedError.message` uit een foutantwoord, als die er is."""
    try:
        data = json.loads(tekst)
    except (TypeError, ValueError):
        return ""
    fout = data.get("detailedError") if isinstance(data, dict) else None
    if isinstance(fout, dict) and isinstance(fout.get("message"), str):
        return f"TomTom: {fout['message']}"
    return ""


def bewaartijd_s(cache_control: str | None) -> int | None:
    """Hoe lang een antwoord bewaard mag worden volgens `Cache-Control`.

    None betekent dat de header er niets over zegt; 0 dat het niet mag.
    """
    if not cache_control:
        return None
    delen = [d.strip().lower() for d in cache_control.split(",")]
    if "no-store" in delen or "no-cache" in delen:
        return 0
    for deel in delen:
        if deel.startswith("max-age="):
            try:
                return max(0, int(deel.split("=", 1)[1]))
            except ValueError:
                return None
    return None


def lees_geocode(data: dict[str, Any]) -> dict[str, Any] | None:
    """Het eerste resultaat: coördinaat, het adres zoals TomTom het las, en
    hoe zeker TomTom ervan is. None als er niets gevonden is."""
    resultaten = data.get("results") if isinstance(data, dict) else None
    if not isinstance(resultaten, list) or not resultaten:
        return None
    eerste = resultaten[0] if isinstance(resultaten[0], dict) else {}
    positie = eerste.get("position") or {}
    lat, lon = _getal(positie.get("lat")), _getal(positie.get("lon"))
    if lat is None or lon is None:
        return None
    adres = (eerste.get("address") or {}).get("freeformAddress")
    zekerheid = _getal((eerste.get("matchConfidence") or {}).get("score"))
    return {
        "lat": lat,
        "lon": lon,
        "adres": adres if isinstance(adres, str) else "",
        "soort": eerste.get("type") if isinstance(eerste.get("type"), str) else "",
        "zekerheid": zekerheid,
    }


def _wegnummer(waarde: Any) -> str:
    """Een wegnummer; TomTom geeft ze als `{"text": "A10"}` in secties en als
    kale tekst in de routebeschrijving. Beide worden gelezen."""
    if isinstance(waarde, str):
        return waarde.strip()
    if isinstance(waarde, dict) and isinstance(waarde.get("text"), str):
        return waarde["text"].strip()
    return ""


def _wegstukken(secties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """De `IMPORTANT_ROAD_STRETCH`-secties: van, tot, belang en een naam.

    De naam is het eerste wegnummer (bij `A10, E10` de A10), en anders de
    straatnaam. Een stuk zonder allebei krijgt geen naam en valt af —
    liever niets dan een geraden weg.
    """
    uit = []
    for sectie in secties:
        if sectie.get("sectionType") != "IMPORTANT_ROAD_STRETCH":
            continue
        begin, eind = sectie.get("startPointIndex"), sectie.get("endPointIndex")
        belang = sectie.get("importantRoadStretchIndex")
        if not all(isinstance(x, int) for x in (begin, eind, belang)):
            continue
        nummers = [_wegnummer(n) for n in (sectie.get("roadNumbers") or [])]
        nummers = [n for n in nummers if n]
        naam = nummers[0] if nummers else _wegnummer(sectie.get("streetName"))
        if naam:
            uit.append({"begin": begin, "eind": eind, "belang": belang, "naam": naam})
    return uit


def _via(stukken: list[dict[str, Any]]) -> list[str]:
    """De belangrijkste wegen, in de volgorde waarin je ze rijdt.

    Een stuk kan in delen voorkomen (TomTom: "there may be gaps in one
    stretch"); het belang groepeert die, de eerste kilometer bepaalt de
    volgorde.
    """
    eerste_punt: dict[int, int] = {}
    naam_van: dict[int, str] = {}
    for stuk in stukken:
        b = stuk["belang"]
        if b not in eerste_punt or stuk["begin"] < eerste_punt[b]:
            eerste_punt[b] = stuk["begin"]
            naam_van[b] = stuk["naam"]
    gekozen = sorted(eerste_punt)[:MAX_WEGEN]
    namen: list[str] = []
    for b in sorted(gekozen, key=lambda x: eerste_punt[x]):
        if naam_van[b] not in namen:
            namen.append(naam_van[b])
    return namen


def _files(secties: list[dict[str, Any]], stukken: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verkeerssecties, met de weg waar ze op liggen als die bekend is.

    De weg komt uit een belangrijk wegstuk dat dezelfde punten beslaat. Ligt
    de file op een stuk dat TomTom niet belangrijk genoeg vond om te noemen,
    dan blijft `weg` leeg — het dichtstbijzijnde stuk nemen zou gokken zijn.
    """
    uit = []
    for sectie in secties:
        if sectie.get("sectionType") != "TRAFFIC":
            continue
        begin, eind = sectie.get("startPointIndex"), sectie.get("endPointIndex")
        weg = None
        if isinstance(begin, int) and isinstance(eind, int):
            raak = [s for s in stukken if s["begin"] < eind and begin < s["eind"]]
            if raak:
                weg = min(raak, key=lambda s: s["belang"])["naam"]
        vertraging = _getal(sectie.get("delayInSeconds"))
        snelheid = _getal(sectie.get("effectiveSpeedInKmh"))
        ernst = sectie.get("magnitudeOfDelay")
        uit.append({
            "soort": CATEGORIE.get(str(sectie.get("simpleCategory")), "hinder"),
            # de code zelf, zodat de kaart hem in de gekozen taal kan noemen
            "categorie": str(sectie.get("simpleCategory")) if sectie.get("simpleCategory") in CATEGORIE else "OTHER",
            "weg": weg,
            "vertraging_s": int(vertraging) if vertraging is not None else None,
            "snelheid_kmh": int(round(snelheid)) if snelheid is not None else None,
            "ernst": ernst if isinstance(ernst, int) else None,
        })
    uit.sort(key=lambda f: -(f["vertraging_s"] or 0))
    return uit


def lees_routes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle routes uit een calculateRoute-antwoord, de eerste is de snelste.

    Een route zonder reistijd telt niet: zonder dat getal is er niets te
    tonen, en een nul zou er als een lege weg uitzien.
    """
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list):
        return []
    uit = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        s = route.get("summary") or {}
        reistijd = _getal(s.get("travelTimeInSeconds"))
        if reistijd is None:
            continue
        secties = [x for x in (route.get("sections") or []) if isinstance(x, dict)]
        stukken = _wegstukken(secties)
        etappes = []
        for etappe in route.get("legs") or []:
            es = (etappe or {}).get("summary") or {}
            et = _getal(es.get("travelTimeInSeconds"))
            if et is None:
                continue
            em = _getal(es.get("lengthInMeters"))
            etappes.append({"reistijd_s": int(et), "afstand_m": int(em) if em is not None else None})

        def _heel(sleutel: str) -> int | None:
            waarde = _getal(s.get(sleutel))
            return int(waarde) if waarde is not None else None

        uit.append({
            "reistijd_s": int(reistijd),
            "afstand_m": _heel("lengthInMeters"),
            "vertraging_s": _heel("trafficDelayInSeconds"),
            "zonder_verkeer_s": _heel("noTrafficTravelTimeInSeconds"),
            "historisch_s": _heel("historicTrafficTravelTimeInSeconds"),
            "vertrek": _tijdstip(s.get("departureTime")),
            "aankomst": _tijdstip(s.get("arrivalTime")),
            "via": _via(stukken),
            "files": _files(secties, stukken),
            "etappes": etappes,
        })
    return uit


# ── het netwerk ──────────────────────────────────────────────────────


async def vraag(
    sessie: aiohttp.ClientSession,
    url: str,
    *,
    sleutel: str,
    agent: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Eén verzoek; geeft de JSON en de headers terug, of een TomTomFout.

    `encoded=True`: het adres is al gecodeerd door `route_url`, en yarl zou
    anders de `%2B` van de tijdzone nog een keer coderen.
    """
    from yarl import URL  # zit bij aiohttp; hier pas, zodat tests zonder kunnen

    try:
        async with sessie.get(
            URL(url, encoded=True),
            headers={"User-Agent": agent, "Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
        ) as antwoord:
            tekst = await antwoord.text()
            status = antwoord.status
            headers = {k: v for k, v in antwoord.headers.items()}
    except asyncio.TimeoutError as err:
        raise TomTomFout(
            f"TomTom antwoordde niet binnen {TIMEOUT_S} seconden", "time_out", seconden=TIMEOUT_S
        ) from err
    except aiohttp.ClientError as err:
        raise TomTomFout(
            zonder_sleutel(f"TomTom niet bereikbaar: {err}", sleutel),
            "onbereikbaar",
            detail=zonder_sleutel(str(err), sleutel),
        ) from err
    return verwerk_antwoord(status, tekst, dienst=dienst_van(url), sleutel=sleutel), headers
