"""De koppeling naar Waze om te gaan rijden.

Dit is de officiële weg: Waze Deep Links, gedocumenteerd op
https://developers.google.com/waze/deeplinks — een adres dat de app opent
(of de website, als de app er niet is) en de navigatie start. Er wordt
niets bij Waze opgevraagd; de kaart zet alleen een link neer waar jij op
tikt.

Waze vertrekt altijd vanaf waar de telefoon is en kent maar één
bestemming. Bij een route met tussenstops wijst de link daarom naar de
eerstvolgende stop; in het detailvenster staat er per etappe een.
"""
from __future__ import annotations

from urllib.parse import urlencode

WAZE_UL = "https://waze.com/ul"
# Waze vraagt om een utm_source "for better partner support"
UTM_BRON = "home-assistant-time-to-leave"


def waze_link(
    lat: float,
    lon: float,
    *,
    vermijd: list[str] | tuple[str, ...] = (),
    vervoer: str = "car",
) -> str:
    """Navigeren naar één punt, met dezelfde voorkeuren als de route.

    De namen verschillen per dienst: wat hier `toll_roads` heet (bij TomTom
    `tollRoads`) is bij Waze `avoid_tolls`. Wat Waze niet kent (onverharde
    wegen staan daar standaard al uit) gaat niet mee.
    """
    params = [("ll", f"{lat:.6f},{lon:.6f}"), ("navigate", "yes")]
    if "toll_roads" in vermijd:
        params.append(("avoid_tolls", "true"))
    if "ferries" in vermijd:
        params.append(("avoid_ferries", "true"))
    if "motorways" in vermijd:
        params.append(("avoid_freeways", "true"))
    if vervoer == "motorcycle":
        params.append(("vehicle_type", "motorcycle"))
    params.append(("utm_source", UTM_BRON))
    return f"{WAZE_UL}?{urlencode(params)}"
