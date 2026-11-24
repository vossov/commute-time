"""Haalt de release-notes van één versie uit CHANGELOG.md.

De release-workflow gebruikt dit om de titel en de tekst van een GitHub-release
te maken, en de tests gebruiken het om te zien of elke versie netjes
beschreven is. Zo komt wat HACS laat zien uit één bron, en kan een versie
zonder beschrijving niet worden uitgebracht.

    python3 tools/release_notes.py 0.2.0 titel     # v0.2.0 — Bubble-stijl nagebouwd …
    python3 tools/release_notes.py 0.2.0 tekst     # de notes van die versie, als markdown
    python3 tools/release_notes.py 0.2.0 check     # exit 1 en wat er mist, of niets

Geen afhankelijkheden: het draait in de CI zonder installatie.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
REPO = os.environ.get("GITHUB_REPOSITORY", "vossov/commute-time")

# de kop van een versie; de streep is een gedachtestreep, zoals in het bestand
KOP = re.compile(r"^## \[(\d+\.\d+\.\d+)\] — (\d{4}-\d{2}-\d{2})[ \t]*$", re.M)
ONDERDEEL = re.compile(r"^### (.+?)[ \t]*$", re.M)

# de kopjes die in een sectie mogen staan, in vaste volgorde
ONDERDELEN = ("Nieuw", "Verbeterd", "Opgelost", "Let op")


class Sectie(NamedTuple):
    versie: str
    datum: str
    samenvatting: str  # de regel als citaat; wordt de titel van de release
    tekst: str  # alles daaronder, zonder de samenvatting


def lees(tekst: str) -> list[Sectie]:
    """Alle versies uit het bestand, zoals ze er staan (nieuwste bovenaan)."""
    koppen = list(KOP.finditer(tekst))
    uit: list[Sectie] = []
    for i, kop in enumerate(koppen):
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        romp = tekst[kop.end():einde].strip("\n")
        regels = romp.split("\n")
        samenvatting = ""
        # de samenvatting is de eerste niet-lege regel, als die een citaat is
        for j, regel in enumerate(regels):
            if not regel.strip():
                continue
            if regel.startswith("> "):
                samenvatting = regel[2:].strip()
                regels = regels[j + 1:]
            break
        uit.append(Sectie(kop.group(1), kop.group(2), samenvatting, "\n".join(regels).strip("\n")))
    return uit


def sectie(tekst: str, versie: str) -> Sectie | None:
    for s in lees(tekst):
        if s.versie == versie:
            return s
    return None


def titel(s: Sectie) -> str:
    return f"v{s.versie} — {s.samenvatting}"


def release_tekst(s: Sectie) -> str:
    """De tekst van de GitHub-release: de notes, met onderaan hoe je hem krijgt."""
    return (
        s.tekst.strip()
        + "\n\n---\n\n"
        + "**Bijwerken:** open HACS, kies *Commute Time* en dan *Bijwerken*; "
        + "herstart daarna Home Assistant.\n"
        + f"**Alle versies:** [CHANGELOG.md](https://github.com/{REPO}/blob/main/CHANGELOG.md)\n"
    )


def fouten(tekst: str, versie: str) -> list[str]:
    """Wat er aan de beschrijving van `versie` ontbreekt of niet klopt.

    Leeg betekent: klaar om uit te brengen. Alleen deze versie wordt streng
    nagekeken; de volgorde en datums van het hele bestand ook, want een
    verkeerd geplaatste versie geeft in HACS een verkeerde "nieuwste".
    """
    uit: list[str] = []
    alle = lees(tekst)
    s = sectie(tekst, versie)
    if s is None:
        return [f"CHANGELOG.md heeft geen sectie “## [{versie}] — jjjj-mm-dd”"]
    if not s.samenvatting:
        uit.append(f"[{versie}] mist de samenvatting: een regel die met “> ” begint, direct onder de kop")
    onderdelen = list(ONDERDEEL.finditer(s.tekst))
    if not onderdelen:
        uit.append(f"[{versie}] heeft geen kopje (### Nieuw, Verbeterd, Opgelost of Let op)")
    gezien: list[str] = []
    for i, kop in enumerate(onderdelen):
        naam = kop.group(1)
        if naam not in ONDERDELEN:
            uit.append(f"[{versie}] kent het kopje “{naam}” niet; kies uit {', '.join(ONDERDELEN)}")
        elif naam in gezien:
            uit.append(f"[{versie}] heeft het kopje “{naam}” twee keer")
        gezien.append(naam)
        einde = onderdelen[i + 1].start() if i + 1 < len(onderdelen) else len(s.tekst)
        streepjes = [r for r in s.tekst[kop.end():einde].split("\n") if r.startswith("- ") and r[2:].strip()]
        if not streepjes:
            uit.append(f"[{versie}] heeft onder “{naam}” geen enkel streepje")
    # de volgorde van de kopjes volgt ONDERDELEN
    volgorde = [ONDERDELEN.index(n) for n in gezien if n in ONDERDELEN]
    if volgorde != sorted(volgorde):
        uit.append(f"[{versie}] zet de kopjes in een andere volgorde dan {' → '.join(ONDERDELEN)}")

    # het hele bestand: nieuwste bovenaan, geldige en oplopende datums
    versies = [tuple(int(x) for x in a.versie.split(".")) for a in alle]
    if versies != sorted(versies, reverse=True):
        uit.append("de versies staan niet van nieuw naar oud")
    for a in alle:
        try:
            date.fromisoformat(a.datum)
        except ValueError:
            uit.append(f"[{a.versie}] heeft een datum die niet bestaat: {a.datum}")
    datums = [a.datum for a in alle]
    if datums != sorted(datums, reverse=True):
        uit.append("de datums lopen niet mee met de versies (nieuwste bovenaan)")
    return uit


def main(argumenten: list[str]) -> int:
    if len(argumenten) != 2 or argumenten[1] not in ("titel", "tekst", "check"):
        print(__doc__, file=sys.stderr)
        return 2
    versie, wat = argumenten
    tekst = CHANGELOG.read_text(encoding="utf-8")
    problemen = fouten(tekst, versie)
    if wat == "check":
        for p in problemen:
            print(f"::error::{p}")
        return 1 if problemen else 0
    if problemen:
        for p in problemen:
            print(p, file=sys.stderr)
        return 1
    s = sectie(tekst, versie)
    assert s is not None
    # zonder extra regeleinde: de titel hoort op één regel, en de tekst eindigt er al op
    print(titel(s) if wat == "titel" else release_tekst(s), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
