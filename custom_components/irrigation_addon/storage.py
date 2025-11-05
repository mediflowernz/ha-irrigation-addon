"""Storage handler for the Irrigation Addon integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    DEFAULT_PUMP_ZONE_DELAY,
    DEFAULT_SENSOR_UPDATE_INTERVAL,
    DEFAULT_MANUAL_DURATION,
    DEFAULT_FAIL_SAFE_ENABLED,
    DEFAULT_EMERGENCY_STOP_ENABLED,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_ERROR_NOTIFICATIONS,
    DEFAULT_LOGGING_LEVEL,
    DEFAULT_MAX_HISTORY_DAYS,
    DEFAULT_MAX_DAILY_IRRIGATION
)
from .models import Room, IrrigationEvent, Shot

_LOGGER = logging.getLogger(__name__)


class IrrigationStorage:
    """Handle storage operations for irrigation data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage handler."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, Any] = {}
        self._loaded = False

    async def async_load(self) -> None:
        """Load data from storage."""
        try:
            stored_data = await self._store.async_load()
            if stored_data is None:
                _LOGGER.info("No existing storage data found, initializing with defaults")
                self._data = self._get_default_data()
            else:
                _LOGGER.debug("Loading existing storage data")
                self._data = stored_data
                
                # Perform migration if needed
                await self._async_migrate_data()
            
            self._loaded = True
            _LOGGER.debug("Storage data loaded successfully")
            
        except Exception as e:
            _LOGGER.error("Failed to load storage data: %s", e)
            self._data = self._get_default_data()
            self._loaded = True
            raise HomeAssistantError(f"Failed to load irrigation storage: {e}")

    async def async_save(self) -> None:
        """Save data to storage."""
        if not self._loaded:
            raise HomeAssistantError("Storage not loaded, cannot save data")
        
        try:
            await self._store.async_save(self._data)
            _LOGGER.debug("Storage data saved successfully")
        except Exception as e:
            _LOGGER.error("Failed to save storage data: %s", e)
            raise HomeAssistantError(f"Failed to save irrigation storage: {e}")

    def _get_default_data(self) -> Dict[str, Any]:
        """Get default storage data structure."""
        return {
            "version": STORAGE_VERSION,
            "rooms": {},
            "settings": {
                "pump_zone_delay": DEFAULT_PUMP_ZONE_DELAY,
                "sensor_update_interval": DEFAULT_SENSOR_UPDATE_INTERVAL,
                "default_manual_duration": DEFAULT_MANUAL_DURATION,
                "fail_safe_enabled": DEFAULT_FAIL_SAFE_ENABLED,
                "emergency_stop_enabled": DEFAULT_EMERGENCY_STOP_ENABLED,
                "notifications_enabled": DEFAULT_NOTIFICATIONS_ENABLED,
                "error_notifications": DEFAULT_ERROR_NOTIFICATIONS,
                "logging_level": DEFAULT_LOGGING_LEVEL,
                "max_daily_irrigation": DEFAULT_MAX_DAILY_IRRIGATION,
            },
            "history": {
                "events": [],
                "max_history_days": DEFAULT_MAX_HISTORY_DAYS
            },
            "performance_metrics": {
                "irrigation_cycles": {
                    "total_attempts": 0,
                    "successful_cycles": 0,
                    "failed_cycles": 0,
                    "total_duration": 0,
                    "average_duration": 0
                },
                "system_health": {
                    "uptime_start": datetime.now().isoformat(),
                    "error_count": 0,
                    "last_error": None
                }
            }
        }

    async def _async_migrate_data(self) -> None:
        """Migrate data to current version if needed."""
        current_version = self._data.get("version", 1)
        
        if current_version < STORAGE_VERSION:
            _LOGGER.info("Migrating storage data from version %s to %s", current_version, STORAGE_VERSION)
            
            # Perform version-specific migrations
            if current_version == 1:
                # Future migration logic would go here
                pass
            
            # Update version
            self._data["version"] = STORAGE_VERSION
            await self.async_save()
            _LOGGER.info("Storage migration completed")

    # Room management methods
    def get_rooms(self) -> Dict[str, Room]:
        """Get all rooms synchronously."""
        if not self._loaded:
            return {}
        
        rooms = {}
        for room_id, room_data in self._data.get("rooms", {}).items():
            try:
                rooms[room_id] = Room.from_dict(room_data)
            except Exception as e:
                _LOGGER.error("Failed to load room %s: %s", room_id, e)
        
        return rooms

    async def async_get_rooms(self) -> Dict[str, Room]:
        """Get all rooms."""
        if not self._loaded:
            await self.async_load()
        
        return self.get_rooms()

    async def async_get_room(self, room_id: str) -> Optional[Room]:
        """Get a specific room by ID."""
        rooms = await self.async_get_rooms()
        return rooms.get(room_id)

    async def async_save_room(self, room: Room) -> None:
        """Save a room to storage."""
        if not self._loaded:
            await self.async_load()
        
        try:
            room.validate()
            self._data.setdefault("rooms", {})[room.room_id] = room.to_dict()
            await self.async_save()
            _LOGGER.debug("Room %s saved successfully", room.room_id)
        except Exception as e:
            _LOGGER.error("Failed to save room %s: %s", room.room_id, e)
            raise HomeAssistantError(f"Failed to save room {room.room_id}: {e}")

    async def add_room(self, room_data: Dict[str, Any]) -> str:
        """Add a new room and return its ID."""
        if not self._loaded:
            await self.async_load()
        
        # Generate a unique room ID
        import uuid
        room_id = str(uuid.uuid4())[:8]
        
        # Ensure room ID is unique
        while room_id in self._data.get("rooms", {}):
            room_id = str(uuid.uuid4())[:8]
        
        # Create room object
        room_data["room_id"] = room_id
        room = Room.from_dict(room_data)
        
        # Save room
        await self.async_save_room(room)
        return room_id

    async def update_room(self, room_id: str, room_data: Dict[str, Any]) -> None:
        """Update an existing room."""
        if not self._loaded:
            await self.async_load()
        
        if room_id not in self._data.get("rooms", {}):
            raise HomeAssistantError(f"Room {room_id} not found")
        
        # Update room data
        room_data["room_id"] = room_id
        room = Room.from_dict(room_data)
        
        # Save updated room
        await self.async_save_room(room)

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room from storage."""
        return await self.async_delete_room(room_id)

    async def async_delete_room(self, room_id: str) -> bool:
        """Delete a room from storage."""
        if not self._loaded:
            await self.async_load()
        
        if room_id in self._data.get("rooms", {}):
            del self._data["rooms"][room_id]
            await self.async_save()
            _LOGGER.info("Room %s deleted successfully", room_id)
            return True
        
        return False

    # Settings management methods
    async def async_get_settings(self) -> Dict[str, Any]:
        """Get system settings."""
        if not self._loaded:
            await self.async_load()
        
        return self._data.get("settings", {})

    async def async_update_settings(self, settings: Dict[str, Any]) -> None:
        """Update system settings."""
        if not self._loaded:
            await self.async_load()
        
        try:
            # Validate settings
            self._validate_settings(settings)
            
            # Update settings
            current_settings = self._data.setdefault("settings", {})
            current_settings.update(settings)
            
            await self.async_save()
            _LOGGER.debug("Settings updated successfully")
        except Exception as e:
            _LOGGER.error("Failed to update settings: %s", e)
            raise HomeAssistantError(f"Failed to update settings: {e}")

    def _validate_settings(self, settings: Dict[str, Any]) -> None:
        """Validate settings values."""
        if "pump_zone_delay" in settings:
            delay = settings["pump_zone_delay"]
            if not isinstance(delay, int) or delay < 0 or delay > 60:
                raise ValueError("pump_zone_delay must be between 0 and 60 seconds")
        
        if "sensor_update_interval" in settings:
            interval = settings["sensor_update_interval"]
            if not isinstance(interval, int) or interval < 5 or interval > 300:
                raise ValueError("sensor_update_interval must be between 5 and 300 seconds")
        
        if "default_manual_duration" in settings:
            duration = settings["default_manual_duration"]
            if not isinstance(duration, int) or duration < 30 or duration > 3600:
                raise ValueError("default_manual_duration must be between 30 and 3600 seconds")
        
        if "max_daily_irrigation" in settings:
            max_daily = settings["max_daily_irrigation"]
            if not isinstance(max_daily, int) or max_daily < 300 or max_daily > 7200:
                raise ValueError("max_daily_irrigation must be between 300 and 7200 seconds")
        
        if "logging_level" in settings:
            level = settings["logging_level"]
            if level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                raise ValueError("logging_level must be one of: DEBUG, INFO, WARNING, ERROR")
        
        if "max_history_days" in settings:
            days = settings["max_history_days"]
            if not isinstance(days, int) or days < 7 or days > 90:
                raise ValueError("max_history_days must be between 7 and 90 days")
        
        # Boolean settings validation
        bool_settings = ["fail_safe_enabled", "emergency_stop_enabled", "notifications_enabled", "error_notifications"]
        for setting in bool_settings:
            if setting in settings and not isinstance(settings[setting], bool):
                raise ValueError(f"{setting} must be a boolean value")

    # History management methods
    async def async_add_history_event(self, room_id: str, event_type: str, 
                                    duration: int, success: bool, 
                                    error_message: Optional[str] = None) -> None:
        """Add an irrigation event to history."""
        if not self._loaded:
            await self.async_load()
        
        history_event = {
            "timestamp": datetime.now().isoformat(),
            "room_id": room_id,
            "event_type": event_type,
            "duration": duration,
            "success": success,
            "error_message": error_message
        }
        
        history = self._data.setdefault("history", {"events": [], "max_history_days": 30})
        history["events"].append(history_event)
        
        # Clean old history
        await self._async_clean_history()
        
        await self.async_save()
        _LOGGER.debug("History event added for room %s", room_id)

    async def async_get_history(self, room_id: Optional[str] = None, 
                              days: int = 7) -> List[Dict[str, Any]]:
        """Get irrigation history."""
        if not self._loaded:
            await self.async_load()
        
        history_events = self._data.get("history", {}).get("events", [])
        
        # Filter by room if specified
        if room_id:
            history_events = [e for e in history_events if e.get("room_id") == room_id]
        
        # Filter by days
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        filtered_events = []
        for event in history_events:
            try:
                event_date = datetime.fromisoformat(event["timestamp"])
                if event_date >= cutoff_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                continue
        
        return sorted(filtered_events, key=lambda x: x["timestamp"], reverse=True)

    async def _async_clean_history(self) -> None:
        """Clean old history events."""
        history = self._data.get("history", {})
        max_days = history.get("max_history_days", 30)
        
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - max_days)
        
        events = history.get("events", [])
        cleaned_events = []
        
        for event in events:
            try:
                event_date = datetime.fromisoformat(event["timestamp"])
                if event_date >= cutoff_date:
                    cleaned_events.append(event)
            except (ValueError, KeyError):
                continue
        
        history["events"] = cleaned_events
        
        if len(events) != len(cleaned_events):
            _LOGGER.debug("Cleaned %d old history events", len(events) - len(cleaned_events))

    # Performance metrics methods
    
    async def async_record_irrigation_cycle(self, success: bool, duration: int = 0) -> None:
        """Record an irrigation cycle for performance tracking."""
        if not self._loaded:
            await self.async_load()
        
        metrics = self._data.setdefault("performance_metrics", {})
        irrigation_metrics = metrics.setdefault("irrigation_cycles", {
            "total_attempts": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "total_duration": 0,
            "average_duration": 0
        })
        
        # Update counters
        irrigation_metrics["total_attempts"] += 1
        
        if success:
            irrigation_metrics["successful_cycles"] += 1
            irrigation_metrics["total_duration"] += duration
        else:
            irrigation_metrics["failed_cycles"] += 1
        
        # Calculate average duration
        if irrigation_metrics["successful_cycles"] > 0:
            irrigation_metrics["average_duration"] = (
                irrigation_metrics["total_duration"] / irrigation_metrics["successful_cycles"]
            )
        
        await self.async_save()
        _LOGGER.debug("Irrigation cycle recorded: success=%s, duration=%d", success, duration)
    
    async def async_record_system_error(self, error_type: str, error_message: str) -> None:
        """Record a system error for performance tracking."""
        if not self._loaded:
            await self.async_load()
        
        metrics = self._data.setdefault("performance_metrics", {})
        system_metrics = metrics.setdefault("system_health", {
            "uptime_start": datetime.now().isoformat(),
            "error_count": 0,
            "last_error": None
        })
        
        system_metrics["error_count"] += 1
        system_metrics["last_error"] = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message
        }
        
        await self.async_save()
        _LOGGER.debug("System error recorded: %s", error_type)
    
    async def async_get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        if not self._loaded:
            await self.async_load()
        
        metrics = self._data.get("performance_metrics", {})
        
        # Calculate success rate
        irrigation_metrics = metrics.get("irrigation_cycles", {})
        total_attempts = irrigation_metrics.get("total_attempts", 0)
        successful_cycles = irrigation_metrics.get("successful_cycles", 0)
        
        success_rate = 0.0
        if total_attempts > 0:
            success_rate = (successful_cycles / total_attempts) * 100
        
        # Calculate uptime
        system_metrics = metrics.get("system_health", {})
        uptime_start = system_metrics.get("uptime_start")
        uptime_seconds = 0
        
        if uptime_start:
            try:
                start_time = datetime.fromisoformat(uptime_start)
                uptime_seconds = (datetime.now() - start_time).total_seconds()
            except ValueError:
                pass
        
        return {
            "irrigation_cycles": {
                **irrigation_metrics,
                "success_rate": round(success_rate, 2)
            },
            "system_health": {
                **system_metrics,
                "uptime_seconds": int(uptime_seconds),
                "uptime_hours": round(uptime_seconds / 3600, 2)
            }
        }
    
    async def async_reset_performance_metrics(self) -> None:
        """Reset performance metrics."""
        if not self._loaded:
            await self.async_load()
        
        self._data["performance_metrics"] = {
            "irrigation_cycles": {
                "total_attempts": 0,
                "successful_cycles": 0,
                "failed_cycles": 0,
                "total_duration": 0,
                "average_duration": 0
            },
            "system_health": {
                "uptime_start": datetime.now().isoformat(),
                "error_count": 0,
                "last_error": None
            }
        }
        
        await self.async_save()
        _LOGGER.info("Performance metrics reset")

    # Backup and restore methods
    async def async_create_backup(self) -> Dict[str, Any]:
        """Create a backup of all data."""
        if not self._loaded:
            await self.async_load()
        
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "version": STORAGE_VERSION,
            "data": self._data.copy()
        }
        
        _LOGGER.info("Backup created successfully")
        return backup_data

    async def async_restore_backup(self, backup_data: Dict[str, Any]) -> None:
        """Restore data from backup."""
        try:
            # Validate backup data
            if "data" not in backup_data:
                raise ValueError("Invalid backup data: missing 'data' key")
            
            # Validate rooms in backup
            rooms_data = backup_data["data"].get("rooms", {})
            for room_id, room_data in rooms_data.items():
                try:
                    Room.from_dict(room_data)
                except Exception as e:
                    raise ValueError(f"Invalid room data for {room_id}: {e}")
            
            # Restore data
            self._data = backup_data["data"]
            self._loaded = True
            
            await self.async_save()
            _LOGGER.info("Backup restored successfully")
            
        except Exception as e:
            _LOGGER.error("Failed to restore backup: %s", e)
            raise HomeAssistantError(f"Failed to restore backup: {e}")

    async def async_export_data(self) -> str:
        """Export all data as JSON string."""
        backup_data = await self.async_create_backup()
        return json.dumps(backup_data, indent=2)

    async def async_import_data(self, json_data: str) -> None:
        """Import data from JSON string."""
        try:
            backup_data = json.loads(json_data)
            await self.async_restore_backup(backup_data)
        except json.JSONDecodeError as e:
            raise HomeAssistantError(f"Invalid JSON data: {e}")

    # Utility methods
    def is_loaded(self) -> bool:
        """Check if storage is loaded."""
        return self._loaded

    async def async_reset_data(self) -> None:
        """Reset all data to defaults."""
        self._data = self._get_default_data()
        await self.async_save()
        _LOGGER.warning("All irrigation data has been reset to defaults")