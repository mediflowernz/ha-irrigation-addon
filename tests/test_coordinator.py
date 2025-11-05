"""Test irrigation coordinator functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from custom_components.irrigation_addon.coordinator import IrrigationCoordinator
from custom_components.irrigation_addon.models import Room, IrrigationEvent, Shot
from custom_components.irrigation_addon.const import EVENT_TYPE_P1, EVENT_TYPE_P2


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.async_create_task = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {"name": "Test Integration"}
    return entry


@pytest.fixture
def sample_room():
    """Create a sample room for testing."""
    return Room(
        room_id="room1",
        name="Test Room",
        pump_entity="switch.pump1",
        zone_entities=["switch.zone1", "switch.zone2"],
        light_entity="light.grow_light",
        sensors={"soil_rh": "sensor.moisture", "temperature": "sensor.temp"}
    )


@pytest.fixture
def sample_event():
    """Create a sample irrigation event for testing."""
    shots = [Shot(duration=30, interval_after=60), Shot(duration=45)]
    return IrrigationEvent(
        event_type=EVENT_TYPE_P1,
        shots=shots,
        schedule="0 8 * * *",
        enabled=True
    )


class TestIrrigationCoordinator:
    """Test IrrigationCoordinator functionality."""

    @pytest.fixture
    async def coordinator(self, mock_hass, mock_config_entry):
        """Create a coordinator instance for testing."""
        with patch('custom_components.irrigation_addon.coordinator.IrrigationStorage'):
            coordinator = IrrigationCoordinator(mock_hass, mock_config_entry)
            coordinator.storage = AsyncMock()
            coordinator.storage.async_load = AsyncMock()
            coordinator.storage.async_get_rooms = AsyncMock(return_value={})
            coordinator.storage.async_get_settings = AsyncMock(return_value={})
            return coordinator

    async def test_coordinator_initialization(self, coordinator, mock_hass, mock_config_entry):
        """Test coordinator initialization."""
        assert coordinator.hass == mock_hass
        assert coordinator.entry == mock_config_entry
        assert coordinator._rooms == {}
        assert coordinator._settings == {}

    async def test_async_setup(self, coordinator):
        """Test coordinator setup."""
        coordinator.storage.async_get_rooms.return_value = {}
        coordinator.storage.async_get_settings.return_value = {"sensor_update_interval": 30}
        
        await coordinator.async_setup()
        
        coordinator.storage.async_load.assert_called_once()
        coordinator.storage.async_get_rooms.assert_called_once()
        coordinator.storage.async_get_settings.assert_called_once()

    async def test_async_add_room(self, coordinator, sample_room):
        """Test adding a room."""
        # Mock entity validation
        sample_room.validate_entities_exist = AsyncMock(return_value=[])
        coordinator.storage.async_save_room = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        await coordinator.async_add_room(sample_room)
        
        coordinator.storage.async_save_room.assert_called_once_with(sample_room)
        coordinator.async_request_refresh.assert_called_once()
        assert coordinator._rooms[sample_room.room_id] == sample_room

    async def test_async_add_room_missing_entities(self, coordinator, sample_room):
        """Test adding a room with missing entities."""
        # Mock entity validation to return missing entities
        sample_room.validate_entities_exist = AsyncMock(return_value=["switch.missing"])
        
        with pytest.raises(HomeAssistantError, match="Missing entities"):
            await coordinator.async_add_room(sample_room)

    async def test_async_update_room(self, coordinator, sample_room):
        """Test updating a room."""
        # Setup existing room
        coordinator._rooms[sample_room.room_id] = sample_room
        
        # Mock entity validation
        sample_room.validate_entities_exist = AsyncMock(return_value=[])
        coordinator.storage.async_save_room = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        # Update room name
        sample_room.name = "Updated Room"
        await coordinator.async_update_room(sample_room)
        
        coordinator.storage.async_save_room.assert_called_once_with(sample_room)
        coordinator.async_request_refresh.assert_called_once()
        assert coordinator._rooms[sample_room.room_id].name == "Updated Room"

    async def test_async_delete_room(self, coordinator, sample_room):
        """Test deleting a room."""
        # Setup existing room
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator.storage.async_delete_room = AsyncMock(return_value=True)
        coordinator.async_request_refresh = AsyncMock()
        
        await coordinator.async_delete_room(sample_room.room_id)
        
        coordinator.storage.async_delete_room.assert_called_once_with(sample_room.room_id)
        coordinator.async_request_refresh.assert_called_once()
        assert sample_room.room_id not in coordinator._rooms

    async def test_async_update_settings(self, coordinator):
        """Test updating settings."""
        new_settings = {"sensor_update_interval": 60, "fail_safe_enabled": False}
        coordinator.storage.async_update_settings = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        await coordinator.async_update_settings(new_settings)
        
        coordinator.storage.async_update_settings.assert_called_once_with(new_settings)
        coordinator.async_request_refresh.assert_called_once()
        assert coordinator._settings["sensor_update_interval"] == 60
        assert coordinator._settings["fail_safe_enabled"] is False

    async def test_get_room_status(self, coordinator, sample_room):
        """Test getting room status."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._daily_irrigation_totals[sample_room.room_id] = 300
        
        status = coordinator.get_room_status(sample_room.room_id)
        
        assert status["active_irrigation"] is False
        assert status["manual_run"] is False
        assert status["daily_total"] == 300
        assert "next_events" in status
        assert "last_events" in status

    async def test_get_room_status_with_active_irrigation(self, coordinator, sample_room):
        """Test getting room status with active irrigation."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._active_irrigations[sample_room.room_id] = {
            "event_type": EVENT_TYPE_P1,
            "current_shot": 1,
            "total_shots": 2,
            "progress": 0.5
        }
        
        status = coordinator.get_room_status(sample_room.room_id)
        
        assert status["active_irrigation"] is True
        assert status["active_irrigation_details"]["event_type"] == EVENT_TYPE_P1
        assert status["active_irrigation_details"]["current_shot"] == 1
        assert status["active_irrigation_details"]["progress"] == 0.5

    async def test_check_fail_safes_all_pass(self, coordinator, sample_room):
        """Test fail-safe checks when all pass."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._settings = {"fail_safe_enabled": True, "max_daily_irrigation": 3600}
        coordinator._daily_irrigation_totals = {}
        
        # Mock entity states
        coordinator.hass.states.get.side_effect = lambda entity_id: MagicMock(state="on")
        
        result = await coordinator._check_fail_safes(sample_room.room_id, 300)
        
        assert result["allowed"] is True
        assert result["reason"] == ""

    async def test_check_fail_safes_light_schedule_conflict(self, coordinator, sample_room):
        """Test fail-safe checks with light schedule conflict."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._settings = {"fail_safe_enabled": True}
        
        # Mock light entity state as off
        def mock_get_state(entity_id):
            if entity_id == sample_room.light_entity:
                return MagicMock(state="off")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        
        result = await coordinator._check_fail_safes(sample_room.room_id, 300)
        
        assert result["allowed"] is False
        assert "lights are off" in result["reason"]

    async def test_check_fail_safes_overwatering_prevention(self, coordinator, sample_room):
        """Test fail-safe checks with overwatering prevention."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._settings = {"fail_safe_enabled": True, "max_daily_irrigation": 3600}
        coordinator._daily_irrigation_totals[sample_room.room_id] = 3500  # Already near limit
        
        # Mock entity states as available
        coordinator.hass.states.get.side_effect = lambda entity_id: MagicMock(state="on")
        
        result = await coordinator._check_fail_safes(sample_room.room_id, 200)  # Would exceed limit
        
        assert result["allowed"] is False
        assert "Daily irrigation limit exceeded" in result["reason"]

    async def test_check_fail_safes_entity_unavailable(self, coordinator, sample_room):
        """Test fail-safe checks with unavailable entities."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._settings = {"fail_safe_enabled": True}
        
        # Mock pump entity as unavailable
        def mock_get_state(entity_id):
            if entity_id == sample_room.pump_entity:
                return MagicMock(state="unavailable")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        
        result = await coordinator._check_fail_safes(sample_room.room_id, 300)
        
        assert result["allowed"] is False
        assert "Unavailable entities" in result["reason"]

    async def test_check_fail_safes_irrigation_conflict(self, coordinator, sample_room):
        """Test fail-safe checks with irrigation conflict."""
        coordinator._rooms[sample_room.room_id] = sample_room
        coordinator._settings = {"fail_safe_enabled": True}
        coordinator._active_irrigations[sample_room.room_id] = {"event_type": EVENT_TYPE_P1}
        
        result = await coordinator._check_fail_safes(sample_room.room_id, 300)
        
        assert result["allowed"] is False
        assert "already active" in result["reason"]

    async def test_activate_pump_success(self, coordinator):
        """Test successful pump activation."""
        coordinator.hass.states.get.return_value = MagicMock(state="off")
        coordinator.hass.services.async_call = AsyncMock()
        
        result = await coordinator._activate_pump("room1", "switch.pump1")
        
        assert result is True
        coordinator.hass.services.async_call.assert_called_once_with(
            "switch", "turn_on", {"entity_id": "switch.pump1"}
        )

    async def test_activate_pump_unavailable(self, coordinator):
        """Test pump activation with unavailable entity."""
        coordinator.hass.states.get.return_value = MagicMock(state="unavailable")
        
        result = await coordinator._activate_pump("room1", "switch.pump1")
        
        assert result is False

    async def test_activate_zones_success(self, coordinator):
        """Test successful zone activation."""
        coordinator.hass.states.get.return_value = MagicMock(state="off")
        coordinator.hass.services.async_call = AsyncMock()
        
        zones = ["switch.zone1", "switch.zone2"]
        result = await coordinator._activate_zones("room1", zones)
        
        assert result is True
        assert coordinator.hass.services.async_call.call_count == 2

    async def test_activate_zones_partial_success(self, coordinator):
        """Test zone activation with some zones unavailable."""
        def mock_get_state(entity_id):
            if entity_id == "switch.zone1":
                return MagicMock(state="off")
            return MagicMock(state="unavailable")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        coordinator.hass.services.async_call = AsyncMock()
        
        zones = ["switch.zone1", "switch.zone2"]
        result = await coordinator._activate_zones("room1", zones)
        
        assert result is True  # At least one zone activated
        coordinator.hass.services.async_call.assert_called_once()

    async def test_deactivate_pump_success(self, coordinator):
        """Test successful pump deactivation."""
        coordinator.hass.services.async_call = AsyncMock()
        
        result = await coordinator._deactivate_pump("room1", "switch.pump1")
        
        assert result is True
        coordinator.hass.services.async_call.assert_called_once_with(
            "switch", "turn_off", {"entity_id": "switch.pump1"}
        )

    async def test_deactivate_zones_success(self, coordinator):
        """Test successful zone deactivation."""
        coordinator.hass.services.async_call = AsyncMock()
        
        zones = ["switch.zone1", "switch.zone2"]
        result = await coordinator._deactivate_zones("room1", zones)
        
        assert result is True
        assert coordinator.hass.services.async_call.call_count == 2

    async def test_get_system_health_healthy(self, coordinator):
        """Test system health when everything is healthy."""
        coordinator._rooms = {"room1": MagicMock()}
        coordinator._active_irrigations = {}
        coordinator._manual_runs = {}
        coordinator._settings = {"fail_safe_enabled": True}
        coordinator._daily_irrigation_totals = {"room1": 1000}
        
        health = coordinator.get_system_health()
        
        assert health["status"] == "healthy"
        assert health["rooms_count"] == 1
        assert health["active_irrigations"] == 0
        assert health["fail_safe_enabled"] is True
        assert len(health["issues"]) == 0

    async def test_get_system_health_with_issues(self, coordinator):
        """Test system health with issues."""
        coordinator._rooms = {"room1": MagicMock()}
        coordinator._settings = {"fail_safe_enabled": True, "max_daily_irrigation": 3600}
        coordinator._daily_irrigation_totals = {"room1": 3600}  # At limit
        
        health = coordinator.get_system_health()
        
        assert health["status"] == "warning"
        assert len(health["issues"]) > 0
        assert any("Daily limit reached" in issue for issue in health["issues"])

    async def test_emergency_stop_all(self, coordinator, sample_room):
        """Test emergency stop for all rooms."""
        coordinator._rooms = {sample_room.room_id: sample_room}
        coordinator._active_irrigations = {sample_room.room_id: {"event_type": EVENT_TYPE_P1}}
        coordinator._manual_runs = {}
        
        coordinator.async_stop_irrigation = AsyncMock(return_value=True)
        coordinator._deactivate_zones = AsyncMock(return_value=True)
        coordinator._deactivate_pump = AsyncMock(return_value=True)
        coordinator.async_request_refresh = AsyncMock()
        
        results = await coordinator.async_emergency_stop_all()
        
        coordinator.async_stop_irrigation.assert_called_once_with(sample_room.room_id)
        coordinator._deactivate_zones.assert_called_once()
        coordinator._deactivate_pump.assert_called_once()
        coordinator.async_request_refresh.assert_called_once()
        
        assert results[f"{sample_room.room_id}_irrigation"] is True
        assert results[f"{sample_room.room_id}_safety_shutoff"] is True