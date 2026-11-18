# Nauwkeurigheid, kosten, privacy en wat niet getest is

[← terug naar de README](../README.md)

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
