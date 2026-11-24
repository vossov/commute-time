"""De release-notes: elke versie die uitgebracht wordt is beschreven.

HACS toont de naam en de notes van een GitHub-release, en die komen uit
CHANGELOG.md (zie tools/release_notes.py). Zonder deze tests kan een versie
met een lege of ontbrekende beschrijving gewoon uitkomen, en dan staat er in
HACS een kale tekst of alleen een commit-hash.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORTEL = Path(__file__).parent.parent
SCRIPT = WORTEL / "tools" / "release_notes.py"
CHANGELOG = WORTEL / "CHANGELOG.md"
MANIFEST = WORTEL / "custom_components" / "commute_time" / "manifest.json"


@pytest.fixture(scope="module")
def notes():
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def versie():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]


@pytest.fixture(scope="module")
def tekst():
    return CHANGELOG.read_text(encoding="utf-8")


# ── het echte bestand ───────────────────────────────────────────────

def test_de_versie_in_de_manifest_is_beschreven(notes, tekst, versie):
    """Dit is de poort: een versie zonder nette sectie komt niet uit."""
    assert notes.fouten(tekst, versie) == []


def test_elke_versie_in_het_bestand_is_netjes(notes, tekst):
    for s in notes.lees(tekst):
        assert notes.fouten(tekst, s.versie) == [], s.versie


def test_de_nieuwste_versie_staat_bovenaan_en_is_de_huidige(notes, tekst, versie):
    assert notes.lees(tekst)[0].versie == versie, (
        "de bovenste sectie hoort de versie in manifest.json te zijn; "
        "of de versie is niet opgehoogd, of de sectie staat op de verkeerde plek"
    )


def test_de_titel_en_de_tekst_van_de_release(notes, tekst, versie):
    s = notes.sectie(tekst, versie)
    assert notes.titel(s) == f"v{versie} — {s.samenvatting}"
    assert "\n" not in notes.titel(s)
    uit = notes.release_tekst(s)
    assert "### " in uit
    assert not uit.lstrip().startswith(">"), "de samenvatting staat al in de titel"
    assert "CHANGELOG.md" in uit
    assert "Updating" in uit


def test_het_script_geeft_dezelfde_uitkomst_op_de_opdrachtregel(versie):
    def draai(wat):
        return subprocess.run(
            [sys.executable, str(SCRIPT), versie, wat], capture_output=True, text=True, check=False
        )

    assert draai("check").returncode == 0
    titel = draai("titel")
    assert titel.returncode == 0 and titel.stdout.startswith(f"v{versie} — ")
    assert "\n" not in titel.stdout, "de titel moet op één regel staan"
    assert draai("tekst").stdout.strip()


def test_een_onbekende_versie_geeft_een_fout_op_de_opdrachtregel():
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "9.9.9", "check"], capture_output=True, text=True, check=False
    )
    assert p.returncode == 1
    assert "9.9.9" in p.stdout


# ── de regels zelf, op een verzonnen bestand ────────────────────────

GOED = """# Changelog

## [0.2.0] — 2026-11-18

> Tweede

### Added
- iets nieuws

### Fixed
- iets gerepareerd

## [0.1.0] — 2026-11-16

> Eerste

### Added
- begin
"""


def test_een_goed_bestand_heeft_geen_fouten(notes):
    assert notes.fouten(GOED, "0.2.0") == []
    assert notes.fouten(GOED, "0.1.0") == []


def test_de_samenvatting_en_de_tekst_worden_gescheiden(notes):
    s = notes.sectie(GOED, "0.2.0")
    assert s.samenvatting == "Tweede"
    assert s.datum == "2026-11-18"
    assert s.tekst.startswith("### Added")
    assert "Tweede" not in s.tekst
    assert "0.1.0" not in s.tekst, "een sectie loopt niet door in de volgende"


@pytest.mark.parametrize("wijziging, fragment", [
    (lambda t: t.replace("> Tweede\n\n", ""), "samenvatting"),
    (lambda t: t.replace("### Added\n- iets nieuws\n\n", "### Added\n\n"), "geen enkel streepje"),
    (lambda t: t.replace("### Fixed", "### Repaired"), "kent het kopje"),
    (lambda t: t.replace("### Added\n- iets nieuws\n\n### Fixed\n- iets gerepareerd",
                         "### Fixed\n- iets gerepareerd\n\n### Added\n- iets nieuws"), "andere volgorde"),
    (lambda t: t.replace("### Fixed\n- iets gerepareerd", "### Added\n- nog iets"), "twee keer"),
    (lambda t: t.replace("### Added\n- iets nieuws\n\n### Fixed\n- iets gerepareerd\n", "Alleen tekst.\n"), "geen kopje"),
    (lambda t: t.replace("2026-11-18", "2026-13-45"), "datum"),
    (lambda t: t.replace("2026-11-18", "2026-11-10"), "datums lopen niet mee"),
])
def test_wat_er_mis_kan_wordt_gezien(notes, wijziging, fragment):
    problemen = notes.fouten(wijziging(GOED), "0.2.0")
    assert any(fragment in p for p in problemen), problemen


def test_een_versie_zonder_sectie(notes):
    assert "geen sectie" in notes.fouten(GOED, "0.3.0")[0]


def test_de_versies_moeten_van_nieuw_naar_oud_staan(notes):
    omgekeerd = GOED.replace("[0.2.0] — 2026-11-18", "[0.0.9] — 2026-11-18")
    assert any("nieuw naar oud" in p for p in notes.fouten(omgekeerd, "0.1.0"))
