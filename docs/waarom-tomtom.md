# Waarom TomTom en niet Waze

[← terug naar de README](../README.md)

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
