# Why TomTom and not Waze

[← back to the README](../README.md)

The original request was "through Waze". That was looked into and
deliberately not done:

- Waze has **no public routing API**. Even Home Assistant's built-in Waze
  integration uses an unofficial route (the `pywaze` library).
- Since September 2026 Waze refuses such requests with a 403. `pywaze`
  1.2.3, in Home Assistant since 2026.10, therefore pretends to be Chrome
  (`curl_cffi`, `impersonate="chrome"`). That was checked in the package's
  source code.
- The [Waze terms of service](https://support.google.com/waze/answer/12373727?hl=en)
  literally forbid *"use automated means to access Content from the
  Service"* and *"You may not circumvent, modify, or disable any security or
  protection measures."* The
  [stricter version](https://support.google.com/waze/answer/17300833)
  applies since 1 August 2026.
- `www.waze.com/robots.txt` excludes `/RoutingManager`, `/row-RoutingManager`
  and `/live-map/api` for every bot.

Getting around a provider's access rules like that was turned down in an
earlier project too. TomTom *does* have an official API, with a free key,
and can work backwards from an arrival time itself.

**Waze stays in the picture for the drive itself.** The button on the card
is a [Waze Deep Link](https://developers.google.com/waze/deeplinks), the
official way to open Waze with a destination. Nothing is requested from
Waze; you tap a link.
