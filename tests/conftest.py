"""Fixtures for Lutron LEAP Limit tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pylutron_caseta import leap

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture(autouse=True)
def enable_integration(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration under test."""


@pytest.fixture(autouse=True)
def no_lutron_setup(hass: HomeAssistant):
    """The dependency on lutron_caseta is only for its requirements."""
    hass.config.components.add("lutron_caseta")


@pytest.fixture(autouse=True)
def restore_limit():
    """Never leak a changed default between tests."""
    original = dict(leap.open_connection.__kwdefaults__)
    yield
    leap.open_connection.__kwdefaults__.clear()
    leap.open_connection.__kwdefaults__.update(original)
