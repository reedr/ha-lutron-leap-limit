# Lutron LEAP Limit

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/reedr/ha-lutron-leap-limit)

A stopgap for large Lutron systems (HomeWorks QS, RA3) on the built-in **Lutron Caseta** integration.

`pylutron-caseta` reads each LEAP reply as a single line, with asyncio's read limit set to 256 KiB. A big system can
send one reply larger than that. The read then fails with

```
Reconnecting after error: Separator is not found, and chunk exceed the limit
```

and the bridge reconnects forever, so Lutron Caseta never finishes setting up and none of its entities load.

This integration raises the default read limit of `pylutron_caseta.leap.open_connection` to 4 MiB when it loads. The
bridge calls that function on every reconnect, so a connection stuck in that loop recovers on its next attempt; nothing
else is changed. Unloading the integration puts the library's own limit back.

Since 1.1.0 it also raises the library's per-request timeout from 5 s to 15 s. A big processor sent a burst of zone
commands (turning off every light in a large room, say) can answer some of them after more than 5 s: the lights change,
but the calls fail with `TimeoutError` and the late replies are logged as "Was not expecting message with tag ...".
Unloading puts the 5 s timeout back.

## Setup

Install through HACS, restart, then **Settings → Devices & services → Add integration → Lutron LEAP Limit**.

## When to remove it

Once `pylutron-caseta` raises its own limit to 4 MiB or more, a repair says the integration is no longer needed. If the
library's connection function stops taking a limit, a repair says it can't apply its change.

## License

MIT. See [LICENSE](LICENSE).
