"""Services for the Irrigation Addon integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import IrrigationCoordinator

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_START_MANUAL_RUN = "start_manual_run"
SERVICE_STOP_IRRIGATION = "stop_irrigation"
SERVICE_ENABLE_EVENT = "enable_event"
SERVICE_DISABLE_EVENT = "disable_event"
SERVICE_ADD_SHOT = "add_shot"
SERVICE_REMOVE_SHOT = "remove_shot"
SERVICE_UPDATE_SHOT = "update_shot"
SERVICE_EMERGENCY_STOP = "emergency_stop"
SERVICE_EMERGENCY_STOP_ALL = "emergency_stop_all"
SERVICE_UPDATE_SETTINGS = "update_settings"
SERVICE_GET_DATA = "get_data"
SERVICE_CREATE_BACKUP = "create_backup"
SERVICE_RESTORE_BACKUP = "restore_backup"
SERVICE_EXPORT_DIAGNOSTICS = "export_diagnostics"
SERVICE_GET_ERROR_STATISTICS = "get_error_statistics"
SERVICE_CLEAR_ERROR_HISTORY = "clear_error_history"
SERVICE_GET_PERFORMANCE_METRICS = "get_performance_metrics"
SERVICE_RESET_PERFORMANCE_METRICS = "reset_performance_metrics"

# Service schemas
START_MANUAL_RUN_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
    vol.Required("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
})

STOP_IRRIGATION_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
})

ENABLE_EVENT_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
    vol.Required("event_type"): vol.In(["P1", "P2"]),
    vol.Required("enabled"): cv.boolean,
})

ADD_SHOT_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
    vol.Required("event_type"): vol.In(["P1", "P2"]),
    vol.Required("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
    vol.Optional("interval_after", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
    vol.Optional("position"): vol.All(vol.Coerce(int), vol.Range(min=0)),
})

REMOVE_SHOT_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
    vol.Required("event_type"): vol.In(["P1", "P2"]),
    vol.Required("shot_index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
})

UPDATE_SHOT_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
    vol.Required("event_type"): vol.In(["P1", "P2"]),
    vol.Required("shot_index"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
    vol.Optional("interval_after"): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
})

EMERGENCY_STOP_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
})

UPDATE_SETTINGS_SCHEMA = vol.Schema({
    vol.Required("settings"): {
        vol.Optional("pump_zone_delay"): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
        vol.Optional("sensor_update_interval"): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
        vol.Optional("default_manual_duration"): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
        vol.Optional("max_daily_irrigation"): vol.All(vol.Coerce(int), vol.Range(min=300, max=7200)),
        vol.Optional("fail_safe_enabled"): cv.boolean,
        vol.Optional("emergency_stop_enabled"): cv.boolean,
        vol.Optional("notifications_enabled"): cv.boolean,
        vol.Optional("error_notifications"): cv.boolean,
        vol.Optional("logging_level"): vol.In(["DEBUG", "INFO", "WARNING", "ERROR"]),
        vol.Optional("max_history_days"): vol.All(vol.Coerce(int), vol.Range(min=7, max=90)),
    }
})

RESTORE_BACKUP_SCHEMA = vol.Schema({
    vol.Required("backup_data"): dict,
})

EXPORT_DIAGNOSTICS_SCHEMA = vol.Schema({
    vol.Optional("include_room_diagnostics", default=True): cv.boolean,
    vol.Optional("include_performance_metrics", default=True): cv.boolean,
    vol.Optional("include_error_history", default=True): cv.boolean,
})


class IrrigationServices:
    """Handle irrigation services."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the services."""
        self.hass = hass

    def async_register_services(self) -> None:
        """Register all irrigation services."""
        _LOGGER.debug("Registering irrigation services")

        # Manual run control services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_START_MANUAL_RUN,
            self._async_start_manual_run,
            schema=START_MANUAL_RUN_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_IRRIGATION,
            self._async_stop_irrigation,
            schema=STOP_IRRIGATION_SCHEMA,
        )

        # Event management services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_EVENT,
            self._async_enable_event,
            schema=ENABLE_EVENT_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_DISABLE_EVENT,
            self._async_disable_event,
            schema=ENABLE_EVENT_SCHEMA,
        )

        # Shot management services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_SHOT,
            self._async_add_shot,
            schema=ADD_SHOT_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_SHOT,
            self._async_remove_shot,
            schema=REMOVE_SHOT_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_SHOT,
            self._async_update_shot,
            schema=UPDATE_SHOT_SCHEMA,
        )

        # Emergency stop services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_EMERGENCY_STOP,
            self._async_emergency_stop,
            schema=EMERGENCY_STOP_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_EMERGENCY_STOP_ALL,
            self._async_emergency_stop_all,
        )

        # Settings and data services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_SETTINGS,
            self._async_update_settings,
            schema=UPDATE_SETTINGS_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_GET_DATA,
            self._async_get_data,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_CREATE_BACKUP,
            self._async_create_backup,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RESTORE_BACKUP,
            self._async_restore_backup,
            schema=RESTORE_BACKUP_SCHEMA,
        )

        # Diagnostic services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_EXPORT_DIAGNOSTICS,
            self._async_export_diagnostics,
            schema=EXPORT_DIAGNOSTICS_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_GET_ERROR_STATISTICS,
            self._async_get_error_statistics,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_ERROR_HISTORY,
            self._async_clear_error_history,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_GET_PERFORMANCE_METRICS,
            self._async_get_performance_metrics,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_PERFORMANCE_METRICS,
            self._async_reset_performance_metrics,
        )

        _LOGGER.info("Irrigation services registered successfully")

    def async_remove_services(self) -> None:
        """Remove all irrigation services."""
        _LOGGER.debug("Removing irrigation services")

        services = [
            SERVICE_START_MANUAL_RUN,
            SERVICE_STOP_IRRIGATION,
            SERVICE_ENABLE_EVENT,
            SERVICE_DISABLE_EVENT,
            SERVICE_ADD_SHOT,
            SERVICE_REMOVE_SHOT,
            SERVICE_UPDATE_SHOT,
            SERVICE_EMERGENCY_STOP,
            SERVICE_EMERGENCY_STOP_ALL,
            SERVICE_UPDATE_SETTINGS,
            SERVICE_GET_DATA,
            SERVICE_CREATE_BACKUP,
            SERVICE_RESTORE_BACKUP,
            SERVICE_EXPORT_DIAGNOSTICS,
            SERVICE_GET_ERROR_STATISTICS,
            SERVICE_CLEAR_ERROR_HISTORY,
            SERVICE_GET_PERFORMANCE_METRICS,
            SERVICE_RESET_PERFORMANCE_METRICS,
        ]

        for service in services:
            if self.hass.services.has_service(DOMAIN, service):
                self.hass.services.async_remove(DOMAIN, service)

        _LOGGER.info("Irrigation services removed successfully")

    def _get_coordinator(self, entry_id: str = None) -> IrrigationCoordinator:
        """Get the coordinator instance."""
        if not self.hass.data.get(DOMAIN):
            raise HomeAssistantError("Irrigation addon not loaded")

        # If no entry_id specified, get the first available coordinator
        if entry_id is None:
            coordinators = list(self.hass.data[DOMAIN].values())
            if not coordinators:
                raise HomeAssistantError("No irrigation coordinators available")
            return coordinators[0]

        coordinator = self.hass.data[DOMAIN].get(entry_id)
        if not coordinator:
            raise HomeAssistantError(f"Coordinator not found for entry {entry_id}")

        return coordinator

    async def _async_start_manual_run(self, call: ServiceCall) -> None:
        """Handle start manual run service call."""
        room_id = call.data["room_id"]
        duration = call.data["duration"]

        _LOGGER.info("Service call: start_manual_run for room %s, duration %d", room_id, duration)

        try:
            coordinator = self._get_coordinator()
            success = await coordinator.async_start_manual_run(room_id, duration)

            if not success:
                raise HomeAssistantError(f"Failed to start manual run for room {room_id}")

            _LOGGER.info("Manual run started successfully for room %s", room_id)

        except Exception as e:
            _LOGGER.error("Error in start_manual_run service: %s", e)
            raise HomeAssistantError(f"Failed to start manual run: {e}")

    async def _async_stop_irrigation(self, call: ServiceCall) -> None:
        """Handle stop irrigation service call."""
        room_id = call.data["room_id"]

        _LOGGER.info("Service call: stop_irrigation for room %s", room_id)

        try:
            coordinator = self._get_coordinator()
            success = await coordinator.async_stop_irrigation(room_id)

            if not success:
                _LOGGER.warning("No active irrigation found for room %s", room_id)
            else:
                _LOGGER.info("Irrigation stopped successfully for room %s", room_id)

        except Exception as e:
            _LOGGER.error("Error in stop_irrigation service: %s", e)
            raise HomeAssistantError(f"Failed to stop irrigation: {e}")

    async def _async_enable_event(self, call: ServiceCall) -> None:
        """Handle enable event service call."""
        room_id = call.data["room_id"]
        event_type = call.data["event_type"]
        enabled = call.data["enabled"]

        _LOGGER.info("Service call: enable_event for room %s, event %s, enabled %s", 
                    room_id, event_type, enabled)

        try:
            coordinator = self._get_coordinator()
            room = await coordinator.async_get_room(room_id)

            if not room:
                raise HomeAssistantError(f"Room {room_id} not found")

            event = room.get_event(event_type)
            if not event:
                raise HomeAssistantError(f"Event {event_type} not found for room {room_id}")

            # Update event enabled status
            event.enabled = enabled

            # Save updated room
            await coordinator.async_update_room(room)

            _LOGGER.info("Event %s %s for room %s", 
                        event_type, "enabled" if enabled else "disabled", room_id)

        except Exception as e:
            _LOGGER.error("Error in enable_event service: %s", e)
            raise HomeAssistantError(f"Failed to update event: {e}")

    async def _async_disable_event(self, call: ServiceCall) -> None:
        """Handle disable event service call (convenience wrapper)."""
        # Create new call data with enabled=False
        new_data = call.data.copy()
        new_data["enabled"] = False
        
        # Create new service call
        new_call = ServiceCall(call.domain, call.service, new_data, call.context)
        await self._async_enable_event(new_call)

    async def _async_add_shot(self, call: ServiceCall) -> None:
        """Handle add shot service call."""
        room_id = call.data["room_id"]
        event_type = call.data["event_type"]
        duration = call.data["duration"]
        interval_after = call.data.get("interval_after", 0)
        position = call.data.get("position")

        _LOGGER.info("Service call: add_shot for room %s, event %s, duration %d", 
                    room_id, event_type, duration)

        try:
            coordinator = self._get_coordinator()
            room = await coordinator.async_get_room(room_id)

            if not room:
                raise HomeAssistantError(f"Room {room_id} not found")

            event = room.get_event(event_type)
            if not event:
                raise HomeAssistantError(f"Event {event_type} not found for room {room_id}")

            # Create new shot
            from .models import Shot
            new_shot = Shot(duration=duration, interval_after=interval_after)

            # Add shot at specified position or at the end
            if position is not None and 0 <= position <= len(event.shots):
                event.shots.insert(position, new_shot)
            else:
                event.shots.append(new_shot)

            # Save updated room
            await coordinator.async_update_room(room)

            _LOGGER.info("Shot added to event %s for room %s", event_type, room_id)

        except Exception as e:
            _LOGGER.error("Error in add_shot service: %s", e)
            raise HomeAssistantError(f"Failed to add shot: {e}")

    async def _async_remove_shot(self, call: ServiceCall) -> None:
        """Handle remove shot service call."""
        room_id = call.data["room_id"]
        event_type = call.data["event_type"]
        shot_index = call.data["shot_index"]

        _LOGGER.info("Service call: remove_shot for room %s, event %s, index %d", 
                    room_id, event_type, shot_index)

        try:
            coordinator = self._get_coordinator()
            room = await coordinator.async_get_room(room_id)

            if not room:
                raise HomeAssistantError(f"Room {room_id} not found")

            event = room.get_event(event_type)
            if not event:
                raise HomeAssistantError(f"Event {event_type} not found for room {room_id}")

            # Validate shot index
            if shot_index < 0 or shot_index >= len(event.shots):
                raise HomeAssistantError(f"Invalid shot index {shot_index}")

            # Remove shot
            event.shots.pop(shot_index)

            # Save updated room
            await coordinator.async_update_room(room)

            _LOGGER.info("Shot removed from event %s for room %s", event_type, room_id)

        except Exception as e:
            _LOGGER.error("Error in remove_shot service: %s", e)
            raise HomeAssistantError(f"Failed to remove shot: {e}")

    async def _async_update_shot(self, call: ServiceCall) -> None:
        """Handle update shot service call."""
        room_id = call.data["room_id"]
        event_type = call.data["event_type"]
        shot_index = call.data["shot_index"]
        duration = call.data.get("duration")
        interval_after = call.data.get("interval_after")

        _LOGGER.info("Service call: update_shot for room %s, event %s, index %d", 
                    room_id, event_type, shot_index)

        try:
            coordinator = self._get_coordinator()
            room = await coordinator.async_get_room(room_id)

            if not room:
                raise HomeAssistantError(f"Room {room_id} not found")

            event = room.get_event(event_type)
            if not event:
                raise HomeAssistantError(f"Event {event_type} not found for room {room_id}")

            # Validate shot index
            if shot_index < 0 or shot_index >= len(event.shots):
                raise HomeAssistantError(f"Invalid shot index {shot_index}")

            # Update shot properties
            shot = event.shots[shot_index]
            if duration is not None:
                shot.duration = duration
            if interval_after is not None:
                shot.interval_after = interval_after

            # Save updated room
            await coordinator.async_update_room(room)

            _LOGGER.info("Shot updated in event %s for room %s", event_type, room_id)

        except Exception as e:
            _LOGGER.error("Error in update_shot service: %s", e)
            raise HomeAssistantError(f"Failed to update shot: {e}")

    async def _async_emergency_stop(self, call: ServiceCall) -> None:
        """Handle emergency stop service call for a specific room."""
        room_id = call.data["room_id"]

        _LOGGER.warning("Service call: emergency_stop for room %s", room_id)

        try:
            coordinator = self._get_coordinator()
            success = await coordinator.async_emergency_stop_room(room_id)

            if not success:
                raise HomeAssistantError(f"Failed to emergency stop room {room_id}")

            _LOGGER.info("Emergency stop completed for room %s", room_id)

        except Exception as e:
            _LOGGER.error("Error in emergency_stop service: %s", e)
            raise HomeAssistantError(f"Failed to emergency stop: {e}")

    async def _async_emergency_stop_all(self, call: ServiceCall) -> None:
        """Handle emergency stop all service call."""
        _LOGGER.warning("Service call: emergency_stop_all")

        try:
            coordinator = self._get_coordinator()
            results = await coordinator.async_emergency_stop_all()

            # Check if any operations failed
            failed_operations = [op for op, success in results.items() if not success]
            if failed_operations:
                _LOGGER.warning("Some emergency stop operations failed: %s", failed_operations)

            _LOGGER.info("Emergency stop all completed")

        except Exception as e:
            _LOGGER.error("Error in emergency_stop_all service: %s", e)
            raise HomeAssistantError(f"Failed to emergency stop all: {e}")

    async def _async_update_settings(self, call: ServiceCall) -> None:
        """Handle update settings service call."""
        settings = call.data["settings"]

        _LOGGER.info("Service call: update_settings with %d settings", len(settings))

        try:
            coordinator = self._get_coordinator()
            await coordinator.async_update_settings(settings)

            _LOGGER.info("Settings updated successfully")

        except Exception as e:
            _LOGGER.error("Error in update_settings service: %s", e)
            raise HomeAssistantError(f"Failed to update settings: {e}")

    async def _async_get_data(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle get data service call."""
        _LOGGER.debug("Service call: get_data")

        try:
            coordinator = self._get_coordinator()
            
            # Get current data from coordinator
            data = {
                "rooms": coordinator.rooms,
                "sensor_data": coordinator.data.get("sensor_data", {}) if coordinator.data else {},
                "settings": coordinator.settings,
                "room_statuses": coordinator.get_all_room_statuses(),
            }

            _LOGGER.debug("Data retrieved successfully")
            return {"data": data}

        except Exception as e:
            _LOGGER.error("Error in get_data service: %s", e)
            raise HomeAssistantError(f"Failed to get data: {e}")

    async def _async_create_backup(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle create backup service call."""
        _LOGGER.info("Service call: create_backup")

        try:
            coordinator = self._get_coordinator()
            backup_data = await coordinator.storage.async_create_backup()

            _LOGGER.info("Backup created successfully")
            return {"backup_data": backup_data}

        except Exception as e:
            _LOGGER.error("Error in create_backup service: %s", e)
            raise HomeAssistantError(f"Failed to create backup: {e}")

    async def _async_restore_backup(self, call: ServiceCall) -> None:
        """Handle restore backup service call."""
        backup_data = call.data["backup_data"]

        _LOGGER.info("Service call: restore_backup")

        try:
            coordinator = self._get_coordinator()
            await coordinator.storage.async_restore_backup(backup_data)

            # Reload coordinator data
            await coordinator.async_setup()

            _LOGGER.info("Backup restored successfully")

        except Exception as e:
            _LOGGER.error("Error in restore_backup service: %s", e)
            raise HomeAssistantError(f"Failed to restore backup: {e}")

    async def _async_export_diagnostics(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle export diagnostics service call."""
        include_room_diagnostics = call.data.get("include_room_diagnostics", True)
        include_performance_metrics = call.data.get("include_performance_metrics", True)
        include_error_history = call.data.get("include_error_history", True)

        _LOGGER.info("Service call: export_diagnostics")

        try:
            coordinator = self._get_coordinator()
            
            # Get comprehensive diagnostics
            diagnostics = await coordinator.get_comprehensive_diagnostics()
            
            # Filter based on parameters
            if not include_room_diagnostics:
                diagnostics.pop("room_diagnostics", None)
            
            if not include_performance_metrics:
                diagnostics.pop("performance_metrics", None)
            
            if not include_error_history:
                if "error_statistics" in diagnostics:
                    diagnostics["error_statistics"].pop("recent_errors", None)

            # Export to file
            filepath = await coordinator.export_diagnostics_file()

            _LOGGER.info("Diagnostics exported successfully")
            return {
                "diagnostics": diagnostics,
                "exported_file": filepath,
                "timestamp": dt_util.now().isoformat()
            }

        except Exception as e:
            _LOGGER.error("Error in export_diagnostics service: %s", e)
            raise HomeAssistantError(f"Failed to export diagnostics: {e}")

    async def _async_get_error_statistics(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle get error statistics service call."""
        _LOGGER.debug("Service call: get_error_statistics")

        try:
            coordinator = self._get_coordinator()
            error_stats = coordinator.get_error_statistics()

            _LOGGER.debug("Error statistics retrieved successfully")
            return {"error_statistics": error_stats}

        except Exception as e:
            _LOGGER.error("Error in get_error_statistics service: %s", e)
            raise HomeAssistantError(f"Failed to get error statistics: {e}")

    async def _async_clear_error_history(self, call: ServiceCall) -> None:
        """Handle clear error history service call."""
        _LOGGER.info("Service call: clear_error_history")

        try:
            coordinator = self._get_coordinator()
            
            # Clear error history (this would need to be implemented in coordinator)
            coordinator._last_errors.clear()
            coordinator._error_counts.clear()

            _LOGGER.info("Error history cleared successfully")

        except Exception as e:
            _LOGGER.error("Error in clear_error_history service: %s", e)
            raise HomeAssistantError(f"Failed to clear error history: {e}")

    async def _async_get_performance_metrics(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle get performance metrics service call."""
        _LOGGER.debug("Service call: get_performance_metrics")

        try:
            coordinator = self._get_coordinator()
            performance_metrics = await coordinator.storage.async_get_performance_metrics()

            _LOGGER.debug("Performance metrics retrieved successfully")
            return {"performance_metrics": performance_metrics}

        except Exception as e:
            _LOGGER.error("Error in get_performance_metrics service: %s", e)
            raise HomeAssistantError(f"Failed to get performance metrics: {e}")

    async def _async_reset_performance_metrics(self, call: ServiceCall) -> None:
        """Handle reset performance metrics service call."""
        _LOGGER.info("Service call: reset_performance_metrics")

        try:
            coordinator = self._get_coordinator()
            await coordinator.storage.async_reset_performance_metrics()

            _LOGGER.info("Performance metrics reset successfully")

        except Exception as e:
            _LOGGER.error("Error in reset_performance_metrics service: %s", e)
            raise HomeAssistantError(f"Failed to reset performance metrics: {e}")