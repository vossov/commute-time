"""Het rooster en het oordeel: wanneer is de route in beeld, en wanneer moet
je weg.

Geen Home Assistant en geen netwerk; tests/test_rooster.py controleert alles
hier, ook rond de zomertijd.

Het rooster komt uit het optiescherm, per weekdag:

    {"monday": {"show_from": "06:30:00", "show_until": "09:30:00",
                "arrive_at": "08:30:00"}, ...}

Een dag zonder begin- of eindtijd is een dag zonder route. Een aankomsttijd
mag ontbreken; dan is er geen vertrektijd te berekenen en toont de kaart de
reistijd en wanneer je aankomt als je nu vertrekt.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any

from .const import CONF_ARRIVE_AT, CONF_SHOW_FROM, CONF_SHOW_UNTIL, DAGEN

# Hoe ver vooruit we naar het volgende venster zoeken: een week plus vandaag.
ZOEK_DAGEN = 8


def lees_tijd(waarde: Any) -> time | None:
    """`06:30`, `06:30:00` of een `time`; leeg of onzin wordt None."""
    if waarde is None:
        return None
    if isinstance(waarde, time):
        return waarde.replace(tzinfo=None, microsecond=0)
    tekst = str(waarde).strip()
    delen = tekst.split(":")
    if len(delen) not in (2, 3):
        return None
    try:
        getallen = [int(d) for d in delen]
    except ValueError:
        return None
    uur, minuut = getallen[0], getallen[1]
    seconde = getallen[2] if len(getallen) == 3 else 0
    if not (0 <= uur <= 23 and 0 <= minuut <= 59 and 0 <= seconde <= 59):
        return None
    return time(uur, minuut, seconde)


def hhmm(moment: datetime | time | None) -> str | None:
    """`07:52`, of None."""
    if moment is None:
        return None
    return f"{moment.hour:02d}:{moment.minute:02d}"


def _u(moment: datetime) -> datetime:
    """Hetzelfde moment in UTC, om mee te vergelijken en te rekenen.

    Python rekent het verschil tussen twee tijdstippen met hetzelfde
    tijdzone-object uit op de wandklok: 04:00 min 01:00 is drie uur, ook op
    de nacht dat de klok teruggaat en er vier uur tussen zit. Hetzelfde
    geldt voor optellen en vergelijken. Alles wat rekent gaat daarom via
    UTC; alleen wat getoond wordt staat in de tijdzone van Home Assistant.
    """
    return moment.astimezone(timezone.utc)


def plus(moment: datetime, seconden: float) -> datetime:
    """`moment` plus zoveel echte seconden, terug in de eigen tijdzone."""
    return (_u(moment) + timedelta(seconds=seconden)).astimezone(moment.tzinfo)


def seconden_tussen(later: datetime, eerder: datetime) -> float:
    """Echte seconden van `eerder` tot `later`."""
    return (_u(later) - _u(eerder)).total_seconds()


def _op(dag: date, tijd: time, tz: tzinfo) -> datetime:
    """Een kloktijd op een dag, in de tijdzone van Home Assistant.

    Via UTC heen en terug, zodat een tijd die door de zomertijd niet bestaat
    (02:30 op de laatste zondag van maart) een echte tijd wordt in plaats van
    een datetime die er bij vergelijken een uur naast zit.
    """
    naief = datetime.combine(dag, tijd).replace(tzinfo=tz)
    return naief.astimezone(timezone.utc).astimezone(tz)


@dataclass(frozen=True)
class Dagplan:
    """Het rooster van één dag, als echte tijdstippen."""

    van: datetime
    tot: datetime
    aankomst: datetime | None


def dagplan(rooster: dict[str, Any], dag: date, tz: tzinfo) -> Dagplan | None:
    """Het plan voor `dag`, of None als de route die dag niet in beeld is.

    Een venster dat over middernacht loopt (tot vóór van) telt niet: dat is
    vrijwel altijd een tikfout, en een route om drie uur 's nachts kan als
    twee dagen worden ingesteld.
    """
    regel = rooster.get(DAGEN[dag.weekday()]) if isinstance(rooster, dict) else None
    if not isinstance(regel, dict):
        return None
    van = lees_tijd(regel.get(CONF_SHOW_FROM))
    tot = lees_tijd(regel.get(CONF_SHOW_UNTIL))
    if van is None or tot is None or tot <= van:
        return None
    aankomst = lees_tijd(regel.get(CONF_ARRIVE_AT))
    return Dagplan(
        van=_op(dag, van, tz),
        tot=_op(dag, tot, tz),
        aankomst=_op(dag, aankomst, tz) if aankomst is not None else None,
    )


def plan_nu(rooster: dict[str, Any], nu: datetime) -> Dagplan | None:
    """Het plan van vandaag als `nu` binnen het venster valt, anders None."""
    plan = dagplan(rooster, nu.date(), nu.tzinfo)
    if plan is not None and _u(plan.van) <= _u(nu) < _u(plan.tot):
        return plan
    return None


def volgende_begin(rooster: dict[str, Any], nu: datetime) -> datetime | None:
    """Het begin van het eerstvolgende venster ná `nu`; None als er geen is."""
    for i in range(ZOEK_DAGEN):
        plan = dagplan(rooster, nu.date() + timedelta(days=i), nu.tzinfo)
        if plan is not None and _u(plan.van) > _u(nu):
            return plan.van
    return None


def fouten_in_rooster(rooster: dict[str, Any]) -> dict[str, str]:
    """Per dag wat er niet klopt, voor het optiescherm.

    Halve vensters worden niet stil genegeerd: wie alleen een begintijd
    invult, verwacht de route te zien, en zou anders nooit weten waarom hij
    wegblijft.
    """
    fouten: dict[str, str] = {}
    for dag in DAGEN:
        regel = rooster.get(dag) or {}
        van = lees_tijd(regel.get(CONF_SHOW_FROM))
        tot = lees_tijd(regel.get(CONF_SHOW_UNTIL))
        aankomst = lees_tijd(regel.get(CONF_ARRIVE_AT))
        if (van is None) != (tot is None):
            fouten[dag] = "venster_half"
        elif van is not None and tot is not None and tot <= van:
            fouten[dag] = "venster_omgekeerd"
        elif aankomst is not None and van is None:
            fouten[dag] = "aankomst_zonder_venster"
    return fouten


# ── het oordeel ──────────────────────────────────────────────────────


def naar_minuut_omlaag(moment: datetime) -> datetime:
    """Seconden eraf, naar beneden. Een vertrektijd van 07:52:40 tonen als
    07:53 laat je 20 seconden te laat vertrekken; 07:52 niet."""
    return moment.replace(second=0, microsecond=0)


def streeftijd(doel: datetime, marge_min: int) -> datetime:
    """Wanneer je er wilt zijn: de aankomsttijd min de marge."""
    return plus(doel, -60 * max(0, int(marge_min)))


@dataclass(frozen=True)
class Oordeel:
    """Wat de kaart en de sensoren moeten zeggen."""

    status: str
    vertrek: datetime | None
    aankomst: datetime | None
    te_laat_min: int | None


def beoordeel(
    *,
    nu: datetime,
    doel: datetime | None,
    reistijd_nu_s: int,
    stoptijd_s: int,
    vertrek_tomtom: datetime | None,
) -> Oordeel:
    """Het oordeel over dit moment.

    `reistijd_nu_s` komt uit de berekening met vertrek nu, `vertrek_tomtom`
    uit die met `arriveAt` (de streeftijd: aankomsttijd min marge). Beide van
    TomTom; hier wordt niets geschat, alleen opgeteld en vergeleken.

    De stoptijd telt TomTom niet mee, want die kent hij niet. Hij gaat er
    hier bij: het vertrek schuift zoveel naar voren, de aankomst zoveel naar
    achteren. Dat het verkeer op dat eerdere moment anders kan zijn, valt
    erbuiten; de README zegt het erbij.

    Statussen:

      geen_doel     geen aankomsttijd vandaag
      doel_voorbij  de aankomsttijd is al geweest
      vertrek_om    je hoeft nog niet weg; `vertrek` zegt wanneer
      vertrek_nu    de vertrektijd is daar of voorbij, maar nu weggaan haalt
                    de aankomsttijd nog (mogelijk zonder de volle marge)
      te_laat       ook nu weggaan haalt de aankomsttijd niet
    """
    aankomst = plus(nu, reistijd_nu_s + stoptijd_s)
    if doel is None:
        return Oordeel("geen_doel", None, aankomst, None)
    if _u(nu) >= _u(doel):
        return Oordeel("doel_voorbij", None, aankomst, None)

    vertrek = None
    if vertrek_tomtom is not None:
        # TomTom noemt de tijd in de zone van de bestemming; wij tonen hem op
        # de klok van Home Assistant
        lokaal = vertrek_tomtom.astimezone(nu.tzinfo)
        vertrek = naar_minuut_omlaag(plus(lokaal, -stoptijd_s))
    if vertrek is not None and _u(vertrek) > _u(nu):
        return Oordeel("vertrek_om", vertrek, aankomst, None)
    if _u(aankomst) <= _u(doel):
        return Oordeel("vertrek_nu", vertrek, aankomst, None)
    te_laat = math.ceil(seconden_tussen(aankomst, doel) / 60)
    return Oordeel("te_laat", vertrek, aankomst, te_laat)
