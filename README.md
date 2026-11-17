# Time to Leave

Home Assistant-integratie die voor je vaste routes laat zien hoe lang je
onderweg bent, welke weg het snelst is, en **hoe laat je weg moet** om op
tijd te zijn. Met een eigen dashboardkaart in drie vormgevingen, waaronder
een Bubble Card-stijl.

- Elke route heeft een eigen **startadres**, eventueel **tussenstops**
  (eerst naar school, dan naar je werk) en een bestemming. Begin en eind
  mogen een adres zijn, een coördinaat, of een entiteit: `zone.home`, of
  `person.naam` om te vertrekken vanaf waar iemand nu is.
- Per weekdag stel je in **wanneer de route in beeld is** en **hoe laat je
  er wilt zijn**. Daaruit volgt de vertrektijd, met een marge die je zelf
  kiest.
- Buiten dat venster wordt er niets opgevraagd en verbergt de kaart de
  route.
- De kaart toont de reistijd, de wegen ("via A12 · A27") en de files.
  Een tik opent de details: andere routes, etappes, en de adressen zoals
  ze gevonden zijn. Een knop opent **Waze** om te gaan rijden.

## Waarom TomTom en niet Waze

De vraag was "via Waze". Dat is onderzocht en bewust niet gedaan:

- Waze heeft **geen openbare routing-API**. Ook de ingebouwde Waze-integratie
  van Home Assistant gebruikt een onofficiële weg (de bibliotheek
  `pywaze`).
- Sinds september 2026 weigert Waze zulke verzoeken met een 403. `pywaze`
  1.2.3, sinds 2026.10 in Home Assistant, doet zich daarom voor als Chrome
  (`curl_cffi`, `impersonate="chrome"`). Dat is in de broncode van het
  pakket nagekeken.
- De [gebruiksvoorwaarden van Waze](https://support.google.com/waze/answer/12373727?hl=en)
  verbieden letterlijk *"use automated means to access Content from the
  Service"* en *"You may not circumvent, modify, or disable any security or
  protection measures."* De
  [aangescherpte versie](https://support.google.com/waze/answer/17300833)
  geldt sinds 1 augustus 2026.
- `www.waze.com/robots.txt` sluit `/RoutingManager`, `/row-RoutingManager`
  en `/live-map/api` uit voor elke bot.

Dat is dezelfde soort omzeiling die in cycling-next-race voor CyclingFlash
is afgewezen. TomTom heeft wél een officiële API, met een gratis sleutel,
en kan zelf terugrekenen vanaf een aankomsttijd.

**Waze blijft wel in beeld voor het rijden zelf.** De knop op de kaart is
een [Waze Deep Link](https://developers.google.com/waze/deeplinks), de
officiële manier om Waze met een bestemming te openen. Er wordt niets bij
Waze opgevraagd; jij tikt op een link.

## Installeren

**Via HACS** (aanbevolen): HACS → ⋮ → *Aangepaste repositories* →
`https://github.com/vossov/time-to-leave`, categorie **Integratie**.
Installeer *Time to Leave* en herstart Home Assistant.

**Met de hand**: kopieer `custom_components/time_to_leave` naar
`config/custom_components/` en herstart.

De kaart hoort bij de integratie en wordt vanzelf geladen. Je hoeft geen
resources toe te voegen, geen button-card en geen Bubble Card.

### Een TomTom-sleutel

De integratie roept precies twee diensten van TomTom aan, allebei in de
klassieke versie (niet de nieuwere Orbis-varianten):

| dienst | adres | waarvoor |
|---|---|---|
| Routing API | `api.tomtom.com/routing/1/calculateRoute` | reistijd met verkeer, wegen, files, en de vertrektijd voor een aankomsttijd |
| Search API | `api.tomtom.com/search/2/geocode` | een ingetypt adres opzoeken. Niet nodig voor `zone.home`, een persoon of een coördinaat |

Zo stel je de sleutel in:

1. **Maak een account** op [developer.tomtom.com](https://developer.tomtom.com),
   in het gratis Freemium-plan.
2. **Maak een aparte sleutel** voor deze integratie. TomTom raadt zelf aan
   om per toepassing een eigen sleutel te gebruiken
   ([best practices](https://docs.tomtom.com/platform/documentation/api-best-practices/api-key-management-best-practices)).
   Lekt hij uit, dan raakt dat alleen dit.
3. **Zet de producten aan die TomTom vraagt, en zoek daarna het minimum.**
   Welke producten dat precies zijn, is **niet vastgesteld**. In de eerste
   proef bleken "Routing API" en "Search API" alleen niet genoeg; die
   sleutel staat nu met alle producten aan. Welk product ontbrak weten we
   niet: de namen in het portaal staan achter een inlog en zijn nooit
   nagekeken. Wat we wel weten: de melding was de algemene weigering van
   TomTom (403), uit een versie die nog niet zei welke dienst weigerde, en
   dezelfde sleutel werkte nadat alle producten aan stonden. Dat wijst op
   een ontbrekend product; of TomTom een nieuwe sleutel pas na enige tijd
   activeert, is niet nagegaan. Een sleutel met alle producten is een grotere schade als hij uitlekt; de
   andere stappen hier beperken dat, maar vervangen het minimum niet.

   Zo vind je het minimum, bij een sleutel waarmee het nu werkt:
   - Zet één product uit.
   - Voeg de integratie opnieuw toe met een **adres** als bestemming (met
     alleen coördinaten of `zone.home` wordt de Search API niet
     geprobeerd) en breek bij de bevestigingsstap af. Er wordt dan niets
     opgeslagen.
   - Weigert TomTom, dan noemt de melding de dienst: *Search API* (adressen
     opzoeken) of *Routing API* (routes berekenen). Dat is de dienst die
     TomTom weigerde, niet de naam van het product dat ontbreekt. Zet het
     product weer aan en probeer het volgende.
4. **Laat de domeinwhitelist leeg.** Die is bedoeld voor een sleutel die in
   een webpagina staat, en werkt via CORS, een controle die de browser
   doet. Hier gaat de sleutel van Home Assistant zelf naar TomTom en komt
   hij nooit in je browser, dus een whitelist beschermt niets. Of TomTom
   met een whitelist verzoeken zonder browser zou weigeren, is niet
   nagegaan.
5. **Voeg geen betaalgegevens toe.** Zonder creditcard kan een uitgelekte
   sleutel geen rekening opleveren; boven het dagkwotum weigert TomTom, en
   dat staat dan op de kaart. Dat volgt uit het plan; het is niet zelf
   uitgeprobeerd.

**Waar de sleutel staat:** in de opslag van Home Assistant
(`.storage/core.config_entries`), onversleuteld, zoals bij elke
integratie. Hij zit daarmee ook in je back-ups. Hij staat níét in de
attributen, niet in de kaart en niet in foutmeldingen in het logboek; daar
zijn tests voor.

**Lekt hij toch uit:** TomTom kan een sleutel vernieuwen (*key rotation*);
de oude werkt dan nog een tijd door. Zet de nieuwe daarna bij elke route
onder *Configureren*. Eén sleutel per route is een bekende beperking.

Het gratis plan geeft 2.500 verzoeken per dag, zonder creditcard. Dat staat
op TomTom's prijspagina; het is niet nagegaan of dat getal per dienst
geldt of voor alle diensten samen.

## Instellen

*Instellingen → Apparaten & Services → Integratie toevoegen → Time to
Leave.* Je voegt **één route per keer** toe; voor een tweede route voeg je
de integratie nog eens toe. De sleutel staat dan al ingevuld.

1. **Route**: naam, sleutel, vertrekpunt, tussenstops (één per regel,
   hoogstens drie) en bestemming.
2. **Bevestigen**: TomTom laat zien welke adressen hij vond, plus de
   reistijd van nu. Klopt een adres niet, breek dan af en typ het
   preciezer. "Stationsstraat 1" ligt in tientallen plaatsen.

Daarna, onder **Configureren**:

| instelling | standaard | wat het doet |
|---|---|---|
| Marge | 5 min | zoveel eerder dan de aankomsttijd wil je er zijn. Staat altijd op de kaart |
| Stoptijd per tussenstop | 0 min | hoe lang je bij elke stop stilstaat; het vertrek schuift zoveel naar voren |
| Vervoer | auto | auto of motor |
| Vermijden | niets | tolwegen, snelwegen, veerboten, onverharde wegen. Een voorkeur, geen verbod |
| Andere routes tonen | 2 | hoeveel alternatieven er in het detailvenster staan |
| Verversen elke | 5 min | alleen binnen het venster |

En op de tweede pagina het **rooster**: per weekdag *tonen vanaf*, *tonen
tot* en *aankomen om*. Standaard maandag tot en met vrijdag van 06:30 tot
09:30, zonder aankomsttijd. Zonder aankomsttijd toont de kaart de
reistijd en wanneer je aankomt als je nu vertrekt.

## De kaart

```yaml
type: custom:time-to-leave-card
entities:
  - sensor.naar_werk_reistijd
  - sensor.naar_school_reistijd
design: bubble
```

Alles is ook in de visuele editor in te stellen.

### Opties van de kaart

| optie | standaard | wat het doet |
|---|---|---|
| `entities` | — | de reistijd-sensoren van je routes, in volgorde |
| `title` | leeg | een kop boven de kaart |
| `design` | `default` | `default` (eigen opmaak), `ha` (volgt je Home Assistant-thema) of `bubble` (in de stijl van Bubble Card, zonder die kaart nodig te hebben) |
| `show` | `window` | `window`: een route staat er alleen binnen zijn venster, en zonder route in beeld verbergt de kaart zich. `always`: altijd, met buiten het venster wanneer hij terugkomt |
| `details` | `true` | een tik opent het detailvenster |
| `waze` | `true` | een knop om Waze te openen met de bestemming |

Wat de kaart toont:

- **Op de tegel**: de reistijd, de status ("Vertrek om 07:52 · over 18
  min", "Vertrek nu · aankomst 08:21", of "… 11 min te laat"), voor
  wanneer en met welke marge, de wegen en de minuten file. Het stipje is
  groen, oranje of rood naar de vertraging die TomTom meldt.
- **In het venster**: de reistijd nu, gebruikelijk op dit uur, en zonder
  verkeer; wat er verwacht wordt bij je vertrektijd; de files met weg,
  snelheid en vertraging; de etappes langs je tussenstops, elk met een
  eigen Waze-knop; andere routes; en de adressen zoals ze gevonden zijn.

Een sensor die er niet is of niet werkt, blijft in beeld met een melding.
Verbergen zou juist het probleem verbergen.

## Sensoren

Per route twee, onder een apparaat met de naam van de route:

| sensor | waarde |
|---|---|
| `sensor.<route>_reistijd` | minuten rijden als je nu vertrekt. Buiten het venster en bij een fout: onbekend. Met langetermijnstatistiek |
| `sensor.<route>_vertrektijd` | het tijdstip waarop je moet vertrekken; alleen als er vandaag een aankomsttijd is |

In een Engelstalige Home Assistant heten ze `_travel_time` en
`_departure_time`. De attributen van de reistijd zijn wat de kaart leest.
Ze gaan niet naar de recorder; de reistijd zelf wel.

### Een melding vóór vertrek

```yaml
alias: Bijna tijd om naar werk te gaan
triggers:
  - trigger: template
    value_template: >
      {% set v = states('sensor.naar_werk_vertrektijd') %}
      {{ v not in ['unknown', 'unavailable']
         and now() >= as_datetime(v) - timedelta(minutes=10) }}
actions:
  - action: notify.mobile_app_telefoon
    data:
      message: >
        Over 10 minuten vertrekken naar werk
        ({{ states('sensor.naar_werk_reistijd') }} min rijden).
```

## Hoe nauwkeurig is het?

- **De reistijd van nu** is wat TomTom *"the estimated travel time"*
  noemt, met *"all available traffic information"*. Het is een schatting
  van TomTom, geen meting.
- **De vertrektijd** rekent TomTom zelf terug vanaf je aankomsttijd min de
  marge (`arriveAt`), met het verkeer dat hij voor dat moment verwacht.
  De documentatie zegt niet hoe zwaar het live verkeer meeweegt voor een
  moment dat nog moet komen. Wel wordt hij elke ronde opnieuw berekend,
  dus naarmate je vertrek nadert leunt hij op steeds actueler verkeer.
- **Afronding** gaat altijd de veilige kant op: een vertrektijd van
  07:52:40 wordt 07:52, en 10 minuten en 20 seconden te laat wordt 11.
- **Tussenstops**: TomTom rekent de rijtijd langs je stops. Hoe lang je
  daar stilstaat weet hij niet; dat telt deze integratie er gewoon bij.
  Dat het verkeer op dat eerdere moment anders kan zijn, valt erbuiten.
- **Files** zijn wat TomTom op de route meldt. De weg staat erbij als de
  file op een stuk ligt dat TomTom zelf als belangrijk aanmerkt. Anders
  blijft hij leeg, in plaats van de dichtstbijzijnde weg te raden.
- **Het stipje** (groen, oranje, rood) is een keuze van de kaart. Oranje
  vanaf 5 minuten of 15% vertraging ten opzichte van een lege weg, rood
  vanaf 15 minuten of 35%. De getallen zelf staan in het venster.
- **Waze rekent zelf**. De knop geeft Waze alleen de bestemming, en Waze
  kiest zijn eigen route. Die kan afwijken van wat TomTom hier toont.
- **Zomer- en wintertijd**: alles wordt via UTC gerekend en op de klok van
  Home Assistant getoond. Een rit over de wisselnacht klopt op de minuut.
  Daar is een test voor.

## Wat het kost

Per ronde één verzoek, of twee als er vandaag een aankomsttijd is die nog
niet voorbij is. Elk adres wordt hooguit één keer per dag opgezocht.

**Buiten het venster gaat er niets naar TomTom.** De integratie wordt dan
hooguit een keer per uur wakker om te kijken of het venster begint, zonder
verzoek. Dat is gemeten met een simulatie van een hele dag
(`tests/test_coordinator.py`): bij een venster van 06:30 tot 09:30 ging het
eerste verzoek om 06:30 uit en het laatste om 09:25, op een dag zonder
venster geen enkel. Alleen waar jij zelf om vraagt gaat buiten het venster
ook iets uit: een route toevoegen of de adressen wijzigen onder
*Configureren* zoekt ze meteen op en vraagt één route, om te controleren
dat het klopt.

Voor 06:30–09:30, elke 5 minuten en een aankomsttijd van 08:30 zijn dat 60
verzoeken per dag: 36 routeverzoeken, 23 aankomstberekeningen (die stoppen
zodra de streeftijd, 08:25, voorbij is) en één opzoeking per adres. Ligt de
aankomsttijd aan het eind van het venster, dan zijn het er hoogstens 73.
Drie routes blijven ruim onder de 2.500 per dag van het gratis plan.

Weigert TomTom (403: sleutel ongeldig of kwotum op; 429: te veel tegelijk),
dan vraagt de integratie steeds minder vaak: na de eerste weigering drie
keer het gewone ritme, daarna steeds drie keer zoveel, tot hooguit één keer
per uur. Antwoordt TomTom weer, dan gaat hij terug naar het gewone ritme.
Elk nieuw venster begint schoon. De melding staat op de kaart, want op een
telefoon heb je geen logboek.

## Privacy en opslag

- Je adressen gaan naar TomTom, om op te zoeken en om de route te berekenen.
- De sleutel staat in de opslag van Home Assistant, zoals bij elke andere
  integratie.
- **Wat TomTom vindt wordt niet op schijf bewaard**, alleen wat je
  intypte. TomTom's eigen voorwaarden staan achter een inlog en zijn niet
  gelezen. Een concurrent schrijft dat TomTom opslag verbiedt en caching
  alleen toestaat zolang de response-headers het zeggen. Daarom: in het
  geheugen, tot middernacht, of korter als `Cache-Control` dat vraagt.

## Wat niet getest is

- **Een echt antwoord van TomTom.** De parser is getest op de voorbeelden
  uit TomTom's documentatie, niet op een antwoord met een echte sleutel.
  Zie `tests/fixtures/README.md` voor hoe je er een opslaat.
- **Het scherm in een draaiende Home Assistant.** De config flow, de
  secties per weekdag en de editor met `ha-form` zijn opgebouwd met
  gestubde modules. De kaart is in Chromium getekend tegen de
  sensorattributen, niet in Home Assistant zelf.
- **Alternatieven bij een route met tussenstops.** Of TomTom die geeft,
  zegt de documentatie niet. Weigert hij, dan gaat het eenmalig verder
  zonder alternatieven.
