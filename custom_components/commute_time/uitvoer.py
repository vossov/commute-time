"""Van rekenwerk naar attributen: wat de sensor publiceert en de kaart leest.

Eén pure functie per toestand, zonder Home Assistant. Dat is het hele
contract met de kaart, op één plek: tests/maak_sensor_fixture.py roept deze
functies aan om tests/fixtures/sensor.json te maken, en tests/kaart.test.mjs
controleert dat de kaart daar precies de velden uit leest die hier gezet
worden.

Tijden gaan twee keer mee: als ISO-tijdstip (om mee te rekenen, zoals het
aftellen) en als `HH:MM` in de tijdzone van Home Assistant (om te tonen).
Dat tweede is geen luxe: de browser kan in een andere tijdzone staan dan
Home Assistant, en dan zou de kaart een vertrektijd een uur verschoven
tonen.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .const import BRON
from .rooster import Dagplan, Oordeel, hhmm, seconden_tussen

DAGNAMEN = ("maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag")


def _min(seconden: int | None) -> int | None:
    """Seconden naar hele minuten, afgerond."""
    return None if seconden is None else int(round(seconden / 60))


def _km(meters: int | None) -> float | None:
    return None if meters is None else round(meters / 1000, 1)


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat(timespec="seconds")


def dag_tekst(moment: datetime, nu: datetime) -> str:
    """`vandaag 16:00`, `morgen 06:30` of `maandag 06:30`."""
    verschil = (moment.date() - nu.date()).days
    if verschil == 0:
        dag = "vandaag"
    elif verschil == 1:
        dag = "morgen"
    else:
        dag = DAGNAMEN[moment.weekday()]
    return f"{dag} {hhmm(moment)}"


def basis(route: str, nu: datetime) -> dict[str, Any]:
    """Wat er in elke toestand staat: welke route, welke bron, en wanneer."""
    return {
        "route": route,
        "bron": BRON,
        "bijgewerkt": _iso(nu),
        "bijgewerkt_hhmm": hhmm(nu),
    }


def buiten_venster(route: str, nu: datetime, volgende: datetime | None) -> dict[str, Any]:
    """Buiten het venster: geen reistijd, alleen wanneer hij weer komt.

    Een reistijd van het vorige venster laten staan zou een getal tonen dat
    uren oud is, zonder dat te zien is dat het oud is.
    """
    return {
        **basis(route, nu),
        "in_venster": False,
        "status": "buiten_venster",
        "volgend_venster": _iso(volgende),
        "volgend_venster_tekst": dag_tekst(volgende, nu) if volgende else None,
        # dezelfde informatie zonder taal, voor de kaart: hoe laat, hoeveel
        # dagen vooruit (0 is vandaag) en welke weekdag (0 is maandag)
        "volgend_venster_hhmm": hhmm(volgende) if volgende else None,
        "volgend_venster_dagen": (volgende.date() - nu.date()).days if volgende else None,
        "volgend_venster_weekdag": volgende.weekday() if volgende else None,
    }


def fout(
    route: str,
    nu: datetime,
    plan: Dagplan | None,
    melding: str,
    code: str = "",
    param: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Binnen het venster, maar TomTom gaf geen bruikbaar antwoord.

    Geen getallen van de vorige ronde: de melding is het antwoord. Op een
    telefoon is er geen logboek, dus de kaart toont hem. `fout` is de
    Nederlandse tekst uit het logboek; `fout_code` en `fout_param` laten de
    kaart dezelfde melding in de gekozen taal zeggen (zie tomtom.FOUTCODES).
    """
    return {
        **basis(route, nu),
        "in_venster": True,
        "status": "fout",
        "venster_van": hhmm(plan.van) if plan else None,
        "venster_tot": hhmm(plan.tot) if plan else None,
        "fout": melding,
        "fout_code": code or None,
        "fout_param": dict(param or {}),
    }


def _alternatief(route: dict[str, Any], snelste_s: int) -> dict[str, Any]:
    return {
        "reistijd_min": _min(route["reistijd_s"]),
        "verschil_min": _min(route["reistijd_s"] - snelste_s),
        "afstand_km": _km(route.get("afstand_m")),
        "vertraging_min": _min(route.get("vertraging_s")),
        "via": list(route.get("via") or []),
    }


def _file(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "soort": f.get("soort"),
        "categorie": f.get("categorie"),
        "weg": f.get("weg"),
        "vertraging_min": _min(f.get("vertraging_s")),
        "snelheid_kmh": f.get("snelheid_kmh"),
        "ernst": f.get("ernst"),
    }


def berekend(
    *,
    route: str,
    nu: datetime,
    plan: Dagplan,
    oordeel: Oordeel,
    routes: list[dict[str, Any]],
    route_bij_vertrek: dict[str, Any] | None,
    punten: list[dict[str, Any]],
    waze: list[str | None],
    marge_min: int,
    stoptijd_min: int,
) -> dict[str, Any]:
    """Binnen het venster, met een antwoord van TomTom.

    `routes[0]` is de snelste route bij vertrek nu, de rest zijn de
    alternatieven. `route_bij_vertrek` komt uit de berekening met een
    aankomsttijd, als die er was. `punten` zijn de adressen zoals ze
    gevonden zijn (start, tussenstops, bestemming), `waze` de link per punt
    na de start.
    """
    snelste = routes[0]
    stops = max(0, len(punten) - 2)
    etappes = []
    if stops:
        for i, etappe in enumerate(snelste.get("etappes") or []):
            if i + 1 >= len(punten):
                break
            etappes.append({
                "van": punten[i]["naam"],
                "naar": punten[i + 1]["naam"],
                "reistijd_min": _min(etappe.get("reistijd_s")),
                "afstand_km": _km(etappe.get("afstand_m")),
                "waze_url": waze[i] if i < len(waze) else None,
            })
    return {
        **basis(route, nu),
        "in_venster": True,
        "status": oordeel.status,
        "venster_van": hhmm(plan.van),
        "venster_tot": hhmm(plan.tot),
        "doel": _iso(plan.aankomst),
        "doel_hhmm": hhmm(plan.aankomst),
        "marge_min": marge_min,
        "stops": stops,
        "stoptijd_min": stoptijd_min,
        "vertrek": _iso(oordeel.vertrek),
        "vertrek_hhmm": hhmm(oordeel.vertrek),
        "aankomst": _iso(oordeel.aankomst),
        "aankomst_hhmm": hhmm(oordeel.aankomst),
        "te_laat_min": oordeel.te_laat_min,
        "reistijd_min": _min(snelste["reistijd_s"]),
        "reistijd_bij_vertrek_min": _min(route_bij_vertrek["reistijd_s"]) if route_bij_vertrek else None,
        "normaal_min": _min(snelste.get("historisch_s")),
        "vrij_min": _min(snelste.get("zonder_verkeer_s")),
        "vertraging_min": _min(snelste.get("vertraging_s")),
        "afstand_km": _km(snelste.get("afstand_m")),
        "via": list(snelste.get("via") or []),
        "files": [_file(f) for f in snelste.get("files") or []],
        "alternatieven": [_alternatief(r, snelste["reistijd_s"]) for r in routes[1:]],
        "etappes": etappes,
        "punten": [
            {"invoer": p["invoer"], "gevonden": p["gevonden"], "soort": p["soort"]}
            for p in punten
        ],
        "waze_url": waze[0] if waze else None,
        "fout": None,
        "fout_code": None,
        "fout_param": {},
    }


def volgende_ronde(nu: datetime, volgende: datetime | None, maximum: timedelta) -> timedelta:
    """Hoe lang de coordinator buiten het venster slaapt.

    Tot het venster begint, maar nooit langer dan `maximum` en nooit korter
    dan een minuut — anders draait hij vlak voor het begin rondjes.

    Vijf seconden speling: Home Assistant plant de volgende ronde op hele
    seconden afgekapt, en een ronde die een tel vóór het begin wakker wordt
    ziet nog geen venster en slaapt dan een volle minuut.
    """
    if volgende is None:
        return maximum
    tot_begin = timedelta(seconds=seconden_tussen(volgende, nu) + 5)
    return max(timedelta(minutes=1), min(maximum, tot_begin))
