"""Config flow voor Commute Time.

Toevoegen is één route: een naam, de TomTom-sleutel, het begin, eventueel
tussenstops, en de bestemming. Daarna een bevestiging met de adressen zoals
TomTom ze vond — "Stationsstraat 1" ligt in tientallen plaatsen, en een
verkeerd gevonden adres zie je anders pas aan een vreemde vertrektijd.

Alles komt in `ConfigEntry.options`, ook de route zelf, zodat elk onderdeel
later via "Configureren" kan worden aangepast. Het optiescherm heeft twee
stappen: de route, en het rooster per weekdag.

Niet beproefd in een draaiende Home Assistant: de tests bouwen de schema's
met gestubde HA-modules, wat niets zegt over hoe de secties per weekdag er
in het scherm uitzien.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .adressen import EntiteitZonderLocatie, Zoeker, lijst_via
from .const import (
    CONF_ALTERNATIVES,
    CONF_API_KEY,
    CONF_AVOID,
    CONF_DESTINATION,
    CONF_MARGIN_MINUTES,
    CONF_NAME,
    CONF_SCAN_MINUTES,
    CONF_START,
    CONF_STOP_MINUTES,
    CONF_TRAVEL_MODE,
    CONF_VIA,
    DAGEN,
    DAGVELDEN,
    DEFAULT_NAME,
    DEFAULT_SCHEDULE,
    DEFAULT_START,
    DOMAIN,
    MAX_ALTERNATIVES,
    MAX_MARGIN_MINUTES,
    MAX_SCAN_MINUTES,
    MAX_STOP_MINUTES,
    MAX_VIA,
    MIN_ALTERNATIVES,
    MIN_MARGIN_MINUTES,
    MIN_SCAN_MINUTES,
    MIN_STOP_MINUTES,
    OPTION_DEFAULTS,
    VERMIJD,
    VERVOER,
)
from .coordinator import AGENT, lees_opties
from .rooster import fouten_in_rooster
from .tomtom import AdresNietGevonden, GeenRoute, TomTomFout, TomTomGeweigerd, lees_routes, route_url, vraag

ROUTEVELDEN = (CONF_API_KEY, CONF_START, CONF_VIA, CONF_DESTINATION)
DAGNAMEN = ("maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag")


def _tekst(**config: Any) -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(**config))


def _minuten(laag: int, hoog: int) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=laag, max=hoog, step=1, mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    )


def _routeschema(huidig: dict[str, Any], *, met_naam: bool) -> vol.Schema:
    """De velden van de route; bij toevoegen met de naam ervoor."""
    velden: dict[Any, Any] = {}
    if met_naam:
        velden[vol.Required(CONF_NAME, default=huidig.get(CONF_NAME, DEFAULT_NAME))] = _tekst()
    velden.update({
        vol.Required(CONF_API_KEY, default=huidig.get(CONF_API_KEY, "")): _tekst(
            type=selector.TextSelectorType.PASSWORD
        ),
        vol.Required(CONF_START, default=huidig.get(CONF_START, DEFAULT_START)): _tekst(),
        # optioneel en leeg te maken: met `suggested_value` in plaats van
        # `default`, anders komt een gewiste tussenstop terug
        vol.Optional(CONF_VIA, description={"suggested_value": huidig.get(CONF_VIA, "")}): _tekst(
            multiline=True
        ),
        vol.Required(CONF_DESTINATION, default=huidig.get(CONF_DESTINATION, "")): _tekst(),
    })
    return vol.Schema(velden)


def _optieschema(huidig: dict[str, Any]) -> vol.Schema:
    """De route plus hoe hij berekend en getoond wordt."""
    velden = dict(_routeschema(huidig, met_naam=False).schema)
    velden.update({
        vol.Required(CONF_MARGIN_MINUTES, default=huidig[CONF_MARGIN_MINUTES]): _minuten(
            MIN_MARGIN_MINUTES, MAX_MARGIN_MINUTES
        ),
        vol.Required(CONF_STOP_MINUTES, default=huidig[CONF_STOP_MINUTES]): _minuten(
            MIN_STOP_MINUTES, MAX_STOP_MINUTES
        ),
        vol.Required(CONF_TRAVEL_MODE, default=huidig[CONF_TRAVEL_MODE]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(VERVOER), translation_key=CONF_TRAVEL_MODE,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_AVOID, default=list(huidig[CONF_AVOID])): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(VERMIJD), translation_key=CONF_AVOID, multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
        vol.Required(CONF_ALTERNATIVES, default=huidig[CONF_ALTERNATIVES]): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_ALTERNATIVES, max=MAX_ALTERNATIVES, step=1,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_SCAN_MINUTES, default=huidig[CONF_SCAN_MINUTES]): _minuten(
            MIN_SCAN_MINUTES, MAX_SCAN_MINUTES
        ),
    })
    return vol.Schema(velden)


def _roosterschema(rooster: dict[str, Any]) -> vol.Schema:
    """Per weekdag een sectie met drie tijden, allemaal leeg te maken.

    Een dag zonder iets ingevuld staat ingeklapt; zo staat een werkweek
    open en het weekend dicht.
    """
    velden: dict[Any, Any] = {}
    for dag in DAGEN:
        huidig = rooster.get(dag) or {}
        binnen = {
            vol.Optional(veld, description={"suggested_value": huidig.get(veld)}): selector.TimeSelector()
            for veld in DAGVELDEN
        }
        velden[vol.Required(dag)] = section(
            vol.Schema(binnen), {"collapsed": not any(huidig.get(v) for v in DAGVELDEN)}
        )
    return vol.Schema(velden)


def _lees_rooster(invoer: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Wat het scherm teruggeeft, met een gewist veld als None."""
    return {
        dag: {veld: ((invoer.get(dag) or {}).get(veld) or None) for veld in DAGVELDEN}
        for dag in DAGEN
    }


def _geweigerd(fout: TomTomGeweigerd) -> str:
    """De foutcode voor een geweigerde sleutel, per dienst.

    Het scherm noemt zo welke van de twee aanroepen TomTom weigerde. Het
    zegt niet welk product in het portaal ontbreekt; dat staat daar achter
    een inlog en is nooit nagekeken.
    """
    return {
        "search": "sleutel_geweigerd_search",
        "routing": "sleutel_geweigerd_routing",
    }.get(fout.dienst, "sleutel_geweigerd")


async def controleer_route(hass: Any, invoer: dict[str, Any]) -> tuple[dict[str, str], list[Any], int | None]:
    """Zoek elk adres op en vraag één route.

    Geeft de fouten per veld, de gevonden punten en de reistijd nu (minuten)
    terug. Elke fout van TomTom wordt een melding in het scherm, nooit een
    uitzondering.
    """
    sleutel = str(invoer.get(CONF_API_KEY, "")).strip()
    fouten: dict[str, str] = {}
    if not sleutel:
        return {CONF_API_KEY: "sleutel_leeg"}, [], None
    stops = lijst_via(invoer.get(CONF_VIA))
    if len([r for r in str(invoer.get(CONF_VIA) or "").replace(";", "\n").split("\n") if r.strip()]) > MAX_VIA:
        return {CONF_VIA: "te_veel_stops"}, [], None

    sessie = async_get_clientsession(hass)
    zoeker = Zoeker(hass, sessie, sleutel, AGENT)
    punten = []
    for veld, tekst in [(CONF_START, invoer.get(CONF_START)), *[(CONF_VIA, s) for s in stops],
                        (CONF_DESTINATION, invoer.get(CONF_DESTINATION))]:
        try:
            punten.append(await zoeker.vind(str(tekst or "")))
        except EntiteitZonderLocatie:
            fouten[veld] = "geen_locatie"
        except AdresNietGevonden:
            fouten[veld] = "adres_niet_gevonden"
        except TomTomGeweigerd as err:
            return {"base": _geweigerd(err)}, [], None
        except TomTomFout:
            return {"base": "tomtom_fout"}, [], None
    if fouten:
        return fouten, [], None

    try:
        data, _ = await vraag(
            sessie, route_url(sleutel, [(p.lat, p.lon) for p in punten]),
            sleutel=sleutel, agent=AGENT,
        )
    except GeenRoute:
        return {"base": "geen_route"}, punten, None
    except TomTomGeweigerd as err:
        return {"base": _geweigerd(err)}, [], None
    except TomTomFout:
        return {"base": "tomtom_fout"}, [], None
    routes = lees_routes(data)
    if not routes:
        return {"base": "geen_route"}, punten, None
    return {}, punten, int(round(routes[0]["reistijd_s"] / 60))


def _puntenlijst(punten: list[Any]) -> str:
    """Voor de bevestiging: wat je typte en wat er gevonden is."""
    regels = []
    for i, p in enumerate(punten):
        rol = "Start" if i == 0 else ("Bestemming" if i == len(punten) - 1 else f"Stop {i}")
        if p.soort == "adres":
            regels.append(f"- **{rol}**: {p.invoer} → {p.gevonden}")
        else:
            regels.append(f"- **{rol}**: {p.gevonden}")
    return "\n".join(regels)


class CommuteTimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Toevoegen via Instellingen → Apparaten & Services, één keer per route."""

    VERSION = 1

    def __init__(self) -> None:
        self._invoer: dict[str, Any] = {}
        self._punten: list[Any] = []
        self._reistijd: int | None = None

    def _eerdere_sleutel(self) -> str:
        """De sleutel van een route die er al is; één sleutel is genoeg."""
        for entry in self._async_current_entries():
            sleutel = (entry.options or {}).get(CONF_API_KEY)
            if sleutel:
                return str(sleutel)
        return ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fouten: dict[str, str] = {}
        if user_input is not None:
            fouten, punten, reistijd = await controleer_route(self.hass, user_input)
            if not str(user_input.get(CONF_NAME, "")).strip():
                fouten[CONF_NAME] = "naam_leeg"
            if not fouten:
                self._invoer, self._punten, self._reistijd = dict(user_input), punten, reistijd
                return await self.async_step_bevestig()

        huidig = dict(user_input or {})
        huidig.setdefault(CONF_API_KEY, self._eerdere_sleutel())
        return self.async_show_form(
            step_id="user", data_schema=_routeschema(huidig, met_naam=True), errors=fouten
        )

    async def async_step_bevestig(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            opties: dict[str, Any] = {**OPTION_DEFAULTS, **DEFAULT_SCHEDULE}
            for veld in ROUTEVELDEN:
                opties[veld] = str(self._invoer.get(veld) or "").strip()
            return self.async_create_entry(
                title=str(self._invoer[CONF_NAME]).strip(), data={}, options=opties
            )
        return self.async_show_form(
            step_id="bevestig",
            data_schema=vol.Schema({}),
            description_placeholders={
                "punten": _puntenlijst(self._punten),
                "reistijd": str(self._reistijd if self._reistijd is not None else "?"),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> CommuteTimeOptionsFlow:
        """Het optiescherm achter de knop Configureren."""
        return CommuteTimeOptionsFlow()


class CommuteTimeOptionsFlow(OptionsFlow):
    """De route en het rooster aanpassen."""

    def __init__(self) -> None:
        self._nieuw: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        opgeslagen = dict(self.config_entry.options)
        huidig = {**lees_opties(opgeslagen), **{v: opgeslagen.get(v, "") for v in ROUTEVELDEN}}
        fouten: dict[str, str] = {}
        if user_input is not None:
            gewijzigd = any(
                str(user_input.get(v) or "").strip() != str(huidig.get(v) or "").strip()
                for v in ROUTEVELDEN
            )
            # alleen opnieuw opzoeken als er aan de route iets veranderd is;
            # het rooster bijstellen hoort geen verzoeken bij TomTom te kosten
            if gewijzigd:
                fouten, _, _ = await controleer_route(self.hass, user_input)
            if not fouten:
                self._nieuw = {**user_input, CONF_VIA: str(user_input.get(CONF_VIA) or "")}
                return await self.async_step_rooster()
            huidig.update(user_input)
        return self.async_show_form(step_id="init", data_schema=_optieschema(huidig), errors=fouten)

    async def async_step_rooster(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        opgeslagen = dict(self.config_entry.options)
        rooster = lees_opties(opgeslagen)["rooster"]
        fouten: dict[str, str] = {}
        plaats: dict[str, str] = {"dag": ""}
        if user_input is not None:
            rooster = _lees_rooster(user_input)
            problemen = fouten_in_rooster(rooster)
            if not problemen:
                return self.async_create_entry(
                    title="", data={**opgeslagen, **self._nieuw, **rooster}
                )
            dag, soort = next(iter(problemen.items()))
            fouten["base"] = soort
            plaats["dag"] = DAGNAMEN[DAGEN.index(dag)]
        return self.async_show_form(
            step_id="rooster",
            data_schema=_roosterschema(rooster),
            errors=fouten,
            description_placeholders=plaats,
        )
