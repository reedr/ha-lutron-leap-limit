"""The limit change, its removal, and the safety checks."""

from __future__ import annotations

import asyncio
import json

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from pylutron_caseta import leap
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lutron_leap_limit.const import DOMAIN, LIMIT

LIBRARY_LIMIT = 2**18


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Lutron LEAP Limit")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _read_big_reply(size: int) -> dict:
    """Serve one LEAP-style reply of ``size`` bytes and read it with the library."""
    body = json.dumps({"CommuniqueType": "ReadResponse", "Body": {"x": "y" * size}}).encode()
    done = asyncio.Event()

    async def serve(reader, writer):
        writer.write(body + b"\r\n")
        await writer.drain()
        await done.wait()
        writer.close()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    protocol = await leap.open_connection("127.0.0.1", port)
    try:
        return json.loads(await protocol._reader.readline())
    finally:
        done.set()
        protocol._writer.close()
        server.close()
        await server.wait_closed()


async def test_large_reply(hass: HomeAssistant, socket_enabled) -> None:
    """A 300 KB reply fails at the library's limit and reads once the limit is raised."""
    assert leap.open_connection.__kwdefaults__["limit"] == LIBRARY_LIMIT
    with pytest.raises(ValueError, match="limit"):
        await _read_big_reply(300_000)

    entry = await _setup(hass)
    assert leap.open_connection.__kwdefaults__["limit"] == LIMIT
    reply = await _read_big_reply(300_000)
    assert len(reply["Body"]["x"]) == 300_000

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert leap.open_connection.__kwdefaults__["limit"] == LIBRARY_LIMIT


async def test_not_needed(hass: HomeAssistant) -> None:
    leap.open_connection.__kwdefaults__["limit"] = 8 * 1024 * 1024
    await _setup(hass)
    assert leap.open_connection.__kwdefaults__["limit"] == 8 * 1024 * 1024
    assert ir.async_get(hass).async_get_issue(DOMAIN, "not_needed")


async def test_incompatible(hass: HomeAssistant) -> None:
    del leap.open_connection.__kwdefaults__["limit"]
    await _setup(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "incompatible")


async def test_reload_keeps_original(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert leap.open_connection.__kwdefaults__["limit"] == LIMIT
    assert not ir.async_get(hass).async_get_issue(DOMAIN, "not_needed")
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert leap.open_connection.__kwdefaults__["limit"] == LIBRARY_LIMIT


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
