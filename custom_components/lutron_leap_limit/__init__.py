"""Raise pylutron-caseta's LEAP read limit for large Lutron systems.

pylutron-caseta reads each LEAP reply as one line, with asyncio's stream limit
set to 256 KiB. A large HomeWorks QS / RA3 system can send a single reply
bigger than that; the read then fails ("Separator is not found, and chunk
exceed the limit") and the bridge reconnects forever, so the Lutron Caseta
integration never finishes setting up.

This raises the default ``limit`` of ``pylutron_caseta.leap.open_connection``,
which the bridge calls on every (re)connect, so a looping connection recovers
on its next attempt. Remove it once pylutron-caseta raises its own limit.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_INCOMPATIBLE, ISSUE_NOT_NEEDED, LIMIT

_LOGGER = logging.getLogger(__name__)

_ORIGINAL = "original_limit"


def _defaults() -> dict | None:
    from pylutron_caseta import leap

    defaults = getattr(leap.open_connection, "__kwdefaults__", None)
    return defaults if defaults and "limit" in defaults else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Raise the limit, or explain why not."""
    for issue in (ISSUE_INCOMPATIBLE, ISSUE_NOT_NEEDED):
        ir.async_delete_issue(hass, DOMAIN, issue)
    defaults = await hass.async_add_import_executor_job(_defaults)
    if defaults is None:
        _LOGGER.error("pylutron_caseta.leap.open_connection has no limit parameter any more")
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_INCOMPATIBLE,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_INCOMPATIBLE,
        )
        return True
    current = defaults["limit"]
    if current >= LIMIT and not hass.data.get(DOMAIN):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_NOT_NEEDED,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_NOT_NEEDED,
            translation_placeholders={"limit": str(current)},
        )
        return True
    hass.data.setdefault(DOMAIN, {}).setdefault(_ORIGINAL, current)
    defaults["limit"] = LIMIT
    _LOGGER.info("pylutron-caseta LEAP read limit raised from %d to %d bytes", current, LIMIT)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Put the library's own limit back (takes effect on its next reconnect)."""
    data = hass.data.pop(DOMAIN, None)
    if data and (defaults := _defaults()) is not None:
        defaults["limit"] = data[_ORIGINAL]
    return True
