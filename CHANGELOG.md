# Changelog

Wat er per versie veranderd is, in gewone taal. De release-notes op GitHub en in
HACS komen rechtstreeks uit dit bestand: elke versie in `manifest.json` heeft
hier een sectie, en een test faalt als die ontbreekt of leeg is.

Een sectie is zo opgebouwd, nieuwste bovenaan:

- een kop `## [versie] — jjjj-mm-dd`;
- direct daaronder één regel als citaat (`> …`). Die wordt de titel van de release;
- daarna de kopjes `### Nieuw`, `### Verbeterd`, `### Opgelost` en `### Let op`,
  alleen als ze iets te melden hebben, elk met streepjes.

## [0.3.0] — 2026-11-24

> Time to Leave heet nu Commute Time

### Nieuw
- De integratie heet voortaan **Commute Time**. De oude naam was al in gebruik door een bekende app die werkuren bijhoudt, en wie op "Time to Leave" zocht kwam daar terecht. De repository is nu `vossov/commute-time`; het oude adres stuurt GitHub door.

### Let op
- **Dit is geen gewone update: je zet je routes één keer opnieuw op.** Home Assistant ziet Commute Time als een andere integratie dan Time to Leave, dus je routes, je TomTom-sleutel en je kaarten komen niet vanzelf mee.
  1. Voeg in HACS `https://github.com/vossov/commute-time` toe (categorie Integratie), download *Commute Time* en herstart Home Assistant.
  2. Schrijf je routes op (adressen, venster, aankomsttijden) en zorg dat je je TomTom-sleutel bij de hand hebt.
  3. Verwijder de routes van Time to Leave onder *Instellingen → Apparaten & Services*. Doe dit **vóór** je ze opnieuw toevoegt: zolang de oude sensoren bestaan, krijgen de nieuwe `_2` achter hun naam.
  4. Voeg je routes opnieuw toe via *Integratie toevoegen → Commute Time*, met dezelfde naam. Dan heten de sensoren weer `sensor.<route>_reistijd` en `sensor.<route>_vertrektijd` en blijven je automatiseringen werken.
  5. Zet in je dashboards `type: custom:time-to-leave-card` om naar `type: custom:commute-time-card`. De andere kaartopties blijven hetzelfde.
  6. Verwijder Time to Leave in HACS en herstart.

## [0.2.1] — 2026-11-18

> Eerste versie met een versienummer en release-notes in HACS

### Verbeterd
- In HACS staat vanaf nu een versienummer en een beschrijving in plaats van een commit-code. Elke versie krijgt vanzelf een GitHub-release, met de notes uit CHANGELOG.md.
- Een getal en zijn eenheid blijven op de kaart bij elkaar: “3 min file”, “47 min rijden” en “11 min te laat” breken niet meer midden in de eenheid.
- De README is opnieuw opgezet, met afbeeldingen van de kaart. De lange uitleg (over de TomTom-sleutel, waarom geen Waze, en nauwkeurigheid en kosten) staat in de map `docs`.

## [0.2.0] — 2026-11-18

> Bubble-stijl nagebouwd en de vertrektijd bovenaan

### Nieuw
- Met een aankomsttijd staat **de vertrektijd** bovenaan de kaart (“Vertrek 07:52”, of “Vertrek nu” als het zover is). Zonder aankomsttijd staat daar **de rijtijd** (“34 min”).
- Kaartoptie `target` (standaard uit): toont de aankomsttijd en marge die je zelf hebt ingevoerd, onder de naam en in het venster.

### Verbeterd
- De Bubble-stijl lijkt nu op de echte Bubble Card: een lichte pil met het icoon in een donker rondje, 50 px hoog, de waarden als kleine pillen, een pop-up onderaan het scherm, en het icoon in de kleur van de drukte. Ze gebruikt dezelfde `--bubble-*`-variabelen, dus een Bubble-thema werkt door.
- De aftelling “over x min” is weggehaald. De ingevoerde aankomsttijd en marge staan niet meer standaard op de kaart.
- De foutmelding bij een geweigerde sleutel had dubbele haakjes.

### Let op
- De kaart is getekend in een browser met voorbeeldgegevens, niet in Home Assistant zelf en niet met een geïnstalleerd Bubble-thema.

## [0.1.3] — 2026-11-17

> Terugschakelen na een weigering begint bij het gewone ritme

### Verbeterd
- Gemeten met een simulatie van een hele dag: buiten het venster gaat er geen enkel verzoek naar TomTom. Die simulatie is nu een test.
- De README noemde “ruim 70 verzoeken per werkdag”; gemeten zijn het er 60, en hoogstens 73.

### Opgelost
- Weigerde TomTom (403 of 429) in de eerste ronde van de ochtend, dan wachtte de integratie een uur in plaats van een kwartier. Het teruggeschakelde ritme begint nu elk venster schoon.
- Elke ochtend stond ten onrechte de logregel “TomTom antwoordt weer”.

## [0.1.2] — 2026-11-17

> Een geweigerde sleutel zegt welke TomTom-dienst weigerde

### Verbeterd
- Een 403 noemt nu de Search API of de Routing API, en herhaalt wat TomTom er zelf over zegt. In het toevoegscherm zijn dat twee aparte meldingen.

### Let op
- Versie 0.1.1 beweerde dat alleen de Routing API en de Search API nodig waren voor de sleutel. Dat bleek te weinig. Welk product ontbrak is niet vastgesteld; de README legt uit hoe je het minimum zelf vindt.

## [0.1.1] — 2026-11-16

> Uitleg over de TomTom-sleutel

### Verbeterd
- README en invulscherm zeggen hoe je een aparte sleutel maakt, zonder domeinwhitelist en zonder betaalgegevens, en wat te doen als hij uitlekt.

## [0.1.0] — 2026-11-16

> Eerste versie: reistijd en vertrektijd per route, via TomTom

### Nieuw
- Per route een eigen startadres, tot drie tussenstops en een bestemming. Begin en eind mogen een adres zijn, een coördinaat, of een entiteit zoals `zone.home` of `person.naam`.
- Reistijd met verkeer, de wegen waarover je rijdt, de files, en tot drie andere routes.
- Per weekdag een venster waarin de route in beeld is en, als je dat wilt, een aankomsttijd. TomTom rekent daar de vertrektijd bij terug, met een marge die je zelf kiest.
- Twee sensoren per route: de reistijd en de vertrektijd.
- Een eigen dashboardkaart in drie vormgevingen (standaard, Home Assistant-thema en Bubble-stijl), met visuele editor en een knop om Waze te openen.

### Let op
- Waze is bewust niet de bron: er is geen officiële API, en de voorwaarden verbieden geautomatiseerde toegang. De knop gebruikt de officiële Waze-link.
- Nog niet beproefd met een echt TomTom-antwoord of in een draaiende Home Assistant.
