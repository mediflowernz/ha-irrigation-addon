"""Integration tests for the Irrigation Addon."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from custom_components.irrigation_addon import async_setup_entry, async_unload_entry
from custom_components.irrigation_addon.coordinator import IrrigationCoordinator
from custom_components.irrigation_addon.models import Room, IrrigationEvent, Shot
from custom_components.irrigation_addon.const import DOMAIN, EVENT_TYPE_P1, EVENT_TYPE_P2


class TestIntegrationSetup:
    """Test integration setup and teardown."""

    @pytest.fixture
    async def mock_hass_with_services(self):
        """Create a mock Home Assistant with service registry."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        hass.states = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.async_create_task = MagicMock()
        hass.http = MagicMock()
        hass.http.register_static_path = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry_full(self):
        """Create a complete mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_integration"
        entry.data = {
            "name": "Test Irrigation System",
            "settings": {
                "pump_zone_delay": 3,
                "sensor_update_interval": 30,
                "default_manual_duration": 300,
                "fail_safe_enabled": True,
                "emergency_stop_enabled": True,
                "notifications_enabled": True
            }
        }
        return entry

    async def test_async_setup_entry_success(self, mock_hass_with_services, mock_config_entry_full):
        """Test successful integration setup."""
        with patch('custom_components.irrigation_addon.IrrigationCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.async_setup = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            
            result = await async_setup_entry(mock_hass_with_services, mock_config_entry_full)
            
            assert result is True
            assert mock_config_entry_full.entry_id in mock_hass_with_services.data[DOMAIN]
            mock_coordinator.async_setup.assert_called_once()
            
            # Verify services are registered
            assert mock_hass_with_services.services.async_register.call_count >= 4

    async def test_async_setup_entry_coordinator_failure(self, mock_hass_with_services, mock_config_entry_full):
        """Test integration setup with coordinator failure."""
        with patch('custom_components.irrigation_addon.IrrigationCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.async_setup.side_effect = Exception("Setup failed")
            mock_coordinator_class.return_value = mock_coordinator
            
            result = await async_setup_entry(mock_hass_with_services, mock_config_entry_full)
            
            assert result is False

    async def test_async_unload_entry_success(self, mock_hass_with_services, mock_config_entry_full):
        """Test successful integration unload."""
        # Setup coordinator in hass data
        mock_coordinator = AsyncMock()
        mock_coordinator.async_shutdown = AsyncMock()
        mock_hass_with_services.data[DOMAIN][mock_config_entry_full.entry_id] = mock_coordinator
        
        result = await async_unload_entry(mock_hass_with_services, mock_config_entry_full)
        
        assert result is True
        mock_coordinator.async_shutdown.assert_called_once()
        assert mock_config_entry_full.entry_id not in mock_hass_with_services.data[DOMAIN]

    async def test_async_unload_entry_not_loaded(self, mock_hass_with_services, mock_config_entry_full):
        """Test unloading entry that wasn't loaded."""
        result = await async_unload_entry(mock_hass_with_services, mock_config_entry_full)
        
        assert result is True  # Should still return True even if not loaded


class TestEndToEndIrrigationCycles:
    """Test complete irrigation cycles end-to-end."""

    @pytest.fixture
    async def setup_coordinator_with_room(self, mock_hass_with_services, mock_config_entry_full):
        """Setup coordinator with a test room."""
        with patch('custom_components.irrigation_addon.coordinator.IrrigationStorage'):
            coordinator = IrrigationCoordinator(mock_hass_with_services, mock_config_entry_full)
            coordinator.storage = AsyncMock()
            
            # Create test room with events
            test_room = Room(
                room_id="test_room",
                name="Test Room",
                pump_entity="switch.test_pump",
                zone_entities=["switch.test_zone1", "switch.test_zone2"],
                light_entity="light.test_light",
                sensors={"soil_rh": "sensor.test_moisture", "temperature": "sensor.test_temp"}
            )
            
            # Add test events
            p1_event = IrrigationEvent(
                event_type=EVENT_TYPE_P1,
                shots=[Shot(duration=30, interval_after=60), Shot(duration=45)],
                schedule="0 8 * * *",
                enabled=True
            )
            test_room.add_event(p1_event)
            
            coordinator._rooms = {"test_room": test_room}
            coordinator._settings = {
                "pump_zone_delay": 3,
                "fail_safe_enabled": True,
                "max_daily_irrigation": 3600
            }
            
            return coordinator, test_room

    async def test_complete_p1_irrigation_cycle(self, setup_coordinator_with_room):
        """Test complete P1 irrigation cycle execution."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock entity states as available
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        coordinator.hass.services.async_call = AsyncMock()
        
        # Mock storage operations
        coordinator.storage.async_add_history_event = AsyncMock()
        coordinator.storage.async_record_irrigation_cycle = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        # Mock sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await coordinator.async_execute_irrigation_event("test_room", EVENT_TYPE_P1)
        
        assert result is True
        
        # Verify pump and zone activation calls
        service_calls = coordinator.hass.services.async_call.call_args_list
        
        # Should have calls to turn on pump, turn on zones, turn off zones, turn off pump
        # For 2 shots: 2 * (pump on + zones on + zones off + pump off) = 8 calls
        assert len(service_calls) >= 8
        
        # Verify history and metrics recording
        coordinator.storage.async_add_history_event.assert_called_once()
        coordinator.storage.async_record_irrigation_cycle.assert_called_once_with(True, 135)  # 30+45+60

    async def test_irrigation_cycle_with_fail_safe_trigger(self, setup_coordinator_with_room):
        """Test irrigation cycle blocked by fail-safe."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock light entity as off (fail-safe trigger)
        def mock_get_state(entity_id):
            if entity_id == "light.test_light":
                return MagicMock(state="off")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        coordinator.storage.async_add_history_event = AsyncMock()
        
        result = await coordinator.async_execute_irrigation_event("test_room", EVENT_TYPE_P1)
        
        assert result is False
        
        # Verify failure was recorded
        coordinator.storage.async_add_history_event.assert_called_once()
        call_args = coordinator.storage.async_add_history_event.call_args[0]
        assert call_args[3] is False  # success=False
        assert "lights are off" in call_args[4]  # error message

    async def test_irrigation_cycle_entity_unavailable(self, setup_coordinator_with_room):
        """Test irrigation cycle with unavailable entities."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock pump entity as unavailable
        def mock_get_state(entity_id):
            if entity_id == "switch.test_pump":
                return MagicMock(state="unavailable")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        coordinator.storage.async_add_history_event = AsyncMock()
        
        result = await coordinator.async_execute_irrigation_event("test_room", EVENT_TYPE_P1)
        
        assert result is False
        
        # Verify failure was recorded with appropriate error
        coordinator.storage.async_add_history_event.assert_called_once()
        call_args = coordinator.storage.async_add_history_event.call_args[0]
        assert call_args[3] is False  # success=False
        assert "Unavailable entities" in call_args[4]

    async def test_manual_run_complete_cycle(self, setup_coordinator_with_room):
        """Test complete manual run cycle."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock entity states and services
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        coordinator.hass.services.async_call = AsyncMock()
        coordinator.storage.async_add_history_event = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        # Mock time tracking
        with patch('custom_components.irrigation_addon.coordinator.async_track_point_in_time') as mock_track:
            mock_track.return_value = MagicMock()  # Cancel callback
            
            result = await coordinator.async_start_manual_run("test_room", 300)
        
        assert result is True
        assert "test_room" in coordinator._manual_runs
        
        # Verify pump and zones were activated
        service_calls = coordinator.hass.services.async_call.call_args_list
        assert len(service_calls) >= 3  # pump on + zones on
        
        # Test stopping manual run
        result = await coordinator.async_stop_manual_run("test_room")
        assert result is True
        assert "test_room" not in coordinator._manual_runs

    async def test_emergency_stop_during_irrigation(self, setup_coordinator_with_room):
        """Test emergency stop during active irrigation."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Setup active irrigation state
        coordinator._active_irrigations["test_room"] = {
            "event_type": EVENT_TYPE_P1,
            "current_shot": 0,
            "total_shots": 2
        }
        
        # Mock services
        coordinator.hass.services.async_call = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        
        result = await coordinator.async_emergency_stop_room("test_room")
        
        assert result is True
        assert "test_room" not in coordinator._active_irrigations
        
        # Verify all devices were turned off
        service_calls = coordinator.hass.services.async_call.call_args_list
        turn_off_calls = [call for call in service_calls if call[0][1] == "turn_off"]
        assert len(turn_off_calls) >= 3  # pump + 2 zones


class TestHomeAssistantEntityIntegration:
    """Test integration with Home Assistant entities."""

    @pytest.fixture
    def mock_entity_registry(self):
        """Create a mock entity registry."""
        registry = MagicMock()
        registry.async_get = MagicMock()
        return registry

    async def test_room_entity_validation_success(self, mock_hass_with_services, mock_entity_registry):
        """Test successful room entity validation."""
        # Mock entities exist in registry
        mock_entity_registry.async_get.return_value = MagicMock()
        
        with patch('custom_components.irrigation_addon.models.er.async_get', return_value=mock_entity_registry):
            room = Room(
                room_id="test_room",
                name="Test Room",
                pump_entity="switch.test_pump",
                zone_entities=["switch.test_zone1"],
                light_entity="light.test_light",
                sensors={"soil_rh": "sensor.test_moisture"}
            )
            
            missing_entities = await room.validate_entities_exist(mock_hass_with_services)
            
            assert missing_entities == []

    async def test_room_entity_validation_missing_entities(self, mock_hass_with_services, mock_entity_registry):
        """Test room entity validation with missing entities."""
        # Mock some entities missing from registry
        def mock_async_get(entity_id):
            if entity_id == "switch.missing_pump":
                return None
            return MagicMock()
        
        mock_entity_registry.async_get.side_effect = mock_async_get
        mock_hass_with_services.states.async_entity_ids.return_value = []
        
        with patch('custom_components.irrigation_addon.models.er.async_get', return_value=mock_entity_registry):
            room = Room(
                room_id="test_room",
                name="Test Room",
                pump_entity="switch.missing_pump",
                zone_entities=["switch.test_zone1"],
                sensors={"soil_rh": "sensor.test_moisture"}
            )
            
            missing_entities = await room.validate_entities_exist(mock_hass_with_services)
            
            assert len(missing_entities) > 0
            assert any("missing_pump" in entity for entity in missing_entities)

    async def test_sensor_data_collection(self, setup_coordinator_with_room):
        """Test sensor data collection from Home Assistant."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock sensor states
        def mock_get_state(entity_id):
            if entity_id == "sensor.test_moisture":
                state = MagicMock()
                state.state = "45.2"
                state.attributes = {"unit_of_measurement": "%"}
                state.last_updated = datetime.now()
                return state
            elif entity_id == "sensor.test_temp":
                state = MagicMock()
                state.state = "24.5"
                state.attributes = {"unit_of_measurement": "°C"}
                state.last_updated = datetime.now()
                return state
            return MagicMock(state="unknown")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        
        data = await coordinator._async_update_data()
        
        assert "sensor_data" in data
        assert "test_room" in data["sensor_data"]
        
        room_sensors = data["sensor_data"]["test_room"]
        assert room_sensors["soil_rh"]["value"] == 45.2
        assert room_sensors["temperature"]["value"] == 24.5
        assert room_sensors["soil_rh"]["unit"] == "%"
        assert room_sensors["temperature"]["unit"] == "°C"

    async def test_sensor_data_unavailable_handling(self, setup_coordinator_with_room):
        """Test handling of unavailable sensor data."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock sensors as unavailable
        def mock_get_state(entity_id):
            if "sensor" in entity_id:
                return MagicMock(state="unavailable")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        
        data = await coordinator._async_update_data()
        
        room_sensors = data["sensor_data"]["test_room"]
        assert room_sensors["soil_rh"]["unavailable"] is True
        assert room_sensors["temperature"]["unavailable"] is True
        assert room_sensors["soil_rh"]["value"] is None


class TestFailSafeScenarios:
    """Test various fail-safe scenarios."""

    @pytest.fixture
    async def coordinator_with_fail_safes(self, mock_hass_with_services, mock_config_entry_full):
        """Setup coordinator with fail-safe settings."""
        with patch('custom_components.irrigation_addon.coordinator.IrrigationStorage'):
            coordinator = IrrigationCoordinator(mock_hass_with_services, mock_config_entry_full)
            coordinator.storage = AsyncMock()
            
            test_room = Room(
                room_id="test_room",
                name="Test Room",
                pump_entity="switch.test_pump",
                zone_entities=["switch.test_zone1"],
                light_entity="light.test_light",
                sensors={"soil_rh": "sensor.test_moisture"}
            )
            
            coordinator._rooms = {"test_room": test_room}
            coordinator._settings = {
                "fail_safe_enabled": True,
                "max_daily_irrigation": 1800,  # 30 minutes
                "pump_zone_delay": 3
            }
            
            return coordinator, test_room

    async def test_daily_limit_enforcement(self, coordinator_with_fail_safes):
        """Test daily irrigation limit enforcement."""
        coordinator, test_room = coordinator_with_fail_safes
        
        # Set daily total near limit
        coordinator._daily_irrigation_totals["test_room"] = 1700  # 100 seconds under limit
        
        # Mock entities as available
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        
        # Test request that would exceed limit
        result = await coordinator._check_fail_safes("test_room", 200)  # Would exceed by 100s
        
        assert result["allowed"] is False
        assert "Daily irrigation limit exceeded" in result["reason"]

    async def test_daily_limit_within_bounds(self, coordinator_with_fail_safes):
        """Test irrigation allowed within daily limits."""
        coordinator, test_room = coordinator_with_fail_safes
        
        # Set daily total well under limit
        coordinator._daily_irrigation_totals["test_room"] = 600  # 10 minutes used
        
        # Mock entities as available
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        
        # Test request within limit
        result = await coordinator._check_fail_safes("test_room", 300)  # 5 more minutes
        
        assert result["allowed"] is True

    async def test_light_schedule_integration(self, coordinator_with_fail_safes):
        """Test light schedule integration scenarios."""
        coordinator, test_room = coordinator_with_fail_safes
        
        # Test with lights on (should allow)
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        result = await coordinator._check_fail_safes("test_room", 300)
        assert result["allowed"] is True
        
        # Test with lights off (should block)
        def mock_get_state(entity_id):
            if entity_id == "light.test_light":
                return MagicMock(state="off")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        result = await coordinator._check_fail_safes("test_room", 300)
        assert result["allowed"] is False
        assert "lights are off" in result["reason"]

    async def test_concurrent_irrigation_prevention(self, coordinator_with_fail_safes):
        """Test prevention of concurrent irrigation operations."""
        coordinator, test_room = coordinator_with_fail_safes
        
        # Mock entities as available
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        
        # Set up active irrigation
        coordinator._active_irrigations["test_room"] = {"event_type": EVENT_TYPE_P1}
        
        result = await coordinator._check_fail_safes("test_room", 300)
        
        assert result["allowed"] is False
        assert "already active" in result["reason"]

    async def test_fail_safe_disabled(self, coordinator_with_fail_safes):
        """Test behavior when fail-safes are disabled."""
        coordinator, test_room = coordinator_with_fail_safes
        
        # Disable fail-safes
        coordinator._settings["fail_safe_enabled"] = False
        
        # Set up conditions that would normally trigger fail-safes
        coordinator._daily_irrigation_totals["test_room"] = 2000  # Over limit
        coordinator.hass.states.get.return_value = MagicMock(state="off")  # Lights off
        
        result = await coordinator._check_fail_safes("test_room", 300)
        
        assert result["allowed"] is True  # Should allow when disabled


class TestSystemHealthMonitoring:
    """Test system health monitoring and diagnostics."""

    async def test_system_health_healthy_state(self, setup_coordinator_with_room):
        """Test system health in healthy state."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Setup healthy state
        coordinator._daily_irrigation_totals = {"test_room": 1000}
        coordinator._settings["max_daily_irrigation"] = 3600
        
        health = coordinator.get_system_health()
        
        assert health["status"] == "healthy"
        assert health["rooms_count"] == 1
        assert health["active_irrigations"] == 0
        assert health["fail_safe_enabled"] is True
        assert len(health["issues"]) == 0

    async def test_system_health_with_warnings(self, setup_coordinator_with_room):
        """Test system health with warning conditions."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Setup warning conditions
        coordinator._daily_irrigation_totals = {"test_room": 3600}  # At daily limit
        coordinator._settings["max_daily_irrigation"] = 3600
        
        health = coordinator.get_system_health()
        
        assert health["status"] == "warning"
        assert len(health["issues"]) > 0
        assert any("Daily limit reached" in issue for issue in health["issues"])

    async def test_room_safety_validation(self, setup_coordinator_with_room):
        """Test room safety validation."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock entity validation
        test_room.validate_entities_exist = AsyncMock(return_value=[])
        coordinator.hass.states.get.return_value = MagicMock(state="on")
        coordinator._daily_irrigation_totals = {"test_room": 1000}
        coordinator._settings["max_daily_irrigation"] = 3600
        
        validation = await coordinator.async_validate_room_safety("test_room")
        
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["daily_usage"] == 1000
        assert validation["remaining_daily"] == 2600

    async def test_room_safety_validation_with_issues(self, setup_coordinator_with_room):
        """Test room safety validation with issues."""
        coordinator, test_room = setup_coordinator_with_room
        
        # Mock missing entities
        test_room.validate_entities_exist = AsyncMock(return_value=["switch.missing_pump"])
        
        # Mock light entity unavailable
        def mock_get_state(entity_id):
            if entity_id == "light.test_light":
                return MagicMock(state="unavailable")
            return MagicMock(state="on")
        
        coordinator.hass.states.get.side_effect = mock_get_state
        coordinator._daily_irrigation_totals = {"test_room": 3600}  # At limit
        coordinator._settings["max_daily_irrigation"] = 3600
        
        validation = await coordinator.async_validate_room_safety("test_room")
        
        assert validation["valid"] is False
        assert len(validation["issues"]) >= 3  # Missing entity, unavailable light, daily limit
        assert validation["remaining_daily"] == 0