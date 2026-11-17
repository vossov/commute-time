"""Gedeelde constanten voor Time to Leave.

Staat apart zodat `config_flow.py`, `__init__.py`, `coordinator.py` en
`sensor.py` dezelfde sleutels en standaardwaarden gebruiken zonder elkaar
te importeren.
"""
from __future__ import annotations

DOMAIN = "time_to_leave"
NAME = "Time to Leave"

# Gelijk aan "version" in manifest.json en aan VERSIE bovenin de kaart.
# Hangt achter de kaart-URL, zodat de browser na een update de nieuwe kaart
# ophaalt. tests/test_repo.py bewaakt dat de drie niet uiteenlopen.
VERSION = "0.1.3"

# De meegeleverde Lovelace-kaart, door de integratie zelf geregistreerd.
KAART_BESTAND = "time-to-leave-card.js"
KAART_URL = f"/{DOMAIN}/{KAART_BESTAND}"

BRON = "TomTom"

# Alleen bij het toevoegen: de naam van de route wordt de titel van de entry,
# de naam van het apparaat en daarmee het begin van de entiteits-ID's.
CONF_NAME = "name"
DEFAULT_NAME = "Naar werk"

# ── optiesleutels (ConfigEntry.options) ──────────────────────────────
# Alles staat in de opties, ook de route zelf: dan kan elk onderdeel later
# via "Configureren" worden aangepast zonder de route te verwijderen.
CONF_API_KEY = "api_key"
CONF_START = "start"
CONF_VIA = "via"
CONF_DESTINATION = "destination"
CONF_MARGIN_MINUTES = "margin_minutes"
CONF_STOP_MINUTES = "stop_minutes"
CONF_TRAVEL_MODE = "travel_mode"
CONF_AVOID = "avoid"
CONF_ALTERNATIVES = "alternatives"
CONF_SCAN_MINUTES = "scan_minutes"

# Het rooster: per weekdag een sectie met drie tijden. De sleutels van de
# dagen volgen `datetime.weekday()` (maandag = 0).
DAGEN = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
CONF_SHOW_FROM = "show_from"
CONF_SHOW_UNTIL = "show_until"
CONF_ARRIVE_AT = "arrive_at"
DAGVELDEN = (CONF_SHOW_FROM, CONF_SHOW_UNTIL, CONF_ARRIVE_AT)

# ── standaardwaarden ─────────────────────────────────────────────────
# "zone.home" is de locatie die in Home Assistant zelf staat ingesteld;
# een adres intypen hoeft dan niet.
DEFAULT_START = "zone.home"
DEFAULT_VIA = ""
DEFAULT_DESTINATION = ""
# De marge is wat je eerder wilt aankomen dan de aankomsttijd: parkeren,
# lopen naar binnen. Hij staat altijd op de kaart, zodat een vertrektijd
# nooit een verborgen buffer bevat.
DEFAULT_MARGIN_MINUTES = 5
# Per tussenstop. Standaard nul: hoe lang je bij school staat weet alleen
# jij, en een gegokte stoptijd zou de vertrektijd stil verschuiven.
DEFAULT_STOP_MINUTES = 0
DEFAULT_TRAVEL_MODE = "car"
DEFAULT_AVOID: list[str] = []
DEFAULT_ALTERNATIVES = 2
DEFAULT_SCAN_MINUTES = 5

# Werkdagen in de ochtend, zonder aankomsttijd. Een beginpunt, geen gok over
# jouw week: aanpassen gaat per dag in het optiescherm.
DEFAULT_SCHEDULE: dict[str, dict[str, str | None]] = {
    dag: (
        {CONF_SHOW_FROM: "06:30:00", CONF_SHOW_UNTIL: "09:30:00", CONF_ARRIVE_AT: None}
        if i < 5
        else {CONF_SHOW_FROM: None, CONF_SHOW_UNTIL: None, CONF_ARRIVE_AT: None}
    )
    for i, dag in enumerate(DAGEN)
}

# Wat TomTom kent als `travelMode` en `avoid`, beperkt tot wat voor een rit
# met verkeer zin heeft. Fiets en lopen hebben geen files.
VERVOER = ("car", "motorcycle")
# Kleine letters: hassfest eist dat de opties van een keuzelijst een
# vertaalsleutel kunnen zijn (`[a-z0-9-_]`). De namen van TomTom staan in
# tomtom.VERMIJD_TOMTOM en worden pas bij het verzoek gebruikt.
VERMIJD = ("toll_roads", "motorways", "ferries", "unpaved_roads")

# ── grenzen voor het optiescherm ─────────────────────────────────────
MIN_MARGIN_MINUTES = 0
MAX_MARGIN_MINUTES = 120
MIN_STOP_MINUTES = 0
MAX_STOP_MINUTES = 120
MIN_ALTERNATIVES = 0
# TomTom staat er vijf toe; meer dan drie past niet meer leesbaar in het
# venster en kost alleen rekentijd bij TomTom.
MAX_ALTERNATIVES = 3
# Twee minuten is de ondergrens: vaker verandert een reistijd niet zinvol, en
# TomTom geeft gratis 2.500 verzoeken per dag, niet per uur.
MIN_SCAN_MINUTES = 2
MAX_SCAN_MINUTES = 60
# Hoogstens drie tussenstops. Elke stop is een verzoek bij het opzoeken van
# het adres, en de kaart toont ze als etappes.
MAX_VIA = 3

OPTION_DEFAULTS: dict[str, object] = {
    CONF_API_KEY: "",
    CONF_START: DEFAULT_START,
    CONF_VIA: DEFAULT_VIA,
    CONF_DESTINATION: DEFAULT_DESTINATION,
    CONF_MARGIN_MINUTES: DEFAULT_MARGIN_MINUTES,
    CONF_STOP_MINUTES: DEFAULT_STOP_MINUTES,
    CONF_TRAVEL_MODE: DEFAULT_TRAVEL_MODE,
    CONF_AVOID: DEFAULT_AVOID,
    CONF_ALTERNATIVES: DEFAULT_ALTERNATIVES,
    CONF_SCAN_MINUTES: DEFAULT_SCAN_MINUTES,
}

# ── terugschakelen ───────────────────────────────────────────────────
# Weigert TomTom (403: sleutel ongeldig of dagkwotum op; 429: te veel
# tegelijk), dan maakt harder vragen het erger. Zoals Skywatch: het interval
# wordt telkens verdrievoudigd tot dit maximum, en zakt terug zodra TomTom
# weer antwoordt.
TERUGSCHAKEL_FACTOR = 3
MAX_TERUGSCHAKEL_MINUTEN = 60

# Buiten het venster slaapt de coordinator tot het volgende venster begint,
# maar nooit langer dan dit: een klok die verzet wordt, of een zomertijd-
# wissel, mag hem niet een dag laten missen.
MAX_SLAAP_MINUTEN = 60
