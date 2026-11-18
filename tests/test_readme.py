"""De README en de documenten daaronder: geen link of afbeelding die nergens heen wijst.

HACS toont de README, en daar werken relatieve paden vaak niet; daarom staan
alle links en afbeeldingen als volledig adres naar `main`. Dat betekent dat
een hernoemd of verwijderd bestand pas stuk gaat nadat het gepusht is. Deze
tests kijken vooraf of elk adres naar iets in deze repo wijst dat er is, en
elk `#anker` naar een kop die bestaat.
"""
import re
from pathlib import Path

import pytest

WORTEL = Path(__file__).parent.parent
REPO = "vossov/time-to-leave"
BLOB = f"https://github.com/{REPO}/blob/main/"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"

DOCUMENTEN = [WORTEL / "README.md", *sorted((WORTEL / "docs").glob("*.md")), WORTEL / "CHANGELOG.md"]


def _slug(kop: str) -> str:
    """Het anker dat GitHub van een kop maakt: kleine letters, leestekens weg,
    spaties een streepje."""
    kop = kop.strip().lower()
    kop = re.sub(r"[^\w\- ]", "", kop, flags=re.UNICODE)
    return kop.replace(" ", "-")


def _ankers(pad: Path) -> set[str]:
    uit = set()
    for regel in pad.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", regel)
        if m:
            uit.add(_slug(m.group(1)))
    return uit


def _adressen(tekst: str) -> list[str]:
    """Alle adressen in markdown-links en in src/href van HTML."""
    uit = []
    for markdown, html in re.findall(r"\]\((https?://[^)\s]+)\)|(?:src|href)=\"(https?://[^\"]+)\"", tekst):
        uit.append(markdown or html)
    return uit


@pytest.fixture(scope="module")
def readme():
    return (WORTEL / "README.md").read_text(encoding="utf-8")


# ── de links naar deze repo ─────────────────────────────────────────

@pytest.mark.parametrize("document", DOCUMENTEN, ids=lambda p: p.name)
def test_elke_link_naar_deze_repo_wijst_naar_iets_dat_er_is(document):
    problemen = []
    for adres in _adressen(document.read_text(encoding="utf-8")):
        if adres.startswith(BLOB):
            rest = adres[len(BLOB):]
            pad, _, anker = rest.partition("#")
            doel = WORTEL / pad
            if not doel.is_file():
                problemen.append(f"{adres}: {pad} bestaat niet")
            elif anker and doel.suffix == ".md" and anker not in _ankers(doel):
                problemen.append(f"{adres}: kop #{anker} staat niet in {pad}")
        elif adres.startswith(RAW):
            pad = adres[len(RAW):]
            if not (WORTEL / pad).is_file():
                problemen.append(f"{adres}: {pad} bestaat niet")
    assert not problemen, "\n".join(problemen)


@pytest.mark.parametrize("document", [WORTEL / "README.md", WORTEL / "CHANGELOG.md"], ids=lambda p: p.name)
def test_geen_relatieve_links_naar_bestanden(document):
    """In HACS en in de release-notes werkt `docs/x.md` niet; het moet een
    volledig adres zijn. (Ankers binnen de pagina, `#kop`, mogen wel.) Alleen
    de README en de changelog worden buiten GitHub gelezen; de documenten
    onder docs niet."""
    tekst = document.read_text(encoding="utf-8")
    relatief = re.findall(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)", tekst)
    assert not relatief, f"relatieve links in {document.name}: {relatief}"


# ── de inhoudsopgave ────────────────────────────────────────────────

def test_de_inhoudsopgave_wijst_naar_koppen_die_bestaan(readme):
    ankers = _ankers(WORTEL / "README.md")
    opgave = re.search(r"## Inhoud\n(.+?)\n## ", readme, flags=re.S).group(1)
    gevonden = re.findall(r"\]\(#([^)]+)\)", opgave)
    assert gevonden, "geen inhoudsopgave gevonden"
    ontbreekt = [a for a in gevonden if a not in ankers]
    assert not ontbreekt, f"de inhoudsopgave wijst naar koppen die er niet zijn: {ontbreekt}"


def test_elke_kop_van_niveau_twee_staat_in_de_inhoudsopgave(readme):
    """Een nieuwe sectie zonder regel in de inhoudsopgave valt niet op."""
    opgave = re.search(r"## Inhoud\n(.+?)\n## ", readme, flags=re.S).group(1)
    in_opgave = set(re.findall(r"\]\(#([^)]+)\)", opgave))
    koppen = re.findall(r"^## (.+)$", readme, flags=re.M)
    ontbreekt = [k for k in koppen if k != "Inhoud" and _slug(k) not in in_opgave]
    assert not ontbreekt, f"niet in de inhoudsopgave: {ontbreekt}"


# ── de afbeeldingen ─────────────────────────────────────────────────

def test_de_afbeeldingen_hebben_een_beschrijving_en_een_voorbeeldmelding(readme):
    for img in re.findall(r"<img [^>]+>", readme):
        assert re.search(r'alt="[^"]{5,}"', img), f"afbeelding zonder beschrijving: {img}"
    # de afbeeldingen van de kaart zijn getekend met voorbeeldgegevens, buiten
    # Home Assistant; dat moet erbij staan, anders lijkt het een schermafbeelding
    assert "Voorbeeldgegevens" in readme and "geen schermafbeelding" in readme
