"""Laadt de integratie zonder dat Home Assistant geïnstalleerd hoeft te zijn.

De HA-imports worden vervangen door kleine stubs; alle pure functies
(parsers, het rooster, het oordeel, de attributen) zijn daarna gewoon te
testen. Zoals bij Stars: als package geladen, want de modules doen
`from .const import ...`.

De tijdzone staat vast op Europe/Amsterdam. De testmachine draait op UTC,
en een rooster dat op "07:30" staat hoort hier niet van af te hangen.
"""
import importlib
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

COMPONENTS = Path(__file__).parent.parent / "custom_components"
TZ = ZoneInfo("Europe/Amsterdam")


def _stub(naam, **attrs):
    mod = sys.modules.get(naam) or types.ModuleType(naam)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[naam] = mod
    return mod


def _klasse(naam):
    # elke stub een eigen klasse; sensor.py erft van er twee tegelijk
    return type(naam, (), {"__init__": lambda self, *a, **kw: None})


def _installeer_stubs():
    # yarl zit bij aiohttp en dus bij Home Assistant, maar niet in de CI;
    # de nep-sessie in test_coordinator.py krijgt dan gewoon de tekst
    try:
        import yarl  # noqa: F401
    except ImportError:
        _stub("yarl", URL=lambda adres, encoded=False: adres)
    if "aiohttp" not in sys.modules:
        _stub(
            "aiohttp",
            ClientError=type("ClientError", (Exception,), {}),
            ClientSession=_klasse("ClientSession"),
            ClientTimeout=lambda **kw: kw,
        )

    _stub("homeassistant")
    _stub("homeassistant.components")
    _stub(
        "homeassistant.components.sensor",
        SensorEntity=_klasse("SensorEntity"),
        SensorDeviceClass=types.SimpleNamespace(DURATION="duration", TIMESTAMP="timestamp"),
        SensorStateClass=types.SimpleNamespace(MEASUREMENT="measurement"),
    )
    _stub("homeassistant.components.frontend", add_extra_js_url=lambda *a, **kw: None)
    _stub("homeassistant.components.http", StaticPathConfig=_klasse("StaticPathConfig"))

    # ConfigFlow neemt `domain=` mee in de klassedefinitie, vandaar het
    # eigen __init_subclass__; een kale type() weigert dat.
    def _init_subclass(cls, **kwargs):
        return None

    config_flow_stub = type("ConfigFlow", (), {
        "__init__": lambda self, *a, **kw: None,
        "__init_subclass__": classmethod(_init_subclass),
    })
    _stub(
        "homeassistant.config_entries",
        ConfigEntry=_klasse("ConfigEntry"),
        ConfigFlow=config_flow_stub,
        ConfigFlowResult=dict,
        OptionsFlow=_klasse("OptionsFlow"),
    )
    _stub(
        "homeassistant.const",
        Platform=types.SimpleNamespace(SENSOR="sensor"),
        MATCH_ALL="*",
        UnitOfTime=types.SimpleNamespace(MINUTES="min"),
    )
    _stub("homeassistant.core", HomeAssistant=_klasse("HomeAssistant"), callback=lambda f: f)

    def _section(schema, opties=None):
        return ("section", schema, opties)

    _stub("homeassistant.data_entry_flow", section=_section)
    _stub("homeassistant.helpers")

    class _Selector:
        def __init__(self, config=None):
            self.config = config

        def __call__(self, waarde):
            return waarde

    _stub(
        "homeassistant.helpers.selector",
        TextSelector=_Selector,
        TextSelectorConfig=lambda **kw: kw,
        TextSelectorType=types.SimpleNamespace(TEXT="text", PASSWORD="password"),
        TimeSelector=_Selector,
        SelectSelector=_Selector,
        SelectSelectorConfig=lambda **kw: kw,
        SelectSelectorMode=types.SimpleNamespace(DROPDOWN="dropdown", LIST="list"),
        NumberSelector=_Selector,
        NumberSelectorConfig=lambda **kw: kw,
        NumberSelectorMode=types.SimpleNamespace(BOX="box", SLIDER="slider"),
    )
    _stub("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda *a, **kw: None)
    _stub("homeassistant.helpers.location", find_coordinates=lambda hass, naam: None)
    _stub(
        "homeassistant.helpers.device_registry",
        DeviceInfo=dict,
        DeviceEntryType=types.SimpleNamespace(SERVICE="service"),
    )
    _stub("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    # DataUpdateCoordinator[dict[str, Any]]: de echte is generiek
    coordinator_stub = type("DataUpdateCoordinator", (), {
        "__init__": lambda self, *a, **kw: None,
        "__class_getitem__": classmethod(lambda cls, item: cls),
    })
    _stub(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=coordinator_stub,
        CoordinatorEntity=_klasse("CoordinatorEntity"),
        UpdateFailed=type("UpdateFailed", (Exception,), {}),
    )
    _stub("homeassistant.util")
    _stub(
        "homeassistant.util.dt",
        now=lambda: datetime.now(TZ),
        parse_datetime=datetime.fromisoformat,
    )
    sys.modules["homeassistant.util"].dt = sys.modules["homeassistant.util.dt"]


def _laad(naam):
    _installeer_stubs()
    if str(COMPONENTS) not in sys.path:
        sys.path.insert(0, str(COMPONENTS))
    return importlib.import_module(f"time_to_leave.{naam}")


@pytest.fixture(scope="session")
def tz():
    return TZ


@pytest.fixture(scope="session")
def const():
    return _laad("const")


@pytest.fixture(scope="session")
def tomtom():
    return _laad("tomtom")


@pytest.fixture(scope="session")
def rooster():
    return _laad("rooster")


@pytest.fixture(scope="session")
def uitvoer():
    return _laad("uitvoer")


@pytest.fixture(scope="session")
def adressen():
    return _laad("adressen")


@pytest.fixture(scope="session")
def waze():
    return _laad("waze")


@pytest.fixture(scope="session")
def coordinator_mod():
    return _laad("coordinator")


@pytest.fixture(scope="session")
def sensor_mod():
    return _laad("sensor")


@pytest.fixture(scope="session")
def flow_mod():
    """De config-flow-module; vereist voluptuous."""
    pytest.importorskip("voluptuous")
    return _laad("config_flow")
