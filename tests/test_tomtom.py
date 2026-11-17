"""De TomTom-client: adressen in het verzoek, en het antwoord lezen.

Het antwoord is het voorbeeld uit TomTom's documentatie (zie
fixtures/README.md voor wat daaraan veranderd is). Geen verzonnen JSON: bij
cycling-next-race heeft verzonnen HTML twee keer een echte fout gemaskeerd.
"""
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _laad(naam):
    return json.loads((FIXTURES / naam).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def routes(tomtom):
    return tomtom.lees_routes(_laad("tomtom_route_documentatie.json"))


# ── het verzoek ─────────────────────────────────────────────────────

def test_de_aankomsttijd_gaat_met_een_gecodeerde_plus_de_deur_uit(tomtom, tz):
    """Een `+` die niet als %2B gaat, leest de server als spatie.

    Dan zou "+01:00" een tijd zonder geldige zone worden, of erger: een
    aankomsttijd die een uur verschoven wordt gelezen. Geen foutmelding.
    """
    aankomst = datetime(2026, 11, 17, 8, 25, tzinfo=tz)
    url = tomtom.route_url("SLEUTEL", [(52.09, 5.12), (52.37, 4.9)], aankomst=aankomst)
    assert "arriveAt=2026-11-17T08%3A25%3A00%2B01%3A00" in url
    assert "+" not in url
    params = parse_qsl(urlsplit(url).query)
    assert ("arriveAt", "2026-11-17T08:25:00+01:00") in params


def test_een_aankomsttijd_zonder_zone_wordt_geweigerd(tomtom):
    with pytest.raises(ValueError):
        tomtom.route_url("S", [(1, 2), (3, 4)], aankomst=datetime(2026, 11, 17, 8, 25))


def test_het_verzoek_vraagt_wat_de_parser_leest(tomtom):
    """Zonder deze sectietypes staan er geen wegen en geen files in het antwoord."""
    url = tomtom.route_url(
        "S", [(1, 2), (3, 4)], alternatieven=2, vermijd=["toll_roads", "ferries", "onbekend"]
    )
    params = parse_qsl(urlsplit(url).query)
    assert ("sectionType", "traffic") in params
    assert ("sectionType", "importantRoadStretch") in params
    assert ("computeTravelTimeFor", "all") in params
    assert ("traffic", "true") in params
    assert ("maxAlternatives", "2") in params
    # onze sleutels vertaald naar die van TomTom; wat TomTom niet kent valt af
    assert [w for k, w in params if k == "avoid"] == ["tollRoads", "ferries"]
    assert ("routeRepresentation", "summaryOnly") in params


def test_zonder_alternatieven_staat_de_parameter_er_niet(tomtom):
    params = dict(parse_qsl(urlsplit(tomtom.route_url("S", [(1, 2), (3, 4)])).query))
    assert "maxAlternatives" not in params


def test_tussenstops_staan_in_volgorde_in_het_pad(tomtom):
    url = tomtom.route_url("S", [(52.1, 5.1), (52.2, 5.2), (52.3, 5.3)])
    assert "/calculateRoute/52.100000,5.100000:52.200000,5.200000:52.300000,5.300000/json?" in url


def test_een_route_heeft_minstens_twee_punten(tomtom):
    with pytest.raises(ValueError):
        tomtom.route_url("S", [(1, 2)])


def test_een_adres_wordt_in_het_pad_gecodeerd(tomtom):
    url = tomtom.geocode_url("S", "Stationsplein 1/3, Utrecht", lat=52.09, lon=5.12)
    assert "/geocode/Stationsplein%201%2F3%2C%20Utrecht.json?" in url
    params = dict(parse_qsl(urlsplit(url).query))
    assert params["limit"] == "1"
    assert params["lat"] == "52.09000"


def test_de_sleutel_verdwijnt_uit_een_melding(tomtom):
    melding = "kan https://api.tomtom.com/x?key=ab+c/d niet openen (ab%2Bc%2Fd)"
    assert "ab+c/d" not in tomtom.zonder_sleutel(melding, "ab+c/d")
    assert "ab%2Bc%2Fd" not in tomtom.zonder_sleutel(melding, "ab+c/d")


# ── het antwoord ────────────────────────────────────────────────────

def test_de_samenvatting_van_de_route(routes):
    assert len(routes) == 1
    r = routes[0]
    assert r["reistijd_s"] == 161
    assert r["afstand_m"] == 1147
    assert r["vertraging_s"] == 15
    assert r["zonder_verkeer_s"] == 120
    assert r["historisch_s"] == 157
    assert r["vertrek"].isoformat() == "2015-04-02T15:01:57+02:00"
    assert r["aankomst"].isoformat() == "2015-04-02T15:04:38+02:00"


def test_de_wegen_komen_in_rijvolgorde_met_het_wegnummer_voorop(routes):
    """Uit de IMPORTANT_ROAD_STRETCH-secties.

    Belang 0 is Sample Street (punt 0), belang 2 de A10/E10 (punt 6) en
    belang 1 de A10 (punt 8). Rijvolgorde: Sample Street, dan de A10 — één
    keer, ook al komt hij in twee stukken voor. Bij "A10, E10" wint de
    eerste.
    """
    assert routes[0]["via"] == ["Sample Street", "A10"]


def test_een_file_krijgt_de_weg_waar_hij_op_ligt_als_die_bekend_is(routes):
    """De TRAFFIC-sectie beslaat punt 3–4. Daar overlapt alleen het stuk
    van punt 0–3 niet (dat eindigt op 3), dus geen bekende weg: leeg laten,
    niet de dichtstbijzijnde nemen."""
    files = routes[0]["files"]
    assert len(files) == 1
    f = files[0]
    assert f["soort"] == "file"
    assert f["vertraging_s"] == 158
    assert f["snelheid_kmh"] == 40
    assert f["ernst"] == 1
    assert f["weg"] is None


def test_een_file_op_een_benoemd_wegstuk(tomtom):
    data = {"routes": [{
        "summary": {"travelTimeInSeconds": 600},
        "sections": [
            {"startPointIndex": 0, "endPointIndex": 10, "sectionType": "IMPORTANT_ROAD_STRETCH",
             "importantRoadStretchIndex": 0, "roadNumbers": [{"text": "A12"}]},
            {"startPointIndex": 2, "endPointIndex": 4, "sectionType": "TRAFFIC",
             "simpleCategory": "ROAD_WORK", "delayInSeconds": 300},
        ],
    }]}
    f = tomtom.lees_routes(data)[0]["files"][0]
    assert f["weg"] == "A12"
    assert f["soort"] == "werk in uitvoering"


def test_hoogstens_drie_wegen_de_belangrijkste(tomtom):
    secties = [
        {"startPointIndex": i * 10, "endPointIndex": i * 10 + 5, "sectionType": "IMPORTANT_ROAD_STRETCH",
         "importantRoadStretchIndex": belang, "roadNumbers": [naam]}
        for i, (belang, naam) in enumerate([(3, "N201"), (0, "A2"), (4, "N401"), (1, "A12"), (2, "A27")])
    ]
    via = tomtom.lees_routes({"routes": [{"summary": {"travelTimeInSeconds": 1}, "sections": secties}]})[0]["via"]
    # belang 0, 1 en 2, in de volgorde waarin je ze tegenkomt
    assert via == ["A2", "A12", "A27"]


def test_etappes_per_tussenstop(routes):
    assert routes[0]["etappes"] == [{"reistijd_s": 11, "afstand_m": 108}]


def test_een_route_zonder_reistijd_telt_niet(tomtom):
    assert tomtom.lees_routes({"routes": [{"summary": {}}]}) == []
    assert tomtom.lees_routes({}) == []
    assert tomtom.lees_routes({"routes": "geen lijst"}) == []


def test_een_tijdstip_zonder_zone_telt_niet(tomtom):
    r = tomtom.lees_routes({"routes": [{"summary": {
        "travelTimeInSeconds": 60, "departureTime": "2026-11-17T07:00:00"}}]})[0]
    assert r["vertrek"] is None


# ── geocode ─────────────────────────────────────────────────────────

def test_het_voorbeeldadres_uit_de_documentatie(tomtom):
    g = tomtom.lees_geocode(_laad("tomtom_geocode_documentatie.json"))
    assert g["lat"] == pytest.approx(36.98844)
    assert g["lon"] == pytest.approx(-121.97482)
    assert g["adres"] == "2501 Soquel Dr, Santa Cruz, CA 95065"
    assert g["zekerheid"] == 1


def test_niets_gevonden_is_none(tomtom):
    assert tomtom.lees_geocode({"results": []}) is None
    assert tomtom.lees_geocode({"results": [{"position": {"lat": "x"}}]}) is None


# ── fouten ──────────────────────────────────────────────────────────

def test_statuscodes_worden_de_juiste_fout(tomtom):
    with pytest.raises(tomtom.TomTomGeweigerd):
        tomtom.verwerk_antwoord(403, "")
    with pytest.raises(tomtom.TomTomTeVaak):
        tomtom.verwerk_antwoord(429, "")
    with pytest.raises(tomtom.TomTomFout):
        tomtom.verwerk_antwoord(500, "")
    with pytest.raises(tomtom.TomTomFout):
        tomtom.verwerk_antwoord(200, "geen json")


def test_een_403_zegt_welke_dienst_weigerde(tomtom):
    with pytest.raises(tomtom.TomTomGeweigerd) as fout:
        tomtom.verwerk_antwoord(403, "", dienst="search")
    assert fout.value.dienst == "search"
    assert "Search API" in str(fout.value) and "403" in str(fout.value)

    with pytest.raises(tomtom.TomTomGeweigerd) as fout:
        tomtom.verwerk_antwoord(403, "", dienst="routing")
    assert "Routing API" in str(fout.value)

    # niet te zien welke dienst: de melding blijft kloppen, zonder te raden
    with pytest.raises(tomtom.TomTomGeweigerd) as fout:
        tomtom.verwerk_antwoord(403, "")
    assert fout.value.dienst == ""
    assert "API" not in str(fout.value)


def test_een_403_herhaalt_wat_tomtom_zelf_zegt_zonder_de_sleutel(tomtom):
    """De tekst van TomTom is het enige dat zegt waaróm; een foutantwoord kan
    het adres van het verzoek herhalen, en daar staat de sleutel in."""
    tekst = json.dumps({"detailedError": {"code": "Forbidden", "message": "key GEHEIM is not allowed here"}})
    with pytest.raises(tomtom.TomTomGeweigerd) as fout:
        tomtom.verwerk_antwoord(403, tekst, dienst="routing", sleutel="GEHEIM")
    assert "is not allowed here" in str(fout.value)
    assert "GEHEIM" not in str(fout.value)


def test_de_dienst_komt_uit_het_adres(tomtom):
    assert tomtom.dienst_van("https://api.tomtom.com/routing/1/calculateRoute/1,2:3,4/json?key=x") == "routing"
    assert tomtom.dienst_van("https://api.tomtom.com/search/2/geocode/Utrecht.json?key=x") == "search"
    assert tomtom.dienst_van("https://example.org/") == ""


def test_een_400_noemt_de_melding_van_tomtom(tomtom):
    tekst = (FIXTURES / "tomtom_fout_documentatie.json").read_text(encoding="utf-8")
    with pytest.raises(tomtom.GeenRoute) as fout:
        tomtom.verwerk_antwoord(400, tekst)
    assert "Error message" in str(fout.value)


def test_geweigerd_en_te_vaak_zijn_ook_gewone_fouten(tomtom):
    """De coordinator vangt TomTomFout; deze twee mogen daar niet langs glippen."""
    assert issubclass(tomtom.TomTomGeweigerd, tomtom.TomTomFout)
    assert issubclass(tomtom.TomTomTeVaak, tomtom.TomTomFout)
    assert issubclass(tomtom.GeenRoute, tomtom.TomTomFout)


@pytest.mark.parametrize("kop, verwacht", [
    (None, None),
    ("", None),
    ("public, max-age=3600", 3600),
    ("no-store", 0),
    ("private, no-cache", 0),
    ("max-age=abc", None),
])
def test_bewaartijd_uit_cache_control(tomtom, kop, verwacht):
    assert tomtom.bewaartijd_s(kop) == verwacht
