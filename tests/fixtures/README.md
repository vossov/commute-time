# Fixtures

## Wat dit zijn — en wat niet

**Geen van deze bestanden is een echt antwoord van TomTom.** Het zijn de
voorbeelden uit TomTom's eigen documentatie, op 16 november 2026 uit de
pagina gehaald. Een echt antwoord vraagt een sleutel, en die is er in de
ontwikkelomgeving niet. Het is daarmee de bron zelf die het voorbeeld
geeft, en geen verzonnen JSON — maar het is ook niet bewezen dat een echt
antwoord er precies zo uitziet. Vervang ze door echte antwoorden zodra er
een sleutel is (zie "Echte antwoorden opslaan" hieronder).

| bestand | komt van |
|---|---|
| `tomtom_route_documentatie.json` | https://docs.tomtom.com/routing-api/documentation/routing/calculate-route/ — het blok "Response body - JSON" |
| `tomtom_geocode_documentatie.json` | https://docs.tomtom.com/search-api/documentation/geocoding-service/geocode/ — de omhulling (`summary`) en het voorbeeldresultaat, die op de pagina als twee blokken staan |
| `tomtom_fout_documentatie.json` | de calculate-route-pagina — "Structure of an error response" |
| `sensor.json` | wat `sensor.py` als attributen publiceert; de kaart leest precies dit. Opnieuw maken met `python3 tests/maak_sensor_fixture.py` |

## Wat er aan het routevoorbeeld veranderd is

Het voorbeeld in de documentatie is geen geldige JSON. Drie ingrepen, en
verder niets:

1. Regels als `...further points...`, `...further legs...` en
   `...further sections...` zijn weggelaten. Ze staan in de documentatie
   als plaatsaanduiding.
2. Daardoor stonden er vier komma's vlak voor een `]` of `}`; die zijn weg.
3. Twee keer ontbrak een komma na `"sectionType": "TRAVEL_MODE"` in de
   documentatie zelf; die is toegevoegd.

Het voorbeeld is een samenraapsel: een route van 1,1 km in Berlijn met
tol, een tunnel, een voetgangersstuk, een file en twee belangrijke
wegstukken (`Sample Street`, `A10`). Precies daarom is het bruikbaar als
test voor de parser — alle secties die wij lezen staan erin — en
onbruikbaar als beeld van een gewone rit.

## Echte antwoorden opslaan

Met een sleutel in `TOMTOM_KEY`:

```
curl -s "https://api.tomtom.com/routing/1/calculateRoute/52.0907,5.1214:52.3676,4.9041/json?key=$TOMTOM_KEY&traffic=true&routeType=fastest&travelMode=car&routeRepresentation=summaryOnly&computeTravelTimeFor=all&sectionType=traffic&sectionType=importantRoadStretch&maxAlternatives=2&language=nl-NL" > tomtom_route_utrecht_amsterdam.json
```

De sleutel staat alleen in het adres en niet in het antwoord, dus het
bestand kan zo de repo in. Een antwoord tijdens de ochtendspits heeft de meeste
waarde — dan staan er files in.
