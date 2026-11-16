"""Maakt tests/fixtures/sensor.json: precies wat de sensor publiceert.

De kaart leest die attributen en niets anders; tests/kaart.test.mjs draait
de kaart tegen dit bestand, en tests/test_kaart.py controleert dat het nog
klopt met wat uitvoer.py maakt. Verandert de vorm van de attributen, draai
dit dan bewust opnieuw — nooit alleen om een test groen te krijgen:

    python3 tests/maak_sensor_fixture.py

De route komt uit TomTom's eigen documentatievoorbeeld (zie
fixtures/README.md). De rest — welk rooster, welke adressen, hoe laat het
is — is de invoer die een gebruiker zou geven, geen gegeven van een bron.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HIER = Path(__file__).parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "custom_components"))

import conftest  # noqa: E402  — stubt Home Assistant

conftest._installeer_stubs()

from time_to_leave import rooster, tomtom, uitvoer  # noqa: E402
from time_to_leave.waze import waze_link  # noqa: E402

TZ = ZoneInfo("Europe/Amsterdam")
NU = datetime(2026, 11, 17, 7, 34, tzinfo=TZ)
ROOSTER = {
    dag: {"show_from": "06:30:00", "show_until": "09:30:00", "arrive_at": "08:30:00"}
    for dag in ("tuesday", "wednesday")
}
PUNTEN = [
    {"invoer": "zone.home", "gevonden": "Thuis", "soort": "entiteit", "naam": "Thuis",
     "lat": 52.09, "lon": 5.12},
    {"invoer": "Stationsplein 1, Utrecht", "gevonden": "Stationsplein 1, 3511 ED Utrecht",
     "soort": "adres", "naam": "Stationsplein 1, Utrecht", "lat": 52.0894, "lon": 5.1102},
]


def staten() -> dict:
    data = json.loads((HIER / "fixtures" / "tomtom_route_documentatie.json").read_text(encoding="utf-8"))
    routes = tomtom.lees_routes(data)
    plan = rooster.plan_nu(ROOSTER, NU)
    # de berekening met een aankomsttijd: hetzelfde voorbeeld, met de
    # vertrektijd uit het voorbeeld omgezet naar een vertrek om 07:52 hier
    bij_vertrek = dict(routes[0], vertrek=datetime(2026, 11, 17, 7, 52, 40, tzinfo=TZ))
    oordeel = rooster.beoordeel(
        nu=NU, doel=plan.aankomst, reistijd_nu_s=routes[0]["reistijd_s"],
        stoptijd_s=0, vertrek_tomtom=bij_vertrek["vertrek"],
    )
    waze = [waze_link(p["lat"], p["lon"]) for p in PUNTEN[1:]]
    return {
        "berekend": uitvoer.berekend(
            route="Naar werk", nu=NU, plan=plan, oordeel=oordeel, routes=routes,
            route_bij_vertrek=bij_vertrek, punten=PUNTEN, waze=waze,
            marge_min=5, stoptijd_min=0,
        ),
        "buiten_venster": uitvoer.buiten_venster(
            "Naar werk", datetime(2026, 11, 17, 18, 0, tzinfo=TZ),
            rooster.volgende_begin(ROOSTER, datetime(2026, 11, 17, 18, 0, tzinfo=TZ)),
        ),
        "fout": uitvoer.fout(
            "Naar werk", NU, plan,
            "TomTom weigert de sleutel (403): ongeldig, niet geactiveerd voor deze dienst, of het dagkwotum is op",
        ),
    }


def tekst() -> str:
    return json.dumps(staten(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    doel = HIER / "fixtures" / "sensor.json"
    doel.write_text(tekst(), encoding="utf-8")
    print(f"geschreven: {doel}")
