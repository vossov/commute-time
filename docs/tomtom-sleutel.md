# Een TomTom-sleutel

[← terug naar de README](../README.md)

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
