# CLAUDE.md — Time to Leave

Context voor Claude Code. Lees dit vóór je iets wijzigt.

## Wat dit is

Home Assistant custom component die per route de reistijd, de wegen, de
files en de vertrektijd voor een gewenste aankomsttijd laat zien, met een
eigen Lovelace-kaart. Bron: TomTom (Routing API + Search API, gratis
sleutel).

- Domein: `time_to_leave`
- Entiteiten per route: `sensor.<route>_reistijd` (minuten, met alle
  attributen voor de kaart) en `sensor.<route>_vertrektijd` (tijdstip)
- Kaart: `custom:time-to-leave-card`
- Eén config entry per route; alles staat in `ConfigEntry.options`

## Werkafspraken

Dezelfde als in cycling-next-race en Stars:

- **Alle communicatie en codecommentaar in het Nederlands.**
- **Nooit data verzinnen.** Ontbreekt een bron, laat het veld leeg en laat
  de kaart het weglaten. Geen geschatte vertrektijd als TomTom er geen gaf,
  geen geraden weg bij een file, geen reistijd van een vorig venster.
- **Benoem onzekerheid expliciet.** De README heeft "Hoe nauwkeurig is
  het?" en "Wat niet getest is"; wat je aan de rekenkant verandert hoort
  daar terug te komen.
- **Elke wijziging aan de integratie hoogt het versienummer op**, in
  dezelfde commit, op drie plekken die gelijk blijven: `version` in
  `manifest.json`, `VERSION` in `const.py` en `VERSIE` bovenin de kaart.
  `tests/test_kaart.py` en de CI bewaken dat. Patch bij een reparatie,
  minor bij iets nieuws. Alleen README, CLAUDE.md of tests: niet nodig.
- **Het nieuwe versienummer staat vooraan in het commitbericht**, als
  `v0.1.1 — korte omschrijving`, alleen op commits die het ophogen.
- **Uitbrengen gaat met een versienummer, nooit met een commit-hash**: tag
  `vX.Y.Z`; `.github/workflows/release.yml` maakt de release en weigert
  een tag die niet met de drie versies overeenkomt.
- Degradeer netjes: een fout van TomTom wordt een `status: "fout"` met een
  leesbare `fout`-tekst in de attributen, nooit een uitzondering naar
  boven. Op een telefoon is er geen logboek.

## Waarom TomTom en niet Waze

De eigenaar vroeg om Waze. Op 16 november 2026 uitgezocht:

| | bevinding |
|---|---|
| officiële API | geen. HA's eigen `waze_travel_time` gebruikt `pywaze` (onofficieel) |
| blokkade | sinds september 2026 een 403 op scripts; gemeld op HA 2026.9.4 |
| omzeiling | `pywaze` 1.2.3 (HA 2026.10+) gebruikt `curl_cffi` met `impersonate="chrome"` — nagekeken in de wheels van 1.2.0, 1.2.3 en 1.2.4 |
| voorwaarden | sinds 1 augustus 2026: *"use automated means to access Content"* en *"circumvent … security or protection measures"* verboden (support.google.com/waze/answer/12373727) |
| robots.txt | `www.waze.com` sluit `/RoutingManager`, `/row-RoutingManager`, `/live-map/api` uit voor `*`. `pywaze` gebruikt `routing-livemap-row.waze.com`, dat ons een 403 gaf |

Dat is het CyclingFlash-geval uit cycling-next-race: een toegangsregel van
de beheerder omzeilen. De eigenaar koos daarop: "Een andere goede bron dan
waze mag ook." **Kom hier niet op terug met een "slimme" Waze-route**
zonder dat Waze een officiële API biedt.

Wat wél mag en gebruikt wordt: de **Waze Deep Link**
(`https://waze.com/ul?ll=…&navigate=yes`), gedocumenteerd op
developers.google.com/waze/deeplinks. Dat is een link waar de gebruiker
op tikt; er wordt niets bij Waze opgevraagd. Zie `waze.py`.

## Architectuur

```
custom_components/time_to_leave/
  const.py        sleutels, standaardwaarden, grenzen
  tomtom.py       verzoeken bouwen en antwoorden lezen; geen HA
  rooster.py      venster per weekdag en het oordeel; geen HA
  uitvoer.py      van rekenwerk naar attributen (het contract met de kaart); geen HA
  adressen.py     tekst → punt: entiteit, coördinaat of TomTom-geocode
  waze.py         de deeplink; geen HA
  coordinator.py  één route, alleen binnen het venster; terugschakelen bij 403/429
  sensor.py       reistijd + vertrektijd
  config_flow.py  toevoegen (+ bevestigen wat TomTom vond) en het optiescherm
  __init__.py     opzetten, en de kaart registreren
  www/time-to-leave-card.js
```

- **De sensor rekent, de kaart toont.** De kaart telt alleen "over 18 min"
  zelf af vanaf `vertrek`; verder leest hij wat de sensor zet.
- Per ronde één verzoek (vertrek nu: reistijd, wegen, files, alternatieven)
  en, als er vandaag een aankomsttijd is die nog niet voorbij is, een
  tweede met `arriveAt` = aankomsttijd min marge. Die geeft de
  vertrektijd.
- Buiten het venster: geen verzoek, `update_interval` tot het volgende
  venster (hooguit `MAX_SLAAP_MINUTEN`, plus vijf seconden speling omdat
  HA de volgende ronde op hele seconden afkapt).
- Een instelling toevoegen raakt: `const.py` (`CONF_*`, `DEFAULT_*`,
  `OPTION_DEFAULTS`, grenzen), het schema in `config_flow.py`,
  `lees_opties` in `coordinator.py`, `strings.json` plus elke vertaling, en
  de tabel in de README. `tests/test_repo.py` faalt als er één achterblijft.
- Een kaartoptie toevoegen raakt: `normaliseer`, `VELDEN`, het
  terugvalformulier in de editor, de optietabel in de README.
  `tests/test_kaart.py` faalt als er één achterblijft.
- Een attribuut toevoegen: in `uitvoer.py`, daarna bewust
  `python3 tests/maak_sensor_fixture.py`. De kaart leest attributen altijd
  als `a.<naam>`; zo controleert `test_kaart.py` dat hij niets leest wat
  de sensor niet zet.

## Valkuilen die al tijd hebben gekost

**Rekenen met tijden gaat via UTC.** Python rekent het verschil tussen twee
tijdstippen met hetzelfde tijdzone-object uit op de wandklok, en optellen
en vergelijken ook. Een rit van 02:50 met een half uur rijden kwam in de
wisselnacht van oktober op 03:20 uit in plaats van 02:20. Gebruik
`rooster.plus`, `rooster.seconden_tussen` en `rooster._u`; nooit `a - b`
of `nu + timedelta` op twee lokale tijden. De test
`test_een_aankomst_over_de_wisselnacht_klopt_op_de_klok` vangt het.

**Een `+` in de aankomsttijd moet `%2B` worden.** `arriveAt=…+01:00` met een
kale `+` leest de server als spatie. Daarom bouwt `route_url` de query zelf
met `urlencode` en geeft `vraag` hem met `encoded=True` door aan yarl.

**Vertaalsleutels zijn kleine letters.** Hassfest weigert `tollRoads` als
optie van een keuzelijst. Intern heet het `toll_roads`;
`tomtom.VERMIJD_TOMTOM` vertaalt pas bij het verzoek.

**TomTom noemt tijden in de zone van de bestemming.** `beoordeel` zet de
vertrektijd eerst om naar de zone van Home Assistant; anders staat een rit
naar Engeland een uur verkeerd op de kaart.

**`ha-form` houdt zijn eigen data bij.** Bij elke `setConfig` van de editor
`this._form.data = this._config`, anders slaat de volgende klik oude
waarden op (zie cycling-next-race).

**`set hass` mag nooit gooien** (zie Skywatch): Home Assistant vervangt de
kaart dan door een grijze foutkaart zonder `hass`, tot de pagina herlaadt.
De setter, `setConfig`, de tikker en `disconnectedCallback` vangen alles;
`_fail` zet een leesbare melding met versie in de kaart.

**De sleutel staat in het adres.** Een foutmelding van aiohttp kan het hele
adres bevatten; `zonder_sleutel` haalt hem eruit vóór het in een log of een
attribuut belandt.

**Een waarschuwingskleur nooit als tekstkleur** (zie Skywatch): de stip en
de rand dragen de kleur, de tekst blijft `--primary-text-color`.

## Bronnen

| wat | adres | nagekeken |
|---|---|---|
| route | `api.tomtom.com/routing/1/calculateRoute/{punten}/json` | documentatie, 16-11-2026 |
| adres | `api.tomtom.com/search/2/geocode/{adres}.json` | documentatie, 16-11-2026 |
| Waze openen | `waze.com/ul?ll=…&navigate=yes` | developers.google.com/waze/deeplinks, 16-11-2026 |

**Wat níét nagekeken is:**

- **Een echt antwoord.** De fixtures zijn de voorbeelden uit TomTom's
  documentatie, minimaal hersteld tot geldige JSON (zie
  `tests/fixtures/README.md`). Met een sleutel: echte antwoorden opslaan,
  bij voorkeur in de spits, en de tests erop laten draaien.
- **Of `arriveAt` live verkeer meeweegt** voor een moment in de toekomst,
  of alleen historisch. De documentatie zegt "all available traffic
  information" en niet meer.
- **Of `maxAlternatives` mag bij tussenstops.** `_routes_nu` probeert het en
  valt bij een 400 eenmalig terug op nul.
- **TomTom's voorwaarden** (docs.tomtom.com/legal) staan achter een inlog.
  Daarom de voorzichtigste lezing: geocodes niet op schijf, in het geheugen
  tot middernacht of korter als `Cache-Control` dat zegt (`adressen.py`).
- **Het gratis kwotum**: 2.500 verzoeken per dag volgens de prijspagina;
  niet nagegaan of dat per dienst of samen geldt.
- **`api.tomtom.com/robots.txt`** geeft een 404; er is geen bestand. Het is
  een API met sleutel, bedoeld voor dit gebruik.

## Testen

```
python3 -m pytest tests -q
node --test tests/kaart.test.mjs
npm install --no-save --silent acorn@8
node tests/floor.mjs custom_components/time_to_leave/www/time-to-leave-card.js
python3 -m compileall -q custom_components/time_to_leave
```

- `tests/floor.mjs` is overgenomen uit Skywatch: de hele Chrome 61-grens
  (parse, syntax, ingebouwde functies, CSS) uit de syntaxboom.
- De kaart is op 16 november 2026 in Chromium getekend tegen
  `sensor.json`, in alle drie de vormgevingen; daaruit kwam dat de
  Waze-knop naast de reistijd de vertrektijd afkapte. Niet in Home
  Assistant zelf.
- **Toets tegen wat je onafhankelijk weet** (de klok, de zomertijd, wat in
  de documentatie staat), niet tegen wat deze code zelf oplevert.

## Openstaande punten

- Echte TomTom-antwoorden als fixture (zie boven).
- De config flow en de secties per weekdag zijn niet in een draaiende Home
  Assistant gezien.
- Eén sleutel per route: wie de sleutel wijzigt, moet dat per route doen.
  Config subentries (een account met routes eronder) zouden dat oplossen,
  maar dat is meer HA-oppervlak dat hier niet te testen is.
- Een route op een andere dag vanaf een ander adres is een tweede route met
  een eigen rooster; een startadres per weekdag bestaat niet.
- De verkeersvoorspelling bij een vertrek over een uur of meer: zie
  "Wat níét nagekeken is".
