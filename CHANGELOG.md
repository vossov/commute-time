# Changelog

What changed in each version, in plain language. The release notes on GitHub
and in HACS come straight from this file: every version in `manifest.json` has
a section here, and a test fails if it is missing or empty.

A section is built like this, newest at the top:

- a heading `## [version] — yyyy-mm-dd`;
- directly below it one line as a quote (`> …`). That becomes the title of the release;
- then the headings `### Added`, `### Improved`, `### Fixed` and `### Heads-up`,
  only when they have something to say, each with bullets.

## [0.4.0] — 2026-11-24

> The card speaks English and Dutch, and the documentation is in English

### Added
- The card has a **language** option: `en` (English, the default) or `nl` (Dutch). The editor follows the language you pick. Error messages from TomTom, the day a route comes back ("tomorrow 06:30") and the kind of traffic ("roadworks") are shown in that language too.

### Improved
- The README, the documents under `docs` and this changelog are now in English. The documents have English names: `tomtom-key.md`, `why-tomtom.md` and `reliability.md`.

### Fixed
- The setup screen said the margin is always shown on the card. Since 0.2.0 it is only shown with the card option `target`.

### Heads-up
- **Your card switches to English.** If you want to keep it in Dutch, add `language: nl` to the card, or pick *Nederlands* under *Language* in the editor.
- The setup screens follow the language of your Home Assistant, as before.
- The sensors have a few new attributes the card uses (`fout_code`, `fout_param`, `volgend_venster_hhmm`, `volgend_venster_dagen`, `volgend_venster_weekdag`, and `categorie` per traffic item). The existing attributes are unchanged.

## [0.3.0] — 2026-11-24

> Time to Leave is now called Commute Time

### Added
- The integration is now called **Commute Time**. The old name was already used by a well-known app that tracks working hours, and searching for "Time to Leave" led there. The repository is now `vossov/commute-time`; GitHub forwards the old address.

### Heads-up
- **This is not a normal update: you set up your routes once more.** Home Assistant sees Commute Time as a different integration from Time to Leave, so your routes, your TomTom key and your cards do not come along by themselves.
  1. Add `https://github.com/vossov/commute-time` in HACS (category Integration), download *Commute Time* and restart Home Assistant.
  2. Write down your routes (addresses, window, arrival times) and have your TomTom key at hand.
  3. Remove the Time to Leave routes under *Settings → Devices & services*. Do this **before** adding them again: as long as the old sensors exist, the new ones get `_2` after their name.
  4. Add your routes again through *Add integration → Commute Time*, with the same name. Then the sensors get the same names again (`sensor.<route>_travel_time` and `sensor.<route>_departure_time`, or `_reistijd` and `_vertrektijd` in a Dutch Home Assistant) and your automations keep working.
  5. In your dashboards, change `type: custom:time-to-leave-card` to `type: custom:commute-time-card`. The other card options stay the same.
  6. Remove Time to Leave in HACS and restart.

## [0.2.1] — 2026-11-18

> First version with a version number and release notes in HACS

### Improved
- HACS now shows a version number and a description instead of a commit code. Every version gets a GitHub release automatically, with the notes from CHANGELOG.md.
- A number and its unit stay together on the card: “3 min file”, “47 min rijden” and “11 min te laat” no longer break in the middle.
- The README has been redone, with pictures of the card. The long explanations (about the TomTom key, why not Waze, and accuracy and cost) are in the `docs` folder.

## [0.2.0] — 2026-11-18

> Bubble style rebuilt and the departure time at the top

### Added
- With an arrival time, **the departure time** is at the top of the card (“Vertrek 07:52”, or “Vertrek nu” when it is time). Without an arrival time it shows **the driving time** (“34 min”).
- Card option `target` (off by default): shows the arrival time and margin you entered yourself, under the name and in the detail view.

### Improved
- The Bubble style now looks like the real Bubble Card: a light pill with the icon in a dark circle, 50 px high, the values as small pills, a pop-up at the bottom of the screen, and the icon in the colour of the traffic. It uses the same `--bubble-*` variables, so a Bubble theme carries through.
- The countdown “over x min” has been removed. The arrival time and margin you entered are no longer on the card by default.
- The error message for a refused key had double brackets.

### Heads-up
- The card was rendered in a browser with sample data, not in Home Assistant itself and not with a Bubble theme installed.

## [0.1.3] — 2026-11-17

> Backing off after a refusal starts from the normal interval

### Improved
- Measured with a simulation of a whole day: outside the window not a single request goes to TomTom. That simulation is now a test.
- The README said “just over 70 requests per working day”; measured, it is 60, and at most 73.

### Fixed
- If TomTom refused (403 or 429) in the first round of the morning, the integration waited an hour instead of a quarter of an hour. The backed-off interval now starts fresh in every window.
- Every morning the log line “TomTom antwoordt weer” appeared for no reason.

## [0.1.2] — 2026-11-17

> A refused key says which TomTom service refused

### Improved
- A 403 now names the Search API or the Routing API, and repeats what TomTom itself says about it. In the setup screen these are two separate messages.

### Heads-up
- Version 0.1.1 claimed that only the Routing API and the Search API were needed for the key. That turned out not to be enough. Which product was missing has not been established; the README explains how to find the minimum yourself.

## [0.1.1] — 2026-11-16

> About the TomTom key

### Improved
- The README and the setup screen say how to create a separate key, without a domain whitelist and without payment details, and what to do if it leaks.

## [0.1.0] — 2026-11-16

> First version: travel time and departure time per route, through TomTom

### Added
- A start address per route, up to three stops on the way and a destination. Start and end can be an address, a coordinate, or an entity such as `zone.home` or `person.name`.
- Travel time with traffic, the roads you drive on, the traffic jams, and up to three other routes.
- Per weekday a window in which the route is shown and, if you like, an arrival time. TomTom works out the departure time for it, with a margin you choose.
- Two sensors per route: the travel time and the departure time.
- A dashboard card in three designs (default, Home Assistant theme and Bubble style), with a visual editor and a button to open Waze.

### Heads-up
- Waze is deliberately not the source: there is no official API, and the terms forbid automated access. The button uses the official Waze link.
- Not yet tried with a real TomTom answer or in a running Home Assistant.
