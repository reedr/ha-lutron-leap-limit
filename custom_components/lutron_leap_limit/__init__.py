"""Raise pylutron-caseta's LEAP read limit for large Lutron systems.

pylutron-caseta reads each LEAP reply as one line, with asyncio's stream limit
set to 256 KiB. A large HomeWorks QS / RA3 system can send a single reply
bigger than that; the read then fails ("Separator is not found, and chunk
exceed the limit") and the bridge reconnects forever, so the Lutron Caseta
integration never finishes setting up.

This raises the default ``limit`` of ``pylutron_caseta.leap.open_connection``,
which the bridge calls on every (re)connect, so a looping connection recovers
on its next attempt. Remove it once pylutron-caseta raises its own limit.

Since 1.1.0 it also raises the library's per-request timeout (5 s) to 15 s:
a large processor answers bursts of commands late, and the 5 s limit turned
commands that had worked into errors (see const.REQUEST_TIMEOUT).
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_INCOMPATIBLE, ISSUE_NOT_NEEDED, LIMIT, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

_ORIGINAL = "original_limit"
_TIMEOUT_DATA = f"{DOMAIN}_timeout"


def _defaults() -> dict | None:
    from pylutron_caseta import leap

    defaults = getattr(leap.open_connection, "__kwdefaults__", None)
    return defaults if defaults and "limit" in defaults else None


def _smartbridge():
    from pylutron_caseta import smartbridge

    return smartbridge


async def _raise_timeout(hass: HomeAssistant) -> None:
    """Give each LEAP request REQUEST_TIMEOUT seconds instead of the library's 5."""
    bridge = await hass.async_add_import_executor_job(_smartbridge)
    current = getattr(bridge, "REQUEST_TIMEOUT", None)
    if not isinstance(current, (int, float)):
        _LOGGER.warning("pylutron_caseta.smartbridge has no REQUEST_TIMEOUT any more; request timeout left alone")
        return
    original = hass.data.setdefault(_TIMEOUT_DATA, current)
    if original < REQUEST_TIMEOUT:
        bridge.REQUEST_TIMEOUT = REQUEST_TIMEOUT
        _LOGGER.info("pylutron-caseta request timeout raised from %s to %s s", original, REQUEST_TIMEOUT)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Raise the limit and the request timeout, or explain why not."""
    await _raise_timeout(hass)
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
    """Put the library's own limit (on its next reconnect) and timeout back."""
    original = hass.data.pop(_TIMEOUT_DATA, None)
    if original is not None:
        _smartbridge().REQUEST_TIMEOUT = original
    data = hass.data.pop(DOMAIN, None)
    if data and (defaults := _defaults()) is not None:
        defaults["limit"] = data[_ORIGINAL]
    return True
