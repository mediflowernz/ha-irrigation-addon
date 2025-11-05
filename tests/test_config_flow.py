"""Test configuration flow functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.irrigation_addon.config_flow import IrrigationAddonConfigFlow
from custom_components.irrigation_addon.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    return hass


class TestIrrigationAddonConfigFlow:
    """Test the config flow."""

    async def test_form_user_step(self):
        """Test the user step form."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        
        result = await flow.async_step_user()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "name" in result["data_schema"].schema

    async def test_form_user_step_with_input(self):
        """Test the user step with valid input."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = MagicMock()
        flow._abort_if_unique_id_configured = MagicMock()
        
        user_input = {"name": "Test Irrigation System"}
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "settings"
        assert flow._name == "Test Irrigation System"

    async def test_form_settings_step(self):
        """Test the settings step form."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        flow._name = "Test System"
        
        result = await flow.async_step_settings()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "settings"
        assert "pump_zone_delay" in result["data_schema"].schema
        assert "sensor_update_interval" in result["data_schema"].schema
        assert "fail_safe_enabled" in result["data_schema"].schema

    async def test_form_settings_step_with_input(self):
        """Test the settings step with valid input."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        flow._name = "Test System"
        
        settings_input = {
            "pump_zone_delay": 5,
            "sensor_update_interval": 60,
            "default_manual_duration": 600,
            "fail_safe_enabled": True
        }
        
        result = await flow.async_step_settings(settings_input)
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "confirm"
        assert flow._settings == settings_input

    async def test_form_confirm_step(self):
        """Test the confirmation step."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        flow._name = "Test System"
        flow._settings = {"pump_zone_delay": 3}
        
        result = await flow.async_step_confirm()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "confirm"
        assert "Test System" in result["description_placeholders"]["name"]

    async def test_form_confirm_step_create_entry(self):
        """Test creating entry from confirmation step."""
        flow = IrrigationAddonConfigFlow()
        flow.hass = MagicMock()
        flow._name = "Test System"
        flow._settings = {"pump_zone_delay": 3, "fail_safe_enabled": True}
        
        result = await flow.async_step_confirm({"confirm": True})
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test System"
        assert result["data"]["name"] == "Test System"
        assert result["data"]["settings"]["pump_zone_delay"] == 3
        assert result["data"]["settings"]["fail_safe_enabled"] is True

    async def test_options_flow_init(self, mock_hass):
        """Test options flow initialization."""
        config_entry = MagicMock()
        config_entry.data = {"settings": {"pump_zone_delay": 3}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        
        result = await options_flow.async_step_init()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "settings"

    async def test_options_flow_settings_update(self, mock_hass):
        """Test updating settings through options flow."""
        config_entry = MagicMock()
        config_entry.data = {"settings": {"pump_zone_delay": 3, "fail_safe_enabled": True}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        
        new_settings = {
            "pump_zone_delay": 5,
            "sensor_update_interval": 45,
            "fail_safe_enabled": False
        }
        
        result = await options_flow.async_step_settings(new_settings)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["settings"]["pump_zone_delay"] == 5
        assert result["data"]["settings"]["sensor_update_interval"] == 45
        assert result["data"]["settings"]["fail_safe_enabled"] is False

    @patch('custom_components.irrigation_addon.config_flow._validate_entity_exists')
    async def test_add_room_valid_entities(self, mock_validate, mock_hass):
        """Test adding a room with valid entities."""
        mock_validate.return_value = True
        
        config_entry = MagicMock()
        config_entry.data = {"settings": {}}
        
        # Mock coordinator and storage
        mock_coordinator = MagicMock()
        mock_coordinator.storage = MagicMock()
        mock_coordinator.storage.get_rooms.return_value = {}
        mock_coordinator.storage.add_room = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        
        mock_hass.data = {DOMAIN: {config_entry.entry_id: mock_coordinator}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        
        with patch('custom_components.irrigation_addon.config_flow._get_entities_by_domain') as mock_get_entities:
            mock_get_entities.return_value = ["switch.pump1", "switch.zone1"]
            
            room_input = {
                "room_name": "Test Room",
                "pump_entity": "switch.pump1",
                "zone_entities": ["switch.zone1"],
                "light_entity": "light.grow_light",
                "soil_rh_sensor": "sensor.moisture"
            }
            
            result = await options_flow.async_step_add_room(room_input)
            
            assert result["type"] == FlowResultType.CREATE_ENTRY
            mock_coordinator.storage.add_room.assert_called_once()

    @patch('custom_components.irrigation_addon.config_flow._validate_entity_exists')
    async def test_add_room_invalid_pump_entity(self, mock_validate, mock_hass):
        """Test adding a room with invalid pump entity."""
        def validate_side_effect(hass, entity_id):
            return entity_id != "switch.invalid_pump"
        
        mock_validate.side_effect = validate_side_effect
        
        config_entry = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator.storage = MagicMock()
        mock_coordinator.storage.get_rooms.return_value = {}
        
        mock_hass.data = {DOMAIN: {config_entry.entry_id: mock_coordinator}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        
        with patch('custom_components.irrigation_addon.config_flow._get_entities_by_domain') as mock_get_entities:
            mock_get_entities.return_value = ["switch.pump1", "switch.zone1"]
            
            room_input = {
                "room_name": "Test Room",
                "pump_entity": "switch.invalid_pump",
                "zone_entities": ["switch.zone1"]
            }
            
            result = await options_flow.async_step_add_room(room_input)
            
            assert result["type"] == FlowResultType.FORM
            assert "invalid_pump_entity" in result["errors"]["pump_entity"]

    async def test_add_room_duplicate_name(self, mock_hass):
        """Test adding a room with duplicate name."""
        config_entry = MagicMock()
        
        # Mock existing room
        existing_room = MagicMock()
        existing_room.name = "Test Room"
        
        mock_coordinator = MagicMock()
        mock_coordinator.storage = MagicMock()
        mock_coordinator.storage.get_rooms.return_value = {"room1": existing_room}
        
        mock_hass.data = {DOMAIN: {config_entry.entry_id: mock_coordinator}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        
        with patch('custom_components.irrigation_addon.config_flow._get_entities_by_domain') as mock_get_entities:
            mock_get_entities.return_value = ["switch.pump1"]
            
            room_input = {
                "room_name": "Test Room",  # Duplicate name
                "pump_entity": "switch.pump1"
            }
            
            result = await options_flow.async_step_add_room(room_input)
            
            assert result["type"] == FlowResultType.FORM
            assert "duplicate_room" in result["errors"]["room_name"]

    async def test_delete_room_confirmation(self, mock_hass):
        """Test room deletion with confirmation."""
        config_entry = MagicMock()
        
        # Mock existing room
        existing_room = MagicMock()
        existing_room.name = "Test Room"
        
        mock_coordinator = MagicMock()
        mock_coordinator.storage = MagicMock()
        mock_coordinator.storage.get_rooms.return_value = {"room1": existing_room}
        mock_coordinator.storage.delete_room = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        
        mock_hass.data = {DOMAIN: {config_entry.entry_id: mock_coordinator}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        options_flow._selected_room_id = "room1"
        
        # Test confirmation step
        result = await options_flow.async_step_delete_room()
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "delete_room"
        
        # Test actual deletion
        result = await options_flow.async_step_delete_room({"confirm_delete": True})
        assert result["type"] == FlowResultType.CREATE_ENTRY
        mock_coordinator.storage.delete_room.assert_called_once_with("room1")

    async def test_delete_room_cancel(self, mock_hass):
        """Test room deletion cancellation."""
        config_entry = MagicMock()
        
        existing_room = MagicMock()
        existing_room.name = "Test Room"
        
        mock_coordinator = MagicMock()
        mock_coordinator.storage = MagicMock()
        mock_coordinator.storage.get_rooms.return_value = {"room1": existing_room}
        
        mock_hass.data = {DOMAIN: {config_entry.entry_id: mock_coordinator}}
        
        from custom_components.irrigation_addon.config_flow import IrrigationAddonOptionsFlow
        options_flow = IrrigationAddonOptionsFlow(config_entry)
        options_flow.hass = mock_hass
        options_flow._selected_room_id = "room1"
        
        # Mock async_step_rooms to return a form
        options_flow.async_step_rooms = AsyncMock(return_value={
            "type": FlowResultType.FORM,
            "step_id": "rooms"
        })
        
        result = await options_flow.async_step_delete_room({"confirm_delete": False})
        
        # Should return to rooms step
        options_flow.async_step_rooms.assert_called_once()


class TestConfigFlowHelpers:
    """Test config flow helper functions."""

    @patch('custom_components.irrigation_addon.config_flow.async_get_entity_registry')
    async def test_validate_entity_exists_in_registry(self, mock_get_registry):
        """Test entity validation when entity exists in registry."""
        mock_registry = MagicMock()
        mock_registry.async_get.return_value = MagicMock()  # Entity exists
        mock_get_registry.return_value = mock_registry
        
        mock_hass = MagicMock()
        
        from custom_components.irrigation_addon.config_flow import _validate_entity_exists
        result = await _validate_entity_exists(mock_hass, "switch.test")
        
        assert result is True
        mock_registry.async_get.assert_called_once_with("switch.test")

    @patch('custom_components.irrigation_addon.config_flow.async_get_entity_registry')
    async def test_validate_entity_exists_in_states(self, mock_get_registry):
        """Test entity validation when entity exists in states."""
        mock_registry = MagicMock()
        mock_registry.async_get.return_value = None  # Not in registry
        mock_get_registry.return_value = mock_registry
        
        mock_hass = MagicMock()
        mock_hass.states.get.return_value = MagicMock()  # Exists in states
        
        from custom_components.irrigation_addon.config_flow import _validate_entity_exists
        result = await _validate_entity_exists(mock_hass, "switch.test")
        
        assert result is True
        mock_hass.states.get.assert_called_once_with("switch.test")

    @patch('custom_components.irrigation_addon.config_flow.async_get_entity_registry')
    async def test_validate_entity_not_exists(self, mock_get_registry):
        """Test entity validation when entity doesn't exist."""
        mock_registry = MagicMock()
        mock_registry.async_get.return_value = None  # Not in registry
        mock_get_registry.return_value = mock_registry
        
        mock_hass = MagicMock()
        mock_hass.states.get.return_value = None  # Not in states
        
        from custom_components.irrigation_addon.config_flow import _validate_entity_exists
        result = await _validate_entity_exists(mock_hass, "switch.test")
        
        assert result is False

    @patch('custom_components.irrigation_addon.config_flow.async_get_entity_registry')
    async def test_get_entities_by_domain(self, mock_get_registry):
        """Test getting entities by domain."""
        # Mock registry entities
        mock_entity1 = MagicMock()
        mock_entity1.entity_id = "switch.pump1"
        mock_entity2 = MagicMock()
        mock_entity2.entity_id = "switch.zone1"
        mock_entity3 = MagicMock()
        mock_entity3.entity_id = "light.grow_light"
        
        mock_registry = MagicMock()
        mock_registry.entities.values.return_value = [mock_entity1, mock_entity2, mock_entity3]
        mock_get_registry.return_value = mock_registry
        
        mock_hass = MagicMock()
        mock_hass.states.async_entity_ids.return_value = ["switch.extra_switch"]
        
        from custom_components.irrigation_addon.config_flow import _get_entities_by_domain
        result = await _get_entities_by_domain(mock_hass, "switch")
        
        assert "switch.pump1" in result
        assert "switch.zone1" in result
        assert "switch.extra_switch" in result
        assert "light.grow_light" not in result
        assert len([e for e in result if e.startswith("switch.")]) == 3