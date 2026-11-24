# A TomTom key

[← back to the README](../README.md)

The integration calls exactly two TomTom services, both in the classic
version (not the newer Orbis variants):

| service | address | used for |
|---|---|---|
| Routing API | `api.tomtom.com/routing/1/calculateRoute` | travel time with traffic, roads, traffic jams, and the departure time for an arrival time |
| Search API | `api.tomtom.com/search/2/geocode` | looking up an address you typed. Not needed for `zone.home`, a person or a coordinate |

How to set up the key:

1. **Create an account** at [developer.tomtom.com](https://developer.tomtom.com),
   on the free Freemium plan.
2. **Create a separate key** for this integration. TomTom itself recommends
   a separate key per application
   ([best practices](https://docs.tomtom.com/platform/documentation/api-best-practices/api-key-management-best-practices)).
   If it leaks, only this is affected.
3. **Enable the products TomTom asks for, then look for the minimum.**
   Exactly which products that are has **not been established**. In the
   first try, "Routing API" and "Search API" alone turned out not to be
   enough; that key now has all products enabled. Which product was
   missing we do not know: the names in the portal are behind a login and
   have never been checked. What we do know: the message was TomTom's
   general refusal (403), from a version that did not yet say which
   service refused, and the same key worked once all products were
   enabled. That points to a missing product; whether TomTom only
   activates a new key after a while has not been checked. A key with all
   products does more damage if it leaks; the other steps here limit
   that, but do not replace the minimum.

   How to find the minimum, with a key that works now:
   - Disable one product.
   - Add the integration again with an **address** as destination (with
     only coordinates or `zone.home` the Search API is not tried) and
     cancel at the confirmation step. Nothing is saved then.
   - If TomTom refuses, the message names the service: *Search API*
     (looking up addresses) or *Routing API* (calculating routes). That is
     the service TomTom refused, not the name of the missing product.
     Enable the product again and try the next one.
4. **Leave the domain whitelist empty.** It is meant for a key that sits in
   a web page, and works through CORS, a check the browser does. Here the
   key goes from Home Assistant itself to TomTom and never reaches your
   browser, so a whitelist protects nothing. Whether TomTom would refuse
   requests without a browser when a whitelist is set, has not been
   checked.
5. **Do not add payment details.** Without a credit card a leaked key
   cannot run up a bill; above the daily quota TomTom refuses, and the
   card says so. That follows from the plan; it has not been tried.

**Where the key is stored:** in Home Assistant's storage
(`.storage/core.config_entries`), unencrypted, like with any integration.
So it is also in your backups. It is *not* in the attributes, not in the
card and not in error messages in the log; there are tests for that.

**If it leaks anyway:** TomTom can renew a key (*key rotation*); the old
one keeps working for a while. Then enter the new one for each route under
*Configure*. One key per route is a known limitation.

The free plan gives 2,500 requests a day, without a credit card. That is
on TomTom's pricing page; whether that number applies per service or to
all services together has not been checked.
