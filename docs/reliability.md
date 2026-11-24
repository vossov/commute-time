# Accuracy, cost, privacy and what has not been tested

[← back to the README](../README.md)

## How accurate is it?

- **The travel time now** is what TomTom calls *"the estimated travel
  time"*, with *"all available traffic information"*. It is TomTom's
  estimate, not a measurement.
- **The departure time** is worked out by TomTom itself, backwards from
  your arrival time minus the margin (`arriveAt`), with the traffic it
  expects for that moment. The documentation does not say how much live
  traffic counts for a moment that is still to come. It is recalculated
  every round, though, so as your departure gets closer it relies on ever
  more current traffic.
- **Rounding** always goes the safe way: a departure time of 07:52:40
  becomes 07:52, and 10 minutes and 20 seconds late becomes 11.
- **Stops on the way**: TomTom calculates the driving time past your
  stops. How long you stand still there it does not know; this
  integration simply adds it. That traffic may be different at that
  earlier moment is not taken into account.
- **Traffic jams** are what TomTom reports on the route. The road is shown
  when the jam lies on a stretch TomTom itself marks as important.
  Otherwise it stays empty, instead of guessing the nearest road.
- **The dot** (green, orange, red) is a choice made by the card. Orange
  from 5 minutes or 15% delay compared with an empty road, red from 15
  minutes or 35%. The numbers themselves are in the detail view.
- **Waze does its own routing**. The button only gives Waze the
  destination, and Waze picks its own route. That can differ from what
  TomTom shows here.
- **Daylight saving time**: everything is calculated in UTC and shown on
  Home Assistant's clock. A drive across the night the clocks change is
  right to the minute. There is a test for that.

## What it costs

One request per round, or two when there is an arrival time today that has
not passed yet. Each address is looked up at most once a day.

**Outside the window nothing goes to TomTom.** The integration then wakes
up at most once an hour to see whether the window starts, without a
request. That was measured with a simulation of a whole day
(`tests/test_coordinator.py`): with a window from 06:30 to 09:30 the first
request went out at 06:30 and the last at 09:25; on a day without a window
not a single one. Only what you ask for yourself goes out outside the
window: adding a route or changing its addresses under *Configure* looks
them up straight away and requests one route, to check that it works.

For 06:30–09:30, every 5 minutes and an arrival time of 08:30 that is 60
requests a day: 36 route requests, 23 arrival calculations (those stop once
the target time, 08:25, has passed) and one lookup per address. If the
arrival time is at the end of the window, it is at most 73. Three routes
stay well below the 2,500 a day of the free plan.

If TomTom refuses (403: key invalid or quota used up; 429: too many at
once), the integration asks less and less often: after the first refusal
three times the normal interval, then three times as long each time, up to
at most once an hour. When TomTom answers again, it returns to the normal
interval. Every new window starts fresh. The message is shown on the card,
because on a phone you have no log.

## Privacy and storage

- Your addresses go to TomTom, to look them up and to calculate the route.
- The key is stored in Home Assistant's storage, like with any other
  integration.
- **What TomTom finds is not stored on disk**, only what you typed.
  TomTom's own terms are behind a login and have not been read. A
  competitor writes that TomTom forbids storage and only allows caching
  for as long as the response headers say. Hence: in memory, until
  midnight, or shorter if `Cache-Control` asks for that.

## What has not been tested

- **A real answer from TomTom.** The parser is tested on the examples from
  TomTom's documentation, not on an answer from a real key. See
  `tests/fixtures/README.md` for how to save one.
- **The screens in a running Home Assistant.** The config flow, the
  sections per weekday and the editor with `ha-form` are built with
  stubbed modules. The card was rendered in Chromium against the sensor
  attributes, not in Home Assistant itself.
- **The card in Dutch and English in Home Assistant itself.** Both
  languages are tested on the card's text in Node and rendered in
  Chromium; switching the language in the editor of a running Home
  Assistant has not been tried.
- **Alternatives on a route with stops.** Whether TomTom gives them, the
  documentation does not say. If it refuses, the integration carries on
  once without alternatives.
