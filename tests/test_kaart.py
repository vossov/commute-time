"""De naad tussen sensor en kaart, en de kaart tegenover de README.

De kaart en de sensor vinden elkaar via attribuutnamen. Verandert er aan
één kant een naam, dan blijft de andere kant stil kapot: geen foutmelding,
alleen een lege regel. Deze tests lezen beide kanten en vergelijken ze.
"""
import json
import re
import sys
from pathlib import Path

import pytest

WORTEL = Path(__file__).parent.parent
COMPONENT = WORTEL / "custom_components" / "commute_time"
KAART = COMPONENT / "www" / "commute-time-card.js"
UITVOER = COMPONENT / "uitvoer.py"
README = WORTEL / "README.md"


@pytest.fixture(scope="module")
def kaart_bron():
    return KAART.read_text(encoding="utf-8")


def _blok(bron: str, kop: str, haken: str = "{}") -> str:
    """De inhoud van een functie of lijst, op haakjes geteld."""
    open_haak, dicht_haak = haken
    begin = bron.index(kop)
    i = bron.index(open_haak, begin)
    diepte = 0
    for j in range(i, len(bron)):
        if bron[j] == open_haak:
            diepte += 1
        elif bron[j] == dicht_haak:
            diepte -= 1
            if diepte == 0:
                return bron[i:j + 1]
    raise AssertionError(f"geen sluitend {dicht_haak!r} voor {kop}")


# ── versie en aanmelden ─────────────────────────────────────────────

def test_de_versie_van_de_kaart_loopt_gelijk(const, kaart_bron):
    """Loopt dit uiteen, dan blijft de browser een oude kaart tonen, of zie
    je in het bewerkscherm een ander nummer dan Home Assistant meldt."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    versie = re.search(r"const VERSIE = '([^']+)';", kaart_bron).group(1)
    assert const.VERSION == manifest["version"] == versie


def test_het_kaartbestand_staat_waar_de_integratie_het_zoekt(const):
    assert (COMPONENT / "www" / const.KAART_BESTAND).is_file()
    assert const.KAART_URL == f"/{const.DOMAIN}/{const.KAART_BESTAND}"


def test_de_kaart_meldt_zich_maar_een_keer_aan(kaart_bron):
    """Een tweede `define` met dezelfde naam gooit, en dan stopt de module."""
    for naam in ("commute-time-card", "commute-time-card-editor"):
        assert f"customElements.get('{naam}')" in kaart_bron
    assert "customCards.some(" in kaart_bron


def test_set_hass_vangt_alles(kaart_bron):
    """Een uitzondering in `set hass` wordt een grijze foutkaart tot de
    pagina herlaadt (zie Skywatch). De setter moet daarom alles vangen."""
    setter = _blok(kaart_bron, "set hass(hass) {")
    assert "try {" in setter and "catch (err)" in setter and "_fail(" in setter


# ── kaart en sensor spreken dezelfde taal ───────────────────────────

def _gezet() -> set[str]:
    """Alle sleutels die uitvoer.py in een woordenboek zet."""
    return set(re.findall(r'"(\w+)":', UITVOER.read_text(encoding="utf-8")))


def test_de_kaart_leest_alleen_attributen_die_de_sensor_zet(kaart_bron):
    """In de kaart heten de attributen altijd `a`; zo is dit te lezen."""
    gelezen = set(re.findall(r"\ba\.(\w+)", kaart_bron))
    assert gelezen, "geen enkel a.<veld> gevonden; is de naamgeving veranderd?"
    onbekend = gelezen - _gezet()
    assert not onbekend, f"de kaart leest velden die de sensor niet zet: {sorted(onbekend)}"


def test_sensor_json_is_bij(uitvoer):
    """De fixture waar de kaarttest op draait is wat uitvoer.py nu maakt.

    Faalt dit: draai `python3 tests/maak_sensor_fixture.py` — bewust, en
    kijk in de diff of de kaart de nieuwe vorm ook leest.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    import maak_sensor_fixture

    opgeslagen = (Path(__file__).parent / "fixtures" / "sensor.json").read_text(encoding="utf-8")
    assert opgeslagen == maak_sensor_fixture.tekst()


def test_de_sensor_zet_alles_wat_de_kaart_leest_ook_echt():
    """Andersom: elk veld dat de kaart leest komt in de fixture voor, in
    minstens één toestand. Een veld dat alleen in de broncode staat maar nooit
    gevuld wordt, zou de vorige test ongemerkt laten slagen."""
    staten = json.loads((Path(__file__).parent / "fixtures" / "sensor.json").read_text(encoding="utf-8"))
    aanwezig = set()
    for attributen in staten.values():
        aanwezig |= set(attributen)
    gelezen = set(re.findall(r"\ba\.(\w+)", KAART.read_text(encoding="utf-8")))
    assert not gelezen - aanwezig, f"nooit gevuld: {sorted(gelezen - aanwezig)}"


# ── editor, configuratie en README ──────────────────────────────────

def test_elk_editorveld_bestaat_overal(kaart_bron):
    """Een kaartoptie raakt vier plekken: normaliseer, VELDEN, het
    terugvalformulier en de optietabel in de README."""
    velden = set(re.findall(r"name: '(\w+)'", _blok(kaart_bron, "const VELDEN = [", "[]")))
    genormaliseerd = set(re.findall(r"^\s{4}(\w+):", _blok(kaart_bron, "function normaliseer(config) {"), re.M))
    assert velden == genormaliseerd, f"VELDEN en normaliseer verschillen: {velden ^ genormaliseerd}"

    # het formulier staat als HTML in een string, vóór de handler die het leest
    begin = kaart_bron.index("// terugval zonder ha-form")
    eind = kaart_bron.index("doos.addEventListener('change'", begin)
    terugval = set(re.findall(r'name="(\w+)"', kaart_bron[begin:eind]))
    gelezen = set(re.findall(r"lees\('(\w+)'\)", _blok(kaart_bron, "doos.addEventListener('change'")))
    assert velden == terugval, f"VELDEN en het terugvalformulier verschillen: {velden ^ terugval}"
    assert velden == gelezen, f"het terugvalformulier leest niet elk veld: {velden ^ gelezen}"

    rijen: list[str] = []
    kop_gezien = False
    for regel in README.read_text(encoding="utf-8").splitlines():
        if regel.startswith("### Opties van de kaart"):
            kop_gezien = True
            continue
        if not kop_gezien:
            continue
        if regel.startswith("|"):
            rijen.append(regel)
        elif rijen:
            break
    in_readme = set(re.findall(r"^\| `(\w+)`", "\n".join(rijen), re.M))
    assert velden == in_readme, f"de README-tabel wijkt af: {velden ^ in_readme}"


def test_de_vormgevingen(kaart_bron):
    """Standaard, het HA-thema en Bubble — en voor elk een stuk CSS."""
    opties = set(re.findall(r"value: '(\w+)'", _blok(kaart_bron, "const VORMGEVING = [", "[]")))
    assert opties == {"default", "ha", "bubble"}
    for o in opties - {"default"}:
        assert f"thema-{o}" in kaart_bron


def test_geen_te_nieuwe_syntax_in_het_commentaarloze_bestand(kaart_bron):
    """Snelle controle; tests/floor.mjs leest de syntaxboom en is de echte."""
    zonder = re.sub(r"/\*.*?\*/", "", kaart_bron, flags=re.S)
    zonder = re.sub(r"^\s*//.*$", "", zonder, flags=re.M)
    assert "?." not in zonder.replace("'?.'", "")
    assert "??" not in zonder
    assert "catch {" not in zonder
    assert not re.search(r"(^|[;{\s])gap\s*:", zonder)
