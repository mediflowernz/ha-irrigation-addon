"""Pytest configuration and fixtures for irrigation addon tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.irrigation_addon.const import DOMAIN


@pytest.fixture
def hass():
    """Return a mock Home Assistant instance."""
    hass_mock = MagicMock(spec=HomeAssistant)
    hass_mock.data = {DOMAIN: {}}
    hass_mock.states = MagicMock()
    hass_mock.services = MagicMock()
    hass_mock.async_create_task = MagicMock()
    return hass_mock


@pytest.fixture
def config_entry():
    """Return a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "name": "Test Irrigation System",
        "settings": {
            "pump_zone_delay": 3,
            "sensor_update_interval": 30,
            "fail_safe_enabled": True
        }
    }
    return entry


@pytest.fixture
def mock_storage():
    """Return a mock storage instance."""
    storage = AsyncMock()
    storage.async_load = AsyncMock()
    storage.async_save = AsyncMock()
    storage.async_get_rooms = AsyncMock(return_value={})
    storage.async_get_settings = AsyncMock(return_value={})
    storage.async_save_room = AsyncMock()
    storage.async_delete_room = AsyncMock(return_value=True)
    storage.async_update_settings = AsyncMock()
    return storage


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)