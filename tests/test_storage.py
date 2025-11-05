"""Test storage functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.irrigation_addon.storage import IrrigationStorage
from custom_components.irrigation_addon.models import Room, IrrigationEvent, Shot
from custom_components.irrigation_addon.const import EVENT_TYPE_P1, STORAGE_VERSION


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def sample_room_data():
    """Create sample room data for testing."""
    return {
        "room_id": "room1",
        "name": "Test Room",
        "pump_entity": "switch.pump1",
        "zone_entities": ["switch.zone1", "switch.zone2"],
        "light_entity": "light.grow_light",
        "sensors": {"soil_rh": "sensor.moisture", "temperature": "sensor.temp"},
        "events": []
    }


class TestIrrigationStorage:
    """Test IrrigationStorage functionality."""

    @pytest.fixture
    async def storage(self, mock_hass):
        """Create a storage instance for testing."""
        with patch('custom_components.irrigation_addon.storage.Store') as mock_store_class:
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store
            
            storage = IrrigationStorage(mock_hass)
            storage._store = mock_store
            return storage

    async def test_storage_initialization(self, storage, mock_hass):
        """Test storage initialization."""
        assert storage.hass == mock_hass
        assert storage._loaded is False
        assert storage._data == {}

    async def test_async_load_new_installation(self, storage):
        """Test loading storage for new installation."""
        storage._store.async_load.return_value = None
        
        await storage.async_load()
        
        assert storage._loaded is True
        assert storage._data["version"] == STORAGE_VERSION
        assert "rooms" in storage._data
        assert "settings" in storage._data
        assert "history" in storage._data

    async def test_async_load_existing_data(self, storage):
        """Test loading existing storage data."""
        existing_data = {
            "version": STORAGE_VERSION,
            "rooms": {"room1": {"name": "Test Room"}},
            "settings": {"pump_zone_delay": 5}
        }
        storage._store.async_load.return_value = existing_data
        
        await storage.async_load()
        
        assert storage._loaded is True
        assert storage._data == existing_data

    async def test_async_load_error_handling(self, storage):
        """Test error handling during storage load."""
        storage._store.async_load.side_effect = Exception("Load error")
        
        with pytest.raises(HomeAssistantError, match="Failed to load irrigation storage"):
            await storage.async_load()
        
        # Should still be loaded with default data
        assert storage._loaded is True
        assert storage._data["version"] == STORAGE_VERSION

    async def test_async_save_success(self, storage):
        """Test successful storage save."""
        storage._loaded = True
        storage._data = {"test": "data"}
        
        await storage.async_save()
        
        storage._store.async_save.assert_called_once_with({"test": "data"})

    async def test_async_save_not_loaded(self, storage):
        """Test save when storage not loaded."""
        storage._loaded = False
        
        with pytest.raises(HomeAssistantError, match="Storage not loaded"):
            await storage.async_save()

    async def test_async_save_error_handling(self, storage):
        """Test error handling during storage save."""
        storage._loaded = True
        storage._store.async_save.side_effect = Exception("Save error")
        
        with pytest.raises(HomeAssistantError, match="Failed to save irrigation storage"):
            await storage.async_save()

    async def test_get_rooms_not_loaded(self, storage):
        """Test getting rooms when storage not loaded."""
        storage._loaded = False
        
        rooms = storage.get_rooms()
        
        assert rooms == {}

    async def test_get_rooms_with_data(self, storage, sample_room_data):
        """Test getting rooms with valid data."""
        storage._loaded = True
        storage._data = {"rooms": {"room1": sample_room_data}}
        
        rooms = storage.get_rooms()
        
        assert len(rooms) == 1
        assert "room1" in rooms
        assert isinstance(rooms["room1"], Room)
        assert rooms["room1"].name == "Test Room"

    async def test_get_rooms_with_invalid_data(self, storage):
        """Test getting rooms with invalid data."""
        storage._loaded = True
        storage._data = {"rooms": {"room1": {"invalid": "data"}}}
        
        rooms = storage.get_rooms()
        
        assert rooms == {}  # Invalid room data should be skipped

    async def test_async_get_rooms(self, storage, sample_room_data):
        """Test async get rooms."""
        storage._loaded = False
        storage.async_load = AsyncMock()
        storage.get_rooms = MagicMock(return_value={"room1": Room.from_dict(sample_room_data)})
        
        rooms = await storage.async_get_rooms()
        
        storage.async_load.assert_called_once()
        assert len(rooms) == 1

    async def test_async_get_room(self, storage, sample_room_data):
        """Test getting a specific room."""
        storage.async_get_rooms = AsyncMock(return_value={"room1": Room.from_dict(sample_room_data)})
        
        room = await storage.async_get_room("room1")
        
        assert room is not None
        assert room.room_id == "room1"
        assert room.name == "Test Room"

    async def test_async_get_room_not_found(self, storage):
        """Test getting a non-existent room."""
        storage.async_get_rooms = AsyncMock(return_value={})
        
        room = await storage.async_get_room("nonexistent")
        
        assert room is None

    async def test_async_save_room(self, storage, sample_room_data):
        """Test saving a room."""
        storage._loaded = True
        storage._data = {"rooms": {}}
        storage.async_save = AsyncMock()
        
        room = Room.from_dict(sample_room_data)
        await storage.async_save_room(room)
        
        assert "room1" in storage._data["rooms"]
        assert storage._data["rooms"]["room1"]["name"] == "Test Room"
        storage.async_save.assert_called_once()

    async def test_async_save_room_not_loaded(self, storage, sample_room_data):
        """Test saving room when storage not loaded."""
        storage._loaded = False
        storage.async_load = AsyncMock()
        storage.async_save = AsyncMock()
        
        room = Room.from_dict(sample_room_data)
        await storage.async_save_room(room)
        
        storage.async_load.assert_called_once()

    async def test_async_save_room_validation_error(self, storage):
        """Test saving room with validation error."""
        storage._loaded = True
        
        # Create invalid room (missing required fields)
        invalid_room = Room(room_id="", name="Test", pump_entity="switch.pump1")
        
        with pytest.raises(HomeAssistantError, match="Failed to save room"):
            await storage.async_save_room(invalid_room)

    async def test_add_room(self, storage, sample_room_data):
        """Test adding a new room."""
        storage._loaded = True
        storage._data = {"rooms": {}}
        storage.async_save = AsyncMock()
        
        # Remove room_id from data as it should be generated
        room_data = sample_room_data.copy()
        del room_data["room_id"]
        
        room_id = await storage.add_room(room_data)
        
        assert room_id is not None
        assert len(room_id) == 8  # UUID prefix length
        assert room_id in storage._data["rooms"]
        storage.async_save.assert_called_once()

    async def test_update_room(self, storage, sample_room_data):
        """Test updating an existing room."""
        storage._loaded = True
        storage._data = {"rooms": {"room1": sample_room_data.copy()}}
        storage.async_save = AsyncMock()
        
        updated_data = sample_room_data.copy()
        updated_data["name"] = "Updated Room"
        del updated_data["room_id"]  # Should be set by function
        
        await storage.update_room("room1", updated_data)
        
        assert storage._data["rooms"]["room1"]["name"] == "Updated Room"
        storage.async_save.assert_called_once()

    async def test_update_room_not_found(self, storage):
        """Test updating a non-existent room."""
        storage._loaded = True
        storage._data = {"rooms": {}}
        
        with pytest.raises(HomeAssistantError, match="Room nonexistent not found"):
            await storage.update_room("nonexistent", {"name": "Test"})

    async def test_async_delete_room(self, storage, sample_room_data):
        """Test deleting a room."""
        storage._loaded = True
        storage._data = {"rooms": {"room1": sample_room_data}}
        storage.async_save = AsyncMock()
        
        result = await storage.async_delete_room("room1")
        
        assert result is True
        assert "room1" not in storage._data["rooms"]
        storage.async_save.assert_called_once()

    async def test_async_delete_room_not_found(self, storage):
        """Test deleting a non-existent room."""
        storage._loaded = True
        storage._data = {"rooms": {}}
        
        result = await storage.async_delete_room("nonexistent")
        
        assert result is False

    async def test_async_get_settings(self, storage):
        """Test getting settings."""
        storage._loaded = True
        storage._data = {"settings": {"pump_zone_delay": 5, "fail_safe_enabled": True}}
        
        settings = await storage.async_get_settings()
        
        assert settings["pump_zone_delay"] == 5
        assert settings["fail_safe_enabled"] is True

    async def test_async_update_settings(self, storage):
        """Test updating settings."""
        storage._loaded = True
        storage._data = {"settings": {"pump_zone_delay": 3}}
        storage.async_save = AsyncMock()
        
        new_settings = {"pump_zone_delay": 5, "fail_safe_enabled": False}
        await storage.async_update_settings(new_settings)
        
        assert storage._data["settings"]["pump_zone_delay"] == 5
        assert storage._data["settings"]["fail_safe_enabled"] is False
        storage.async_save.assert_called_once()

    async def test_validate_settings_valid(self, storage):
        """Test settings validation with valid values."""
        valid_settings = {
            "pump_zone_delay": 5,
            "sensor_update_interval": 60,
            "default_manual_duration": 600,
            "max_daily_irrigation": 7200,
            "logging_level": "INFO",
            "fail_safe_enabled": True
        }
        
        # Should not raise any exception
        storage._validate_settings(valid_settings)

    async def test_validate_settings_invalid_pump_delay(self, storage):
        """Test settings validation with invalid pump delay."""
        invalid_settings = {"pump_zone_delay": -1}
        
        with pytest.raises(ValueError, match="pump_zone_delay must be between 0 and 60"):
            storage._validate_settings(invalid_settings)

    async def test_validate_settings_invalid_sensor_interval(self, storage):
        """Test settings validation with invalid sensor interval."""
        invalid_settings = {"sensor_update_interval": 400}
        
        with pytest.raises(ValueError, match="sensor_update_interval must be between 5 and 300"):
            storage._validate_settings(invalid_settings)

    async def test_validate_settings_invalid_logging_level(self, storage):
        """Test settings validation with invalid logging level."""
        invalid_settings = {"logging_level": "INVALID"}
        
        with pytest.raises(ValueError, match="logging_level must be one of"):
            storage._validate_settings(invalid_settings)

    async def test_async_add_history_event(self, storage):
        """Test adding a history event."""
        storage._loaded = True
        storage._data = {"history": {"events": [], "max_history_days": 30}}
        storage._async_clean_history = AsyncMock()
        storage.async_save = AsyncMock()
        
        await storage.async_add_history_event("room1", EVENT_TYPE_P1, 300, True)
        
        assert len(storage._data["history"]["events"]) == 1
        event = storage._data["history"]["events"][0]
        assert event["room_id"] == "room1"
        assert event["event_type"] == EVENT_TYPE_P1
        assert event["duration"] == 300
        assert event["success"] is True
        storage._async_clean_history.assert_called_once()
        storage.async_save.assert_called_once()

    async def test_async_get_history_all_rooms(self, storage):
        """Test getting history for all rooms."""
        now = datetime.now()
        storage._loaded = True
        storage._data = {
            "history": {
                "events": [
                    {
                        "timestamp": now.isoformat(),
                        "room_id": "room1",
                        "event_type": EVENT_TYPE_P1,
                        "duration": 300,
                        "success": True
                    },
                    {
                        "timestamp": (now - timedelta(days=10)).isoformat(),
                        "room_id": "room2",
                        "event_type": EVENT_TYPE_P1,
                        "duration": 250,
                        "success": False
                    }
                ]
            }
        }
        
        history = await storage.async_get_history(days=7)
        
        # Should only return events from last 7 days
        assert len(history) == 1
        assert history[0]["room_id"] == "room1"

    async def test_async_get_history_specific_room(self, storage):
        """Test getting history for a specific room."""
        now = datetime.now()
        storage._loaded = True
        storage._data = {
            "history": {
                "events": [
                    {
                        "timestamp": now.isoformat(),
                        "room_id": "room1",
                        "event_type": EVENT_TYPE_P1,
                        "duration": 300,
                        "success": True
                    },
                    {
                        "timestamp": now.isoformat(),
                        "room_id": "room2",
                        "event_type": EVENT_TYPE_P1,
                        "duration": 250,
                        "success": True
                    }
                ]
            }
        }
        
        history = await storage.async_get_history(room_id="room1")
        
        assert len(history) == 1
        assert history[0]["room_id"] == "room1"

    async def test_async_record_irrigation_cycle_success(self, storage):
        """Test recording successful irrigation cycle."""
        storage._loaded = True
        storage._data = {
            "performance_metrics": {
                "irrigation_cycles": {
                    "total_attempts": 5,
                    "successful_cycles": 4,
                    "failed_cycles": 1,
                    "total_duration": 1200,
                    "average_duration": 300
                }
            }
        }
        storage.async_save = AsyncMock()
        
        await storage.async_record_irrigation_cycle(True, 350)
        
        metrics = storage._data["performance_metrics"]["irrigation_cycles"]
        assert metrics["total_attempts"] == 6
        assert metrics["successful_cycles"] == 5
        assert metrics["failed_cycles"] == 1
        assert metrics["total_duration"] == 1550
        assert metrics["average_duration"] == 310  # 1550 / 5

    async def test_async_record_irrigation_cycle_failure(self, storage):
        """Test recording failed irrigation cycle."""
        storage._loaded = True
        storage._data = {
            "performance_metrics": {
                "irrigation_cycles": {
                    "total_attempts": 5,
                    "successful_cycles": 4,
                    "failed_cycles": 1,
                    "total_duration": 1200,
                    "average_duration": 300
                }
            }
        }
        storage.async_save = AsyncMock()
        
        await storage.async_record_irrigation_cycle(False, 0)
        
        metrics = storage._data["performance_metrics"]["irrigation_cycles"]
        assert metrics["total_attempts"] == 6
        assert metrics["successful_cycles"] == 4
        assert metrics["failed_cycles"] == 2
        assert metrics["total_duration"] == 1200  # No change for failed cycle
        assert metrics["average_duration"] == 300  # No change

    async def test_async_get_performance_metrics(self, storage):
        """Test getting performance metrics."""
        storage._loaded = True
        storage._data = {
            "performance_metrics": {
                "irrigation_cycles": {
                    "total_attempts": 10,
                    "successful_cycles": 8,
                    "failed_cycles": 2,
                    "total_duration": 2400,
                    "average_duration": 300
                },
                "system_health": {
                    "uptime_start": datetime.now().isoformat(),
                    "error_count": 3
                }
            }
        }
        
        metrics = await storage.async_get_performance_metrics()
        
        assert metrics["irrigation_cycles"]["success_rate"] == 80.0  # 8/10 * 100
        assert metrics["irrigation_cycles"]["total_attempts"] == 10
        assert "uptime_seconds" in metrics["system_health"]
        assert "uptime_hours" in metrics["system_health"]

    async def test_async_create_backup(self, storage):
        """Test creating a backup."""
        storage._loaded = True
        storage._data = {"test": "data", "version": STORAGE_VERSION}
        
        backup = await storage.async_create_backup()
        
        assert "backup_timestamp" in backup
        assert backup["version"] == STORAGE_VERSION
        assert backup["data"]["test"] == "data"

    async def test_async_restore_backup(self, storage):
        """Test restoring from backup."""
        storage._loaded = False
        storage.async_save = AsyncMock()
        
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "version": STORAGE_VERSION,
            "data": {
                "rooms": {"room1": {"name": "Test Room"}},
                "settings": {"pump_zone_delay": 5}
            }
        }
        
        await storage.async_restore_backup(backup_data)
        
        assert storage._loaded is True
        assert storage._data["rooms"]["room1"]["name"] == "Test Room"
        assert storage._data["settings"]["pump_zone_delay"] == 5
        storage.async_save.assert_called_once()

    async def test_async_restore_backup_invalid_data(self, storage):
        """Test restoring from invalid backup."""
        invalid_backup = {"invalid": "backup"}
        
        with pytest.raises(HomeAssistantError, match="Invalid backup data"):
            await storage.async_restore_backup(invalid_backup)

    async def test_async_export_data(self, storage):
        """Test exporting data as JSON."""
        storage.async_create_backup = AsyncMock(return_value={"test": "backup"})
        
        json_data = await storage.async_export_data()
        
        assert isinstance(json_data, str)
        assert "test" in json_data
        assert "backup" in json_data

    async def test_async_import_data(self, storage):
        """Test importing data from JSON."""
        storage.async_restore_backup = AsyncMock()
        
        json_data = '{"data": {"test": "imported"}}'
        await storage.async_import_data(json_data)
        
        storage.async_restore_backup.assert_called_once()

    async def test_async_import_data_invalid_json(self, storage):
        """Test importing invalid JSON data."""
        invalid_json = "invalid json"
        
        with pytest.raises(HomeAssistantError, match="Invalid JSON data"):
            await storage.async_import_data(invalid_json)

    async def test_async_reset_data(self, storage):
        """Test resetting all data to defaults."""
        storage._data = {"existing": "data"}
        storage.async_save = AsyncMock()
        
        await storage.async_reset_data()
        
        assert storage._data["version"] == STORAGE_VERSION
        assert "rooms" in storage._data
        assert "settings" in storage._data
        assert "existing" not in storage._data
        storage.async_save.assert_called_once()