"""Het toevoegen van een route en de twee sensoren.

`controleer_route` is het eerste wat een gebruiker raakt: elke fout van
TomTom moet daar een melding in het scherm worden, nooit een uitzondering.
De stappen van het scherm zelf (async_show_form en verder) zijn hier niet
te draaien; die hebben een echte Home Assistant nodig.
"""
import asyncio
import json
import sys
import types
from datetime import datetime

import pytest
from test_coordinator import ROUTE, NepSessie, _geocodes, _routes


@pytest.fixture
def controleer(flow_mod, monkeypatch):
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers.location"], "find_coordinates",
        lambda hass, naam: "52.0907,5.1214" if naam == "zone.home" else None,
    )
    hass = types.SimpleNamespace(
        config=types.SimpleNamespace(latitude=52.09, longitude=5.12),
        states=types.SimpleNamespace(get=lambda e: types.SimpleNamespace(name="Thuis")),
    )

    def _controleer(sessie, **invoer):
        monkeypatch.setattr(flow_mod, "async_get_clientsession", lambda h: sessie)
        basis = {"api_key": "S", "start": "zone.home", "destination": "Stationsplein 1, Utrecht"}
        return asyncio.run(flow_mod.controleer_route(hass, {**basis, **invoer}))

    return _controleer


def test_een_goede_route(controleer, flow_mod):
    sessie = NepSessie()
    fouten, punten, reistijd = controleer(sessie)
    assert fouten == {}
    assert [p.soort for p in punten] == ["entiteit", "adres"]
    assert reistijd == 3
    assert len(_geocodes(sessie)) == 1 and len(_routes(sessie)) == 1
    lijst = flow_mod._puntenlijst(punten)
    assert "**Start**: Thuis" in lijst
    assert "**Bestemming**: Stationsplein 1, Utrecht → 2501 Soquel Dr" in lijst


def test_zonder_sleutel_geen_verzoek(controleer):
    sessie = NepSessie()
    fouten, _, _ = controleer(sessie, api_key="  ")
    assert fouten == {"api_key": "sleutel_leeg"}
    assert sessie.adressen == []


def test_meer_dan_drie_stops(controleer):
    sessie = NepSessie()
    fouten, _, _ = controleer(sessie, via="a\nb\nc\nd")
    assert fouten == {"via": "te_veel_stops"}
    assert sessie.adressen == []


def test_een_geweigerde_sleutel_noemt_de_dienst_die_weigerde(controleer):
    """Zonder dat bleef er raden over welke producten in het portaal aan
    moesten: dezelfde melding voor het opzoeken en voor de route."""
    # het adres wordt eerst opgezocht, dus dat is wat er weigert
    fouten, _, _ = controleer(NepSessie(geocode=(403, ""), route=(403, "")))
    assert fouten == {"base": "sleutel_geweigerd_search"}

    # adres lukt, route niet
    fouten, _, _ = controleer(NepSessie(route=(403, "")))
    assert fouten == {"base": "sleutel_geweigerd_routing"}

    # zonder adres wordt de Search API niet eens aangeroepen
    sessie = NepSessie(route=(403, ""))
    fouten, _, _ = controleer(sessie, destination="52.3676, 4.9041")
    assert fouten == {"base": "sleutel_geweigerd_routing"}
    assert _geocodes(sessie) == []


def test_een_onbekend_adres_staat_bij_het_goede_veld(controleer):
    fouten, _, _ = controleer(NepSessie(geocode=(200, json.dumps({"results": []}))))
    assert fouten == {"destination": "adres_niet_gevonden"}


def test_een_persoon_zonder_locatie(controleer):
    fouten, _, _ = controleer(NepSessie(), start="person.niemand")
    assert fouten == {"start": "geen_locatie"}


def test_geen_route_tussen_de_punten(controleer):
    fouten, punten, _ = controleer(NepSessie(route=(400, "{}")))
    assert fouten == {"base": "geen_route"}


def test_tomtom_ligt_eruit(controleer):
    fouten, _, _ = controleer(NepSessie(route=(503, "")))
    assert fouten == {"base": "tomtom_fout"}


def test_coordinaten_hoeven_niet_opgezocht(controleer):
    sessie = NepSessie()
    fouten, punten, _ = controleer(sessie, destination="52.3676, 4.9041")
    assert fouten == {}
    assert _geocodes(sessie) == []
    assert punten[1].soort == "coordinaat"


# ── de sensoren ─────────────────────────────────────────────────────

def _sensor(sensor_mod, klasse, data):
    coordinator = types.SimpleNamespace(
        data=data, entry=types.SimpleNamespace(entry_id="abc", title="Naar werk"),
    )
    s = klasse(coordinator)
    s.coordinator = coordinator  # de echte CoordinatorEntity zet dit zelf
    return s


def test_de_reistijd_en_de_vertrektijd(sensor_mod, tz):
    staten = json.loads((__import__("pathlib").Path(__file__).parent / "fixtures" / "sensor.json").read_text())
    reistijd = _sensor(sensor_mod, sensor_mod.ReistijdSensor, staten["berekend"])
    assert reistijd.native_value == 3
    assert reistijd.extra_state_attributes["route"] == "Naar werk"
    assert reistijd._attr_unique_id == "abc_reistijd"

    vertrek = _sensor(sensor_mod, sensor_mod.VertrektijdSensor, staten["berekend"])
    assert vertrek.native_value == datetime(2026, 11, 17, 7, 52, tzinfo=tz)


def test_buiten_het_venster_onbekend_en_geen_vertrektijd(sensor_mod):
    staten = json.loads((__import__("pathlib").Path(__file__).parent / "fixtures" / "sensor.json").read_text())
    for toestand in ("buiten_venster", "fout"):
        assert _sensor(sensor_mod, sensor_mod.ReistijdSensor, staten[toestand]).native_value is None
        assert _sensor(sensor_mod, sensor_mod.VertrektijdSensor, staten[toestand]).native_value is None


def test_de_attributen_gaan_niet_naar_de_recorder(sensor_mod):
    assert sensor_mod.ReistijdSensor._unrecorded_attributes == frozenset({"*"})


def test_een_reistijd_uit_een_onbekende_vorm_wordt_geen_getal(sensor_mod):
    assert _sensor(sensor_mod, sensor_mod.ReistijdSensor, {"reistijd_min": "34"}).native_value is None
    assert _sensor(sensor_mod, sensor_mod.ReistijdSensor, None).native_value is None
    assert ROUTE  # dezelfde fixture als de coordinator
