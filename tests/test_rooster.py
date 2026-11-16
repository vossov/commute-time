"""Het rooster en het oordeel.

Getoetst tegen wat je met de klok in de hand zelf kunt narekenen, en rond
de zomertijdwissels van 2026 (29 maart en 25 oktober), want daar gaat
rekenen met kloktijden het eerst mis.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

WERKWEEK = {
    dag: {"show_from": "06:30:00", "show_until": "09:30:00", "arrive_at": "08:30:00"}
    for dag in ("monday", "tuesday", "wednesday", "thursday", "friday")
}


def _nu(tz, *args):
    return datetime(*args, tzinfo=tz)


def _echt(later, eerder):
    """Echte tijd ertussen. `later - eerder` rekent bij één tijdzone-object op
    de wandklok, en juist dat is wat deze tests moeten kunnen zien."""
    return later.astimezone(timezone.utc) - eerder.astimezone(timezone.utc)


# ── tijden lezen ────────────────────────────────────────────────────

@pytest.mark.parametrize("invoer, verwacht", [
    ("06:30", (6, 30, 0)),
    ("06:30:15", (6, 30, 15)),
    (" 7:05 ", (7, 5, 0)),
    ("24:00", None),
    ("06:60", None),
    ("zes uur", None),
    ("", None),
    (None, None),
])
def test_tijden_lezen(rooster, invoer, verwacht):
    t = rooster.lees_tijd(invoer)
    assert (None if t is None else (t.hour, t.minute, t.second)) == verwacht


# ── het venster ─────────────────────────────────────────────────────

def test_binnen_en_buiten_het_venster(rooster, tz):
    # dinsdag 17 november 2026
    assert rooster.plan_nu(WERKWEEK, _nu(tz, 2026, 11, 17, 6, 29)) is None
    plan = rooster.plan_nu(WERKWEEK, _nu(tz, 2026, 11, 17, 6, 30))
    assert plan is not None
    assert plan.aankomst == _nu(tz, 2026, 11, 17, 8, 30)
    # het einde hoort er niet meer bij
    assert rooster.plan_nu(WERKWEEK, _nu(tz, 2026, 11, 17, 9, 30)) is None


def test_geen_venster_in_het_weekend(rooster, tz):
    assert rooster.plan_nu(WERKWEEK, _nu(tz, 2026, 11, 21, 8, 0)) is None  # zaterdag


def test_het_volgende_venster_na_vrijdag_is_maandag(rooster, tz):
    vrijdagavond = _nu(tz, 2026, 11, 20, 18, 0)
    assert rooster.volgende_begin(WERKWEEK, vrijdagavond) == _nu(tz, 2026, 11, 23, 6, 30)


def test_het_volgende_venster_later_vandaag(rooster, tz):
    assert rooster.volgende_begin(WERKWEEK, _nu(tz, 2026, 11, 17, 5, 0)) == _nu(tz, 2026, 11, 17, 6, 30)


def test_zonder_enig_venster_is_er_geen_volgende(rooster, tz):
    assert rooster.volgende_begin({}, _nu(tz, 2026, 11, 17, 5, 0)) is None


def test_een_omgekeerd_venster_telt_niet(rooster, tz):
    r = {"tuesday": {"show_from": "09:00", "show_until": "07:00"}}
    assert rooster.dagplan(r, date(2026, 11, 17), tz) is None


def test_de_zomertijd_verschuift_het_venster_niet(rooster, tz):
    """Op 29 maart 2026 gaat de klok vooruit; 06:30 blijft 06:30 op de klok."""
    r = {"sunday": {"show_from": "06:30", "show_until": "09:30", "arrive_at": "08:30"}}
    plan = rooster.dagplan(r, date(2026, 3, 29), tz)
    assert plan.van.hour == 6 and plan.van.minute == 30
    assert plan.van.utcoffset() == timedelta(hours=2)
    # en het venster is drie echte uren lang, niet twee of vier
    assert _echt(plan.tot, plan.van) == timedelta(hours=3)


def test_een_tijd_die_niet_bestaat_wordt_een_echte_tijd(rooster, tz):
    """02:30 bestaat niet op 29 maart; het wordt 03:30 zomertijd."""
    r = {"sunday": {"show_from": "02:30", "show_until": "05:00"}}
    plan = rooster.dagplan(r, date(2026, 3, 29), tz)
    assert (plan.van.hour, plan.van.minute) == (3, 30)


def test_wintertijd_venster_over_de_wissel(rooster, tz):
    """25 oktober 2026: de klok gaat terug. 01:00–04:00 duurt dan vier uur."""
    r = {"sunday": {"show_from": "01:00", "show_until": "04:00"}}
    plan = rooster.dagplan(r, date(2026, 10, 25), tz)
    assert _echt(plan.tot, plan.van) == timedelta(hours=4)


def test_een_aankomst_over_de_wisselnacht_klopt_op_de_klok(rooster, tz):
    """25 oktober 2026, 02:50 zomertijd, half uur rijden.

    Echt verstreken: 30 minuten, en om 03:00 zomertijd wordt het 02:00
    wintertijd — je komt dus om 02:20 aan. Op de wandklok optellen gaf 03:20,
    een uur te laat."""
    nu = datetime(2026, 10, 25, 2, 50, tzinfo=tz)  # fold=0: de eerste 02:50
    o = rooster.beoordeel(nu=nu, doel=None, reistijd_nu_s=1800, stoptijd_s=0, vertrek_tomtom=None)
    assert rooster.hhmm(o.aankomst) == "02:20"
    assert _echt(o.aankomst, nu) == timedelta(minutes=30)


def test_tomtom_noemt_de_tijd_in_een_andere_zone(rooster, tz):
    """Een bestemming in Engeland: TomTom zegt 07:00+00:00, dat is 08:00 hier."""
    nu = _nu(tz, 2026, 11, 17, 6, 0)
    vertrek = datetime(2026, 11, 17, 7, 0, tzinfo=timezone.utc)
    o = rooster.beoordeel(
        nu=nu, doel=_nu(tz, 2026, 11, 17, 12, 0), reistijd_nu_s=3600, stoptijd_s=0,
        vertrek_tomtom=vertrek,
    )
    assert rooster.hhmm(o.vertrek) == "08:00"


# ── het rooster nakijken ────────────────────────────────────────────

def test_fouten_in_het_rooster(rooster):
    fouten = rooster.fouten_in_rooster({
        "monday": {"show_from": "07:00"},
        "tuesday": {"show_from": "09:00", "show_until": "08:00"},
        "wednesday": {"arrive_at": "08:30"},
        "thursday": {"show_from": "07:00", "show_until": "09:00", "arrive_at": "10:00"},
        "friday": {},
    })
    assert fouten == {
        "monday": "venster_half",
        "tuesday": "venster_omgekeerd",
        "wednesday": "aankomst_zonder_venster",
    }


def test_het_standaardrooster_klopt(rooster, const):
    assert rooster.fouten_in_rooster(const.DEFAULT_SCHEDULE) == {}


# ── het oordeel ─────────────────────────────────────────────────────

def test_vertrek_om(rooster, tz):
    nu = _nu(tz, 2026, 11, 17, 7, 30)
    doel = _nu(tz, 2026, 11, 17, 8, 30)
    o = rooster.beoordeel(
        nu=nu, doel=doel, reistijd_nu_s=30 * 60, stoptijd_s=0,
        vertrek_tomtom=_nu(tz, 2026, 11, 17, 7, 52, 40),
    )
    assert o.status == "vertrek_om"
    # naar beneden afgerond: 07:52:40 wordt 07:52, niet 07:53
    assert o.vertrek == _nu(tz, 2026, 11, 17, 7, 52)
    assert o.aankomst == _nu(tz, 2026, 11, 17, 8, 0)
    assert o.te_laat_min is None


def test_de_stoptijd_haalt_het_vertrek_naar_voren(rooster, tz):
    nu = _nu(tz, 2026, 11, 17, 7, 0)
    o = rooster.beoordeel(
        nu=nu, doel=_nu(tz, 2026, 11, 17, 8, 30), reistijd_nu_s=30 * 60,
        stoptijd_s=2 * 5 * 60,  # twee stops van vijf minuten
        vertrek_tomtom=_nu(tz, 2026, 11, 17, 7, 50),
    )
    assert o.vertrek == _nu(tz, 2026, 11, 17, 7, 40)
    assert o.aankomst == _nu(tz, 2026, 11, 17, 7, 40)


def test_vertrek_nu_als_de_vertrektijd_voorbij_is_maar_het_nog_lukt(rooster, tz):
    nu = _nu(tz, 2026, 11, 17, 7, 55)
    o = rooster.beoordeel(
        nu=nu, doel=_nu(tz, 2026, 11, 17, 8, 30), reistijd_nu_s=30 * 60, stoptijd_s=0,
        vertrek_tomtom=_nu(tz, 2026, 11, 17, 7, 52),
    )
    assert o.status == "vertrek_nu"
    assert o.aankomst == _nu(tz, 2026, 11, 17, 8, 25)


def test_te_laat(rooster, tz):
    nu = _nu(tz, 2026, 11, 17, 8, 10)
    o = rooster.beoordeel(
        nu=nu, doel=_nu(tz, 2026, 11, 17, 8, 30), reistijd_nu_s=30 * 60 + 20, stoptijd_s=0,
        vertrek_tomtom=_nu(tz, 2026, 11, 17, 7, 52),
    )
    assert o.status == "te_laat"
    # 08:40:20 is tien minuten en twintig seconden te laat: dat is elf
    assert o.te_laat_min == 11


def test_zonder_aankomsttijd_geen_vertrektijd(rooster, tz):
    o = rooster.beoordeel(
        nu=_nu(tz, 2026, 11, 17, 7, 0), doel=None, reistijd_nu_s=600, stoptijd_s=0,
        vertrek_tomtom=None,
    )
    assert o.status == "geen_doel"
    assert o.vertrek is None
    assert o.aankomst == _nu(tz, 2026, 11, 17, 7, 10)


def test_na_de_aankomsttijd(rooster, tz):
    o = rooster.beoordeel(
        nu=_nu(tz, 2026, 11, 17, 8, 31), doel=_nu(tz, 2026, 11, 17, 8, 30),
        reistijd_nu_s=600, stoptijd_s=0, vertrek_tomtom=None,
    )
    assert o.status == "doel_voorbij"
    assert o.vertrek is None


def test_zonder_antwoord_met_aankomsttijd_geen_verzonnen_vertrektijd(rooster, tz):
    """Kwam de aankomstberekening niet terug, dan is er geen vertrektijd.

    Terugrekenen met de reistijd van nu zou kunnen, maar dat is een andere
    berekening dan wat de kaart belooft; dan liever "vertrek nu" of "te laat"
    op grond van wat er wél gemeten is."""
    o = rooster.beoordeel(
        nu=_nu(tz, 2026, 11, 17, 7, 0), doel=_nu(tz, 2026, 11, 17, 8, 30),
        reistijd_nu_s=1800, stoptijd_s=0, vertrek_tomtom=None,
    )
    assert o.vertrek is None
    assert o.status == "vertrek_nu"


def test_de_streeftijd_is_de_aankomsttijd_min_de_marge(rooster, tz):
    doel = _nu(tz, 2026, 11, 17, 8, 30)
    assert rooster.streeftijd(doel, 5) == _nu(tz, 2026, 11, 17, 8, 25)
    assert rooster.streeftijd(doel, -3) == doel
