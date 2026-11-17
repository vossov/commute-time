"""Controles op de repo-bestanden die hassfest en HACS in CI valideren, en
op de vier plekken die een instelling raakt.

Deze draaien zonder netwerk en vangen fouten af die anders pas in GitHub
Actions zichtbaar worden — of helemaal niet, zoals een optie zonder label.
"""
import json
import re
from pathlib import Path

WORTEL = Path(__file__).parent.parent
COMPONENT = WORTEL / "custom_components" / "time_to_leave"
MANIFEST = COMPONENT / "manifest.json"
HACS_JSON = WORTEL / "hacs.json"
STRINGS = COMPONENT / "strings.json"
VERTALINGEN = COMPONENT / "translations"
FLOW = COMPONENT / "config_flow.py"


def _laad(pad):
    return json.loads(pad.read_text(encoding="utf-8"))


# ── manifest.json ───────────────────────────────────────────────────

def test_manifest_sleutels_zijn_gesorteerd():
    """Hassfest eist: domain, name, daarna alfabetisch."""
    sleutels = list(_laad(MANIFEST))
    assert sleutels[:2] == ["domain", "name"]
    assert sleutels[2:] == sorted(sleutels[2:]), f"niet alfabetisch: {sleutels[2:]}"


def test_manifest_heeft_wat_hacs_vereist(const):
    m = _laad(MANIFEST)
    for sleutel in ("codeowners", "documentation", "domain", "issue_tracker", "name", "version"):
        assert sleutel in m, f"manifest mist {sleutel}"
    assert m["domain"] == const.DOMAIN == COMPONENT.name
    assert m["requirements"] == [], "TomTom gaat over aiohttp; er hoort geen pakket bij"


def test_de_kaart_kan_worden_geserveerd():
    m = _laad(MANIFEST)
    for nodig in ("frontend", "http"):
        assert nodig in m.get("dependencies", []), f"dependencies mist {nodig}"


def test_de_kaart_wordt_vroeg_en_met_cache_aangemeld():
    """De twee dingen die "Configuratiefout" op de kaart voorkomen; zie Stars."""
    bron = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "async def async_setup(" in bron
    assert "StaticPathConfig(KAART_URL, str(pad), True)" in bron
    assert 'f"{KAART_URL}?v={VERSION}"' in bron


def test_de_eerste_ronde_houdt_het_opzetten_niet_tegen():
    """`async_config_entry_first_refresh` gooit bij een mislukte eerste
    ronde, en dan staat er een entiteit met `restored: true` zonder reden.
    Zie cycling-next-race."""
    bron = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    code = "\n".join(r for r in bron.splitlines() if not r.strip().startswith("#"))
    assert "async_refresh()" in code
    assert "first_refresh" not in code


def test_de_readme_noemt_precies_de_tomtom_diensten_die_de_code_gebruikt():
    """Minimale rechten: de README zegt welke producten de sleutel nodig
    heeft. Gebruikt de code er een bij, dan moet die tabel mee — anders
    zet iemand netjes alleen de genoemde producten aan en krijgt hij een
    403 op het nieuwe."""
    bron = (COMPONENT / "tomtom.py").read_text(encoding="utf-8")
    in_code = set(re.findall(r'"https://(api\.tomtom\.com/[a-z]+/\d+/[a-zA-Z]+)', bron))
    readme = (WORTEL / "README.md").read_text(encoding="utf-8")
    sectie = readme.split("### Een TomTom-sleutel", 1)[1].split("\n## ", 1)[0]
    in_readme = set(re.findall(r"`(api\.tomtom\.com/[a-z]+/\d+/[a-zA-Z]+)`", sectie))
    assert in_code, "geen TomTom-adressen gevonden in tomtom.py; is de schrijfwijze veranderd?"
    assert in_code == in_readme, f"README en code verschillen: {in_code ^ in_readme}"


# ── hacs.json ───────────────────────────────────────────────────────

HACS_TOEGESTAAN = {
    "content_in_root", "country", "filename", "hacs", "hide_default_branch",
    "homeassistant", "name", "persistent_directory", "render_readme", "zip_release",
}


def test_hacs_json_is_geldig():
    h = _laad(HACS_JSON)
    assert "name" in h
    assert not set(h) - HACS_TOEGESTAAN, f"onbekende sleutels: {set(h) - HACS_TOEGESTAAN}"


# ── vertalingen ─────────────────────────────────────────────────────

def _sleutelboom(obj, pad=""):
    if not isinstance(obj, dict):
        return {pad}
    uit = set()
    for k, v in obj.items():
        uit |= _sleutelboom(v, f"{pad}.{k}" if pad else k)
    return uit


def test_vertalingen_dekken_dezelfde_sleutels():
    verwacht = _sleutelboom(_laad(STRINGS))
    assert (VERTALINGEN / "en.json").exists(), "en.json is verplicht"
    for pad in sorted(VERTALINGEN.glob("*.json")):
        assert _sleutelboom(_laad(pad)) == verwacht, f"{pad.name} wijkt af van strings.json"


def test_nl_is_strings():
    """strings.json is Nederlands, zoals bij Stars; nl.json is er een kopie van."""
    assert _laad(VERTALINGEN / "nl.json") == _laad(STRINGS)


def test_vertaalsleutels_zijn_kleine_letters():
    """Hassfest weigert een vertaalsleutel met hoofdletters, ook als optie
    van een keuzelijst. Daarom heet het hier `toll_roads` en niet zoals bij
    TomTom `tollRoads`."""
    s = _laad(STRINGS)
    for keuzelijst in s["selector"].values():
        for sleutel in keuzelijst["options"]:
            assert re.fullmatch(r"[a-z0-9_-]+", sleutel), sleutel
    for soort in ("config", "options"):
        for sleutel in s[soort]["error"]:
            assert re.fullmatch(r"[a-z0-9_-]+", sleutel), sleutel


# ── de vier plekken van een instelling ──────────────────────────────

def test_elke_optie_heeft_een_standaard_een_label_en_een_veld(const):
    """Een optie raakt const.py, het schema in config_flow.py en strings.json
    plus elke vertaling. Blijft er één achter, dan is hij niet in te stellen
    of staat er een kale sleutel in het scherm."""
    labels = set(_laad(STRINGS)["options"]["step"]["init"]["data"])
    assert set(const.OPTION_DEFAULTS) == labels, f"verschil: {set(const.OPTION_DEFAULTS) ^ labels}"
    bron = FLOW.read_text(encoding="utf-8")
    for naam, waarde in vars(const).items():
        if naam.startswith("CONF_") and waarde in const.OPTION_DEFAULTS:
            assert naam in bron, f"{naam} ontbreekt in config_flow.py"


def test_het_toevoegscherm_heeft_een_label_voor_elk_veld(const):
    labels = set(_laad(STRINGS)["config"]["step"]["user"]["data"])
    verwacht = {const.CONF_NAME, const.CONF_API_KEY, const.CONF_START, const.CONF_VIA, const.CONF_DESTINATION}
    assert labels == verwacht


def test_elke_dag_heeft_een_sectie_met_drie_velden(const):
    secties = _laad(STRINGS)["options"]["step"]["rooster"]["sections"]
    assert set(secties) == set(const.DAGEN)
    for dag, sectie in secties.items():
        assert set(sectie["data"]) == set(const.DAGVELDEN), dag


def test_elke_fout_uit_de_code_heeft_een_tekst():
    """Een foutcode zonder vertaling toont een kale sleutel in het scherm."""
    bron = FLOW.read_text(encoding="utf-8") + (COMPONENT / "rooster.py").read_text(encoding="utf-8")
    # alleen waar de code echt een fout toekent: fouten[x] = "…" of {"base": "…"}
    codes = set(re.findall(r'(?:fouten\[\w+\]\s*=|\{\s*(?:"base"|CONF_\w+)\s*:)\s*"([a-z_]+)"', bron))
    # de geweigerde sleutel wordt per dienst gekozen, uit een opzoektabel
    codes |= set(re.findall(r'"(sleutel_geweigerd\w*)"', bron))
    s = _laad(STRINGS)
    bekend = set(s["config"]["error"]) | set(s["options"]["error"])
    assert codes, "geen foutcodes gevonden; is de schrijfwijze veranderd?"
    assert not codes - bekend, f"zonder tekst: {codes - bekend}"


def test_de_standaardwaarden_liggen_binnen_de_grenzen(const):
    grenzen = {
        const.CONF_MARGIN_MINUTES: (const.MIN_MARGIN_MINUTES, const.MAX_MARGIN_MINUTES),
        const.CONF_STOP_MINUTES: (const.MIN_STOP_MINUTES, const.MAX_STOP_MINUTES),
        const.CONF_ALTERNATIVES: (const.MIN_ALTERNATIVES, const.MAX_ALTERNATIVES),
        const.CONF_SCAN_MINUTES: (const.MIN_SCAN_MINUTES, const.MAX_SCAN_MINUTES),
    }
    for sleutel, (laag, hoog) in grenzen.items():
        assert laag <= const.OPTION_DEFAULTS[sleutel] <= hoog, sleutel


def test_onzin_in_de_opslag_valt_terug_op_de_standaard(coordinator_mod, const):
    """Een kapotte opslag mag de route niet omver halen."""
    o = coordinator_mod.lees_opties({
        const.CONF_SCAN_MINUTES: "geen getal",
        const.CONF_MARGIN_MINUTES: 999,
        const.CONF_ALTERNATIVES: 2.0,  # zo komt een getal uit het scherm
        const.CONF_TRAVEL_MODE: "raket",
        const.CONF_AVOID: ["toll_roads", "kuilen"],
        "monday": "geen dict",
    })
    assert o[const.CONF_SCAN_MINUTES] == const.DEFAULT_SCAN_MINUTES
    assert o[const.CONF_MARGIN_MINUTES] == const.DEFAULT_MARGIN_MINUTES
    assert o[const.CONF_ALTERNATIVES] == 2
    assert o[const.CONF_TRAVEL_MODE] == const.DEFAULT_TRAVEL_MODE
    assert o[const.CONF_AVOID] == ["toll_roads"]
    assert o["rooster"] == const.DEFAULT_SCHEDULE


def test_het_schema_laat_zich_bouwen(flow_mod, coordinator_mod):
    """Met gestubde HA-modules: zegt alleen dat de schema's opgebouwd kunnen
    worden, niet dat het scherm er in Home Assistant goed uitziet."""
    huidig = {**coordinator_mod.lees_opties({}), "api_key": "", "start": "zone.home", "destination": "", "via": ""}
    assert flow_mod._optieschema(huidig)
    assert flow_mod._roosterschema(huidig["rooster"])
    assert flow_mod._routeschema({}, met_naam=True)


def test_een_gewist_veld_in_het_rooster_wordt_none(flow_mod, const):
    uit = flow_mod._lees_rooster({"monday": {"show_from": "07:00:00", "show_until": "09:00:00"}})
    assert uit["monday"] == {"show_from": "07:00:00", "show_until": "09:00:00", "arrive_at": None}
    assert set(uit) == set(const.DAGEN)
