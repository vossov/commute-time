# CLAUDE.md — Commute Time

Context voor Claude Code. Lees dit vóór je iets wijzigt.

## Wat dit is

Home Assistant custom component die per route de reistijd, de wegen, de
files en de vertrektijd voor een gewenste aankomsttijd laat zien, met een
eigen Lovelace-kaart. Bron: TomTom (Routing API + Search API, gratis
sleutel).

- Domein: `commute_time` (tot v0.2.1: `time_to_leave`, zie "De naam")
- Entiteiten per route: `sensor.<route>_reistijd` (minuten, met alle
  attributen voor de kaart) en `sensor.<route>_vertrektijd` (tijdstip)
- Kaart: `custom:commute-time-card`
- Eén config entry per route; alles staat in `ConfigEntry.options`

## Werkafspraken

Dezelfde als in cycling-next-race en Stars:

- **Communicatie met de eigenaar, codecommentaar, CLAUDE.md en de
  ontwikkelaarsdocs (tests/, tools/) in het Nederlands. Alles wat een
  gebruiker leest in het Engels**: README, `docs/`, CHANGELOG (dus de
  release-notes) en `strings.json`. De kaart spreekt Engels (standaard) of
  Nederlands, via de kaartoptie `language`. Besloten door de eigenaar op 24
  november 2026: "De documentatie moet eigenlijk in het engels, op de kaart
  kan je dan nog kiezen voor en of nl. Maar en moet de standaard zijn."
- **Nooit data verzinnen.** Ontbreekt een bron, laat het veld leeg en laat
  de kaart het weglaten. Geen geschatte vertrektijd als TomTom er geen gaf,
  geen geraden weg bij een file, geen reistijd van een vorig venster.
- **Benoem onzekerheid expliciet.** `docs/reliability.md` heeft "How
  accurate is it?" en "What has not been tested"; wat je aan de rekenkant
  verandert hoort daar terug te komen.
- **Elke wijziging aan de integratie hoogt het versienummer op**, in
  dezelfde commit, op drie plekken die gelijk blijven: `version` in
  `manifest.json`, `VERSION` in `const.py` en `VERSIE` bovenin de kaart.
  `tests/test_kaart.py` en de CI bewaken dat. Patch bij een reparatie,
  minor bij iets nieuws. Alleen README, CLAUDE.md of tests: niet nodig.
- **Het nieuwe versienummer staat vooraan in het commitbericht**, als
  `v0.1.1 — korte omschrijving`, alleen op commits die het ophogen.
- **Uitbrengen gaat vanzelf, met een versienummer en notes, nooit met een
  commit-hash.** Zonder GitHub-release toont HACS "10f32a5" in plaats van
  "v0.2.1" en geen release-notes (zo stond het op 18 november 2026, omdat de
  tag-push vanuit de sandbox een 403 gaf). De stappen, alle drie in dezelfde
  push: (1) de versie ophogen op de drie plekken; (2) bovenaan `CHANGELOG.md`
  een sectie voor die versie; (3) naar `main` pushen. Dan maakt
  `.github/workflows/release.yml` zelf de tag en de release, met titel en
  notes uit de changelog (`tools/release_notes.py`). **Push geen tags**; dat
  hoeft niet en lukt hier niet. De workflow draait eerst de tests, de
  Chrome 61-grens en hassfest, en faalt als de drie versies verschillen of de
  changelog-sectie ontbreekt. `tests/test_release.py` faalt in de gewone CI
  als de versie in de manifest geen netjes ingevulde sectie heeft. Bestaat de
  release al, dan trekt dezelfde workflow de notes gelijk met de changelog:
  een tikfout herstel je in `CHANGELOG.md` van de huidige versie en push je;
  de releasepagina hoef je niet te bewerken (en kan hier ook niet).
- **Schrijf de changelog voor de gebruiker**, in gewone Engelse taal: wat
  verandert er voor hem, niet welke functie je aanpaste. Kopjes: `Added`,
  `Improved`, `Fixed`, `Heads-up` (`tools/release_notes.py` kent alleen die).
  Heeft een eerdere versie iets onjuists beweerd, zet dat er dan bij onder
  "Heads-up" (zie 0.1.2). Alleen
  README, docs of tests aangepast: geen nieuwe versie en geen nieuwe sectie.
- **Een afgeronde wijziging mag meteen live.** Staande toestemming van de
  eigenaar, 17 november 2026, op de vraag "rechtstreeks naar main en taggen,
  zonder pull request?": "ja". Dezelfde werkwijze als in cycling-next-race:
  naar `main` pushen hoort bij het werk afmaken (de release volgt dan vanzelf,
  zie hierboven), en een wijziging die op een branch blijft staan draait
  nergens. Vraag alleen als de wijziging zelf
  onzeker is (niet getest, een gok). De CI draait hier ná de push, dus kijk
  na elke push of alles groen is, vooral hassfest: dat draait de
  release-workflow zelf niet. HACS faalt zolang de repo geen beschrijving en
  topics heeft; dat stel je in op GitHub en is geen codefout.
- Degradeer netjes: een fout van TomTom wordt een `status: "fout"` met een
  leesbare `fout`-tekst in de attributen, nooit een uitzondering naar
  boven. Op een telefoon is er geen logboek.

## De naam

Tot v0.2.1 heette dit **Time to Leave** (`time_to_leave`,
`vossov/time-to-leave`). Op 24 november 2026 hernoemd naar **Commute Time**
(`commute_time`, `custom:commute-time-card`, `vossov/commute-time`), op
verzoek van de eigenaar. Overwogen en afgevallen:

| naam | waarom niet |
|---|---|
| Time to Leave | al in gebruik door thamara/time-to-leave, een bekende app die werkuren bijhoudt (timetoleave.app) |
| Travel Time | `custom:travel-time-card` bestaat al (ljmerza); twee kaarten met dezelfde elementnaam laden niet. TravelTime is ook een bedrijf met een reistijd-API |
| TomTom/Google/Waze Travel Time | de eigenaar wil geen bron of merk in de naam |
| Wayfinder, On Time | bestaan al als HA-project |

Bij twee zoekopdrachten (forum, GitHub) vonden we geen Home Assistant-project
dat Commute Time heet. In HACS zelf is dat niet nagekeken.
**Kom niet terug op de naam** zonder dat de eigenaar erom vraagt. Een nieuw
domein betekent dat iedereen zijn routes opnieuw moet toevoegen (zie
CHANGELOG 0.3.0); dat doe je niet voor een iets mooiere naam.

Oude vermeldingen van Time to Leave in de CHANGELOG blijven staan; dat is
geschiedenis.

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
custom_components/commute_time/
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
  www/commute-time-card.js
```

Daaromheen, in de root van de repo:

```
CHANGELOG.md                  wat er per versie veranderd is; bron van de release-notes
docs/                         de lange uitleg die de README kort houdt; docs/img: de afbeeldingen
tools/release_notes.py        titel en notes van een versie uit CHANGELOG.md; geen afhankelijkheden
tools/maak_afbeeldingen.cjs   tekent docs/img/*.png met de echte kaart (Playwright)
.github/workflows/            validate.yml (CI) en release.yml (maakt de release zelf)
```

- **De sensor rekent, de kaart toont.** De kaart zegt alleen zelf "nu" zodra
  `vertrek` voorbij is; verder leest hij wat de sensor zet.
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
  terugvalformulier in de editor, de optietabel in de README, en `l_<naam>`
  en `u_<naam>` in `TEKST` voor beide talen. `tests/test_kaart.py` en
  `tests/kaart.test.mjs` falen als er één achterblijft.
- **Tekst op de kaart staat alleen in `TEKST`** (`en` en `nl`), en komt er
  via `t(taal, sleutel, waarden)` uit. Beide talen hebben dezelfde sleutels
  en dezelfde `{invulplekken}`; `kaart.test.mjs` bewaakt dat en zoekt
  Nederlandse woorden op de Engelse kaart.
- **Wat de sensor als tekst zet, is Nederlands** (`fout`,
  `volgend_venster_tekst`, `files[].soort`) en blijft staan voor wie het in
  een automatisering gebruikt. De kaart leest de taalloze velden ernaast:
  `fout_code` + `fout_param` (codes in `tomtom.FOUTCODES`; elke code heeft
  een zin in `TEKST` als `fout_<code>`), `volgend_venster_hhmm/_dagen/_weekdag`
  en `files[].categorie` (TomTom's `simpleCategory`). Een nieuwe foutcode
  raakt: de `raise`, `FOUTCODES` en `TEKST`; `test_tomtom.py` en
  `kaart.test.mjs` falen anders. Zonder code toont de kaart `fout` zoals hij
  is (een oudere integratie).
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

## De kaart

- **Hoofdgetal** (`weergave()`): met een aankomsttijd de vertrektijd
  ("Vertrek 07:52", of "Vertrek nu"), zonder aankomsttijd de rijtijd ("34
  min"). Geen aftelling "over x min": de eigenaar wilde dat niet (18
  november 2026).
- **De ingevoerde aankomsttijd en marge staan er niet**, tenzij de
  kaartoptie `target` aan staat (standaard uit), op de tegel én in het
  venster. De aankomst "als je nu vertrekt" is iets anders (afgeleid, niet
  ingevoerd) en blijft in het venster staan.
- **De aankomsttijd is optioneel**: per weekdag, standaard leeg. In de
  frontend van Home Assistant (dev, bekeken 18 november 2026) is de
  tijdkiezer `clearable` en blijft een leeggemaakt veld bewust `undefined`;
  `_lees_rooster` maakt er `None` van. Niet in een draaiende Home Assistant
  beproefd.
- **Scheiding in een regel** is een vaste spatie + punt (`PUNT`), zodat een
  omslaande regel de punt bij het woord ervoor laat.

### De Bubble-stijl is nagebouwd naar de bron

De eerste versie (v0.1.0) was uit het hoofd gemaakt en leek er niet op ("ziet
er niet uit als een bubble kaart", 18 november 2026). Daarna is
`dist/bubble-card.js` van github.com/Clooos/Bubble-Card nagelezen (main; de
API-boomlijst gaf een 403, de raw-bestanden niet) en naast de afbeeldingen in
de README gelegd. Wat ertoe doet:

- **De pil is de secundaire achtergrond, het icoonrondje de kaartachtergrond.**
  Pil: `--bubble-main-background-color` → `--background-color-2` →
  `--secondary-background-color`. Rondje en waardepillen:
  `--bubble-icon-background-color` → `--bubble-secondary-background-color` →
  `--card-background-color`. Omgekeerd aan een gewone kaart; met één kleur
  voor beide verdwijnt de pil.
- 50 px hoog, radius 28 px; rondje 38 px met 6 px marge; naam 13 px/600,
  status 12 px op 70%; waarden als sub-knoppen van 36 px, radius 18 px.
- De pop-up is een bladzijde onderaan; achtergrond
  `--bubble-pop-up-main-background-color` → … → `--secondary-background-color`.
- Het icoonrondje krijgt de kleur van de vertraging (glyph in die kleur, het
  rondje op 20%), zoals Bubble Card een actief icoon inkleurt.

**Niet geprobeerd:** met een geïnstalleerd Bubble-thema dat `--bubble-*`
instelt, en in Home Assistant zelf. Dat een thema de kaart volgt is uit de
terugvalketens afgeleid. Gerenderd is in Chromium, donker en licht, met een
eigen `ha-card` (achtergrond op `:host`) en `ha-icon` (shadow root, MDI-paden).
**Pas op bij zo'n testpagina:** zet `display` van `ha-icon` niet inline, want
dan wint dat van `.waze ha-icon { display: none }`; de echte `ha-icon` doet dat
niet. Zet het op `:host`.

## De README en docs

De eigenaar vond de eerste README "niet netjes" (18 november 2026) en wees naar
Bubble Card als voorbeeld van hoe het eruit hoort te zien. Daarom:

- **De README is het visitekaartje en blijft kort**: banner, één zin, badges,
  de HACS-knop, een inhoudsopgave, de stappen, de kaartopties, en
  veelgestelde vragen in `<details>`. De lange uitleg staat in `docs/`
  (`tomtom-key.md`, `why-tomtom.md`, `reliability.md`; tot v0.3.0 Nederlands
  en met Nederlandse namen). Verplaats
  uitleg naar docs in plaats van de README te laten groeien.
- **Alle links en afbeeldingen zijn volledige adressen naar `main`**
  (`https://github.com/vossov/commute-time/blob/main/…`, `raw.githubusercontent.com`).
  Relatieve paden werken in HACS vaak niet. `tests/test_readme.py` controleert
  dat elk adres naar iets wijst dat er is, dat elk `#anker` een kop is, en dat
  elke `##`-kop in de inhoudsopgave staat.
- De kop `### Card options` en de tabel eronder moeten blijven staan:
  `tests/test_kaart.py` vergelijkt hem met de editor. `## Contents` is de
  inhoudsopgave die `tests/test_readme.py` leest.
- **De afbeeldingen zijn geen schermafbeeldingen uit Home Assistant.** Ze zijn
  met `node tools/maak_afbeeldingen.cjs` getekend in Chromium, met de echte
  kaart en voorbeeldgegevens, en de README zegt dat erbij. Hou de voorbeeld-
  getallen onderling kloppend (33 + 8 min vertraging = 41 min, vertrek 07:34
  geeft aankomst 08:15): de eerste versie toonde "nu 41 min, gebruikelijk
  3 min" naast elkaar. Ze tonen de kaart in het Engels, de standaard. Maak ze opnieuw als de kaart er anders uitziet. Echte
  schermafbeeldingen van de eigenaar zijn beter, zodra die er zijn.

## Bronnen

| wat | adres | nagekeken |
|---|---|---|
| route | `api.tomtom.com/routing/1/calculateRoute/{punten}/json` | documentatie, 16-11-2026 |
| adres | `api.tomtom.com/search/2/geocode/{adres}.json` | documentatie, 16-11-2026 |
| Waze openen | `waze.com/ul?ll=…&navigate=yes` | developers.google.com/waze/deeplinks, 16-11-2026 |

**Rechten van de sleutel: het minimum is níét vastgesteld** (de uitleg voor
gebruikers staat in `docs/tomtom-key.md`). Op 16 november 2026 beweerde de README dat alleen de Routing API en de Search API nodig
waren (klassiek, niet Orbis). Bij het eerste echte gebruik, 17 november,
bleken die twee te weinig en zette de eigenaar alle producten aan. Welk
product ontbrak is niet bekend: de productnamen in het portaal staan achter
een inlog en zijn nooit nagekeken. Wel bekend, volgens de eigenaar: de
melding was de algemene weigering (403) van vóór v0.1.2, die nog niet zei
welke dienst weigerde, en dezelfde sleutel werkte nadat alle producten aan
stonden. Dat wijst op een ontbrekend product; of TomTom een nieuwe sleutel
pas na enige tijd activeert, is niet nagegaan. **Beweer geen rechtenlijst van een portaal dat je niet hebt
gezien.** Wat wel staat: een aparte sleutel, geen domeinwhitelist (die werkt
via CORS en de sleutel komt nooit in een browser) en geen betaalgegevens.

Om het minimum alsnog te vinden zegt een geweigerde sleutel nu welke dienst
weigerde (`TomTomGeweigerd.dienst`, `tomtom.dienst_van`; in het scherm
`sleutel_geweigerd_search` en `_routing`) en herhaalt de melding wat TomTom
zelf schrijft, zonder de sleutel. Wie het minimum vaststelt, zet het met
datum in de README.
`test_de_readme_noemt_precies_de_tomtom_diensten_die_de_code_gebruikt`
bewaakt alleen dat de adressen in de README kloppen met de code, niet welke
vinkjes erbij horen.

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
node tests/floor.mjs custom_components/commute_time/www/commute-time-card.js
python3 -m compileall -q custom_components/commute_time
python3 tools/release_notes.py "$(python3 -c "import json;print(json.load(open('custom_components/commute_time/manifest.json'))['version'])")" check
```

De laatste regel vraagt of de huidige versie een nette changelog-sectie heeft;
`tests/test_release.py` doet hetzelfde. De afbeeldingen opnieuw maken kan met
`node tools/maak_afbeeldingen.cjs` (vraagt Playwright; niet in de CI).

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
