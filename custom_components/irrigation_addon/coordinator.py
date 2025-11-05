"""Irrigation coordinator for managing data updates and scheduling."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from croniter import croniter

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval, async_track_point_in_time
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DEFAULT_SENSOR_UPDATE_INTERVAL
from .storage import IrrigationStorage
from .models import Room, IrrigationEvent, Shot
from .exceptions import (
    IrrigationError, EntityUnavailableError, LightScheduleConflictError,
    OverWateringError, IrrigationConflictError, HardwareControlError,
    SchedulingError, EmergencyStopError, IrrigationErrorHandler
)
from .logging_utils import get_irrigation_logger, PerformanceTracker, DiagnosticCollector

_LOGGER = logging.getLogger(__name__)


class IrrigationCoordinator(DataUpdateCoordinator):
    """Irrigation coordinator for managing data updates and scheduling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.storage = IrrigationStorage(hass)
        self._rooms: Dict[str, Room] = {}
        self._settings: Dict[str, Any] = {}
        
        # Enhanced logging and monitoring
        self.irrigation_logger = get_irrigation_logger(f"{__name__}.{entry.entry_id}", hass)
        self.performance_tracker = PerformanceTracker(self.irrigation_logger)
        self.diagnostic_collector = DiagnosticCollector(hass, self.irrigation_logger)
        
        # Error tracking
        self._error_counts: Dict[str, int] = {}
        self._last_errors: List[Dict[str, Any]] = []
        self._max_error_history = 50
        
        # Scheduling and execution state
        self._scheduled_events: Dict[str, Any] = {}  # room_id -> {event_type: cancel_callback}
        self._active_irrigations: Dict[str, Dict[str, Any]] = {}  # room_id -> irrigation_state
        self._manual_runs: Dict[str, Dict[str, Any]] = {}  # room_id -> manual_run_state
        self._daily_irrigation_totals: Dict[str, int] = {}  # room_id -> seconds_today
        
        # Event tracking
        self._event_listeners: Set[Any] = set()
        
        # Initialize with default update interval
        update_interval = timedelta(seconds=DEFAULT_SENSOR_UPDATE_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        with IrrigationErrorHandler("coordinator_setup", self.irrigation_logger):
            self.performance_tracker.start_operation("coordinator_setup")
            
            try:
                # Load storage data
                await self.storage.async_load()
                
                # Load rooms and settings
                self._rooms = await self.storage.async_get_rooms()
                self._settings = await self.storage.async_get_settings()
                
                # Update coordinator interval based on settings
                sensor_interval = self._settings.get("sensor_update_interval", DEFAULT_SENSOR_UPDATE_INTERVAL)
                self.update_interval = timedelta(seconds=sensor_interval)
                
                # Initialize daily irrigation tracking
                self._reset_daily_totals()
                
                # Schedule all irrigation events
                await self._schedule_all_events()
                
                # Set up daily reset timer
                self._schedule_daily_reset()
                
                self.irrigation_logger.info(
                    "Coordinator setup complete", 
                    rooms_count=len(self._rooms),
                    settings_loaded=len(self._settings)
                )
                
            except Exception as e:
                self._record_error("coordinator_setup", e)
                raise IrrigationError(
                    f"Failed to setup irrigation coordinator: {e}",
                    error_code="COORDINATOR_SETUP_FAILED",
                    details={"underlying_error": str(e)}
                )
            finally:
                self.performance_tracker.end_operation("coordinator_setup")

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        try:
            # Cancel all scheduled events
            await self._cancel_all_scheduled_events()
            
            # Stop any active irrigations
            for room_id in list(self._active_irrigations.keys()):
                await self.async_stop_irrigation(room_id)
            
            # Stop any manual runs
            for room_id in list(self._manual_runs.keys()):
                await self.async_stop_manual_run(room_id)
            
            # Remove event listeners
            for listener in self._event_listeners:
                listener()
            self._event_listeners.clear()
            
            _LOGGER.info("Coordinator shutdown complete")
            
        except Exception as e:
            _LOGGER.error("Error during coordinator shutdown: %s", e)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sensors and update irrigation status."""
        with IrrigationErrorHandler("sensor_data_update", self.irrigation_logger, suppress_exceptions=True):
            self.performance_tracker.start_operation("sensor_data_update")
            
            try:
                # Update sensor data for all rooms
                sensor_data = {}
                unavailable_sensors = []
                
                for room_id, room in self._rooms.items():
                    room_sensors = {}
                    
                    # Read sensor values from Home Assistant
                    for sensor_type, entity_id in room.sensors.items():
                        try:
                            state = self.hass.states.get(entity_id)
                            if state and state.state not in ["unknown", "unavailable"]:
                                try:
                                    room_sensors[sensor_type] = {
                                        "value": float(state.state),
                                        "unit": state.attributes.get("unit_of_measurement"),
                                        "last_updated": state.last_updated.isoformat()
                                    }
                                except (ValueError, TypeError):
                                    room_sensors[sensor_type] = {
                                        "value": state.state,
                                        "unit": state.attributes.get("unit_of_measurement"),
                                        "last_updated": state.last_updated.isoformat()
                                    }
                            else:
                                room_sensors[sensor_type] = {
                                    "value": None,
                                    "unit": None,
                                    "last_updated": None,
                                    "unavailable": True
                                }
                                unavailable_sensors.append(f"{room_id}:{sensor_type}:{entity_id}")
                        except Exception as sensor_error:
                            self.irrigation_logger.warning(
                                f"Failed to read sensor {entity_id}",
                                room_id=room_id,
                                sensor_type=sensor_type,
                                entity_id=entity_id,
                                error=str(sensor_error)
                            )
                            room_sensors[sensor_type] = {
                                "value": None,
                                "unit": None,
                                "last_updated": None,
                                "error": str(sensor_error)
                            }
                    
                    sensor_data[room_id] = room_sensors
                
                # Log sensor availability issues
                if unavailable_sensors:
                    self.irrigation_logger.debug(
                        f"Unavailable sensors detected: {len(unavailable_sensors)}",
                        unavailable_sensors=unavailable_sensors
                    )
                
                # Record performance metrics
                self.performance_tracker.record_metric(
                    "sensor_update_count", 
                    sum(len(room.sensors) for room in self._rooms.values())
                )
                self.performance_tracker.record_metric(
                    "unavailable_sensor_count", 
                    len(unavailable_sensors)
                )
                
                return {
                    "rooms": self._rooms,
                    "sensor_data": sensor_data,
                    "settings": self._settings,
                    "system_health": self.get_system_health()
                }
                
            except Exception as e:
                self._record_error("sensor_data_update", e)
                self.irrigation_logger.error("Error updating coordinator data", error=e)
                # Return minimal data to keep system functional
                return {
                    "rooms": self._rooms,
                    "sensor_data": {},
                    "settings": self._settings,
                    "error": str(e)
                }
            finally:
                self.performance_tracker.end_operation("sensor_data_update")

    @property
    def rooms(self) -> Dict[str, Room]:
        """Get all rooms."""
        return self._rooms

    @property
    def settings(self) -> Dict[str, Any]:
        """Get current settings."""
        return self._settings

    async def async_add_room(self, room: Room) -> None:
        """Add a new room."""
        try:
            # Validate entities exist in Home Assistant
            missing_entities = await room.validate_entities_exist(self.hass)
            if missing_entities:
                raise HomeAssistantError(f"Missing entities: {', '.join(missing_entities)}")
            
            # Save to storage
            await self.storage.async_save_room(room)
            
            # Update local cache
            self._rooms[room.room_id] = room
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info("Room %s added successfully", room.room_id)
            
        except Exception as e:
            _LOGGER.error("Failed to add room %s: %s", room.room_id, e)
            raise

    async def async_update_room(self, room: Room) -> None:
        """Update an existing room."""
        try:
            # Validate entities exist in Home Assistant
            missing_entities = await room.validate_entities_exist(self.hass)
            if missing_entities:
                raise HomeAssistantError(f"Missing entities: {', '.join(missing_entities)}")
            
            # Save to storage
            await self.storage.async_save_room(room)
            
            # Update local cache
            self._rooms[room.room_id] = room
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info("Room %s updated successfully", room.room_id)
            
        except Exception as e:
            _LOGGER.error("Failed to update room %s: %s", room.room_id, e)
            raise

    async def async_delete_room(self, room_id: str) -> None:
        """Delete a room."""
        try:
            # Remove from storage
            success = await self.storage.async_delete_room(room_id)
            
            if success:
                # Remove from local cache
                self._rooms.pop(room_id, None)
                
                # Trigger data update
                await self.async_request_refresh()
                
                _LOGGER.info("Room %s deleted successfully", room_id)
            else:
                raise HomeAssistantError(f"Room {room_id} not found")
                
        except Exception as e:
            _LOGGER.error("Failed to delete room %s: %s", room_id, e)
            raise

    async def async_get_room(self, room_id: str) -> Optional[Room]:
        """Get a specific room."""
        return self._rooms.get(room_id)

    async def async_update_settings(self, settings: Dict[str, Any]) -> None:
        """Update system settings."""
        try:
            # Save to storage
            await self.storage.async_update_settings(settings)
            
            # Update local cache
            self._settings.update(settings)
            
            # Update coordinator interval if sensor_update_interval changed
            if "sensor_update_interval" in settings:
                self.update_interval = timedelta(seconds=settings["sensor_update_interval"])
            
            # Update logging level if changed
            if "logging_level" in settings:
                self._update_logging_level(settings["logging_level"])
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info("Settings updated successfully")
            
        except Exception as e:
            _LOGGER.error("Failed to update settings: %s", e)
            raise

    # Scheduling Engine Methods
    
    async def _schedule_all_events(self) -> None:
        """Schedule all irrigation events for all rooms."""
        for room_id, room in self._rooms.items():
            await self._schedule_room_events(room_id, room)

    async def _schedule_room_events(self, room_id: str, room: Room) -> None:
        """Schedule irrigation events for a specific room."""
        # Cancel existing schedules for this room
        await self._cancel_room_scheduled_events(room_id)
        
        for event in room.events:
            if event.enabled and event.schedule:
                await self._schedule_event(room_id, event)

    async def _schedule_event(self, room_id: str, event: IrrigationEvent) -> None:
        """Schedule a single irrigation event."""
        try:
            # Parse cron expression and get next run time
            now = dt_util.now()
            cron = croniter(event.schedule, now)
            next_run = cron.get_next(datetime)
            
            # Update event next_run time
            event.next_run = next_run
            
            # Schedule the event
            cancel_callback = async_track_point_in_time(
                self.hass,
                lambda dt, r_id=room_id, evt=event: self.hass.async_create_task(
                    self._execute_scheduled_event(r_id, evt)
                ),
                next_run
            )
            
            # Store the cancel callback
            if room_id not in self._scheduled_events:
                self._scheduled_events[room_id] = {}
            self._scheduled_events[room_id][event.event_type] = cancel_callback
            
            _LOGGER.debug(
                "Scheduled %s event for room %s at %s", 
                event.event_type, room_id, next_run
            )
            
        except Exception as e:
            _LOGGER.error(
                "Failed to schedule %s event for room %s: %s", 
                event.event_type, room_id, e
            )

    async def _cancel_all_scheduled_events(self) -> None:
        """Cancel all scheduled irrigation events."""
        for room_id in list(self._scheduled_events.keys()):
            await self._cancel_room_scheduled_events(room_id)

    async def _cancel_room_scheduled_events(self, room_id: str) -> None:
        """Cancel scheduled events for a specific room."""
        if room_id in self._scheduled_events:
            for event_type, cancel_callback in self._scheduled_events[room_id].items():
                if cancel_callback:
                    cancel_callback()
            del self._scheduled_events[room_id]

    async def _execute_scheduled_event(self, room_id: str, event: IrrigationEvent) -> None:
        """Execute a scheduled irrigation event."""
        try:
            _LOGGER.info("Executing scheduled %s event for room %s", event.event_type, room_id)
            
            # Check if room still exists
            if room_id not in self._rooms:
                _LOGGER.warning("Room %s no longer exists, skipping event", room_id)
                return
            
            # Execute the irrigation event
            success = await self.async_execute_irrigation_event(room_id, event.event_type)
            
            if success:
                # Update last run time
                event.last_run = dt_util.now()
                
                # Save updated room data
                room = self._rooms[room_id]
                await self.storage.async_save_room(room)
            
            # Reschedule the event for next occurrence
            await self._schedule_event(room_id, event)
            
        except Exception as e:
            _LOGGER.error("Error executing scheduled event for room %s: %s", room_id, e)
            
            # Still reschedule even if execution failed
            try:
                await self._schedule_event(room_id, event)
            except Exception as reschedule_error:
                _LOGGER.error("Failed to reschedule event: %s", reschedule_error)

    def _schedule_daily_reset(self) -> None:
        """Schedule daily reset of irrigation totals."""
        # Schedule reset at midnight
        next_midnight = dt_util.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        
        cancel_callback = async_track_point_in_time(
            self.hass,
            self._daily_reset_callback,
            next_midnight
        )
        
        self._event_listeners.add(cancel_callback)

    @callback
    def _daily_reset_callback(self, now: datetime) -> None:
        """Callback for daily reset."""
        self._reset_daily_totals()
        # Schedule next day's reset
        self._schedule_daily_reset()

    def _reset_daily_totals(self) -> None:
        """Reset daily irrigation totals."""
        self._daily_irrigation_totals.clear()
        _LOGGER.debug("Daily irrigation totals reset")

    # Status and State Tracking Methods
    
    def get_room_status(self, room_id: str) -> Dict[str, Any]:
        """Get current status for a room."""
        status = {
            "active_irrigation": room_id in self._active_irrigations,
            "manual_run": room_id in self._manual_runs,
            "daily_total": self._daily_irrigation_totals.get(room_id, 0),
            "next_events": {},
            "last_events": {}
        }
        
        # Get next and last event times
        if room_id in self._rooms:
            room = self._rooms[room_id]
            for event in room.events:
                if event.enabled:
                    status["next_events"][event.event_type] = event.next_run
                    status["last_events"][event.event_type] = event.last_run
        
        # Add active irrigation details
        if room_id in self._active_irrigations:
            irrigation_state = self._active_irrigations[room_id]
            status["active_irrigation_details"] = {
                "event_type": irrigation_state.get("event_type"),
                "current_shot": irrigation_state.get("current_shot", 0),
                "total_shots": irrigation_state.get("total_shots", 0),
                "shot_start_time": irrigation_state.get("shot_start_time"),
                "shot_duration": irrigation_state.get("shot_duration", 0),
                "progress": irrigation_state.get("progress", 0)
            }
        
        # Add manual run details
        if room_id in self._manual_runs:
            manual_state = self._manual_runs[room_id]
            status["manual_run_details"] = {
                "start_time": manual_state.get("start_time"),
                "duration": manual_state.get("duration", 0),
                "remaining": manual_state.get("remaining", 0)
            }
        
        return status

    def get_all_room_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all rooms."""
        return {room_id: self.get_room_status(room_id) for room_id in self._rooms}

    async def async_get_irrigation_history(self, room_id: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """Get irrigation history."""
        return await self.storage.async_get_history(room_id, days)

    # Irrigation Execution Methods
    
    async def async_execute_irrigation_event(self, room_id: str, event_type: str) -> bool:
        """Execute an irrigation event for a room."""
        try:
            # Check if room exists
            if room_id not in self._rooms:
                _LOGGER.error("Room %s not found", room_id)
                return False
            
            room = self._rooms[room_id]
            event = room.get_event(event_type)
            
            if not event:
                _LOGGER.error("Event %s not found for room %s", event_type, room_id)
                return False
            
            if not event.enabled:
                _LOGGER.warning("Event %s is disabled for room %s", event_type, room_id)
                return False
            
            # Check if already running irrigation
            if room_id in self._active_irrigations:
                _LOGGER.warning("Irrigation already active for room %s", room_id)
                return False
            
            # Perform fail-safe checks
            fail_safe_result = await self._check_fail_safes(room_id, event.get_total_duration())
            if not fail_safe_result["allowed"]:
                _LOGGER.warning(
                    "Fail-safe check failed for room %s: %s", 
                    room_id, fail_safe_result["reason"]
                )
                await self.storage.async_add_history_event(
                    room_id, event_type, 0, False, fail_safe_result["reason"]
                )
                
                # Send error notification for fail-safe issues
                await self.send_error_notification(
                    f"Irrigation blocked by fail-safe: {fail_safe_result['reason']}", room_id
                )
                
                return False
            
            # Start irrigation execution
            _LOGGER.info("Starting %s irrigation for room %s", event_type, room_id)
            
            # Initialize irrigation state
            irrigation_state = {
                "event_type": event_type,
                "shots": event.shots,
                "current_shot": 0,
                "total_shots": len(event.shots),
                "start_time": dt_util.now(),
                "shot_start_time": None,
                "shot_duration": 0,
                "progress": 0,
                "total_duration": event.get_total_duration()
            }
            
            self._active_irrigations[room_id] = irrigation_state
            
            # Execute shots sequentially
            success = await self._execute_irrigation_shots(room_id, event.shots)
            
            # Clean up irrigation state
            if room_id in self._active_irrigations:
                del self._active_irrigations[room_id]
            
            # Update daily totals
            if success:
                actual_duration = event.get_total_duration()
                self._daily_irrigation_totals[room_id] = (
                    self._daily_irrigation_totals.get(room_id, 0) + actual_duration
                )
            
            # Add to history
            await self.storage.async_add_history_event(
                room_id, event_type, event.get_total_duration(), success
            )
            
            # Record performance metrics
            await self.storage.async_record_irrigation_cycle(success, event.get_total_duration())
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info(
                "Irrigation %s for room %s: %s", 
                event_type, room_id, "completed" if success else "failed"
            )
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error executing irrigation event for room %s: %s", room_id, e)
            
            # Clean up on error
            if room_id in self._active_irrigations:
                del self._active_irrigations[room_id]
            
            # Add failed event to history
            await self.storage.async_add_history_event(
                room_id, event_type, 0, False, str(e)
            )
            
            # Record failed performance metrics
            await self.storage.async_record_irrigation_cycle(False, 0)
            
            # Send error notification if enabled
            await self.send_error_notification(
                f"Irrigation failed: {str(e)}", room_id
            )
            
            return False

    async def _execute_irrigation_shots(self, room_id: str, shots: List[Shot]) -> bool:
        """Execute a sequence of irrigation shots."""
        try:
            room = self._rooms[room_id]
            irrigation_state = self._active_irrigations[room_id]
            
            for i, shot in enumerate(shots):
                # Update current shot info
                irrigation_state["current_shot"] = i
                irrigation_state["shot_start_time"] = dt_util.now()
                irrigation_state["shot_duration"] = shot.duration
                irrigation_state["progress"] = i / len(shots)
                
                _LOGGER.debug(
                    "Executing shot %d/%d for room %s (duration: %ds)", 
                    i + 1, len(shots), room_id, shot.duration
                )
                
                # Start pump and zones
                pump_success = await self._activate_pump(room_id, room.pump_entity)
                if not pump_success:
                    _LOGGER.error("Failed to activate pump for room %s", room_id)
                    return False
                
                # Wait for pump stabilization (3-second delay)
                pump_delay = self._settings.get("pump_zone_delay", 3)
                await asyncio.sleep(pump_delay)
                
                # Activate zones
                zones_success = await self._activate_zones(room_id, room.zone_entities)
                if not zones_success:
                    _LOGGER.error("Failed to activate zones for room %s", room_id)
                    # Still try to turn off pump
                    await self._deactivate_pump(room_id, room.pump_entity)
                    return False
                
                # Run shot for specified duration
                await asyncio.sleep(shot.duration)
                
                # Deactivate zones first
                await self._deactivate_zones(room_id, room.zone_entities)
                
                # Deactivate pump
                await self._deactivate_pump(room_id, room.pump_entity)
                
                # Wait for interval before next shot (if not last shot)
                if i < len(shots) - 1 and shot.interval_after > 0:
                    _LOGGER.debug(
                        "Waiting %ds before next shot for room %s", 
                        shot.interval_after, room_id
                    )
                    await asyncio.sleep(shot.interval_after)
                
                # Check if irrigation was stopped externally
                if room_id not in self._active_irrigations:
                    _LOGGER.info("Irrigation stopped externally for room %s", room_id)
                    return False
            
            # Update final progress
            irrigation_state["progress"] = 1.0
            
            return True
            
        except Exception as e:
            _LOGGER.error("Error executing irrigation shots for room %s: %s", room_id, e)
            
            # Emergency cleanup - turn off all devices
            try:
                room = self._rooms[room_id]
                await self._deactivate_zones(room_id, room.zone_entities)
                await self._deactivate_pump(room_id, room.pump_entity)
            except Exception as cleanup_error:
                _LOGGER.error("Error during emergency cleanup: %s", cleanup_error)
            
            return False

    async def async_start_manual_run(self, room_id: str, duration: int) -> bool:
        """Start a manual irrigation run."""
        try:
            # Validate inputs
            if room_id not in self._rooms:
                _LOGGER.error("Room %s not found", room_id)
                return False
            
            if duration <= 0 or duration > 3600:  # Max 1 hour
                _LOGGER.error("Invalid duration %d for manual run", duration)
                return False
            
            # Check if already running
            if room_id in self._active_irrigations or room_id in self._manual_runs:
                _LOGGER.warning("Irrigation already active for room %s", room_id)
                return False
            
            # Perform fail-safe checks
            fail_safe_result = await self._check_fail_safes(room_id, duration)
            if not fail_safe_result["allowed"]:
                _LOGGER.warning(
                    "Fail-safe check failed for manual run on room %s: %s", 
                    room_id, fail_safe_result["reason"]
                )
                return False
            
            room = self._rooms[room_id]
            
            _LOGGER.info("Starting manual run for room %s (duration: %ds)", room_id, duration)
            
            # Initialize manual run state
            manual_state = {
                "start_time": dt_util.now(),
                "duration": duration,
                "remaining": duration
            }
            
            self._manual_runs[room_id] = manual_state
            
            # Start pump and zones
            pump_success = await self._activate_pump(room_id, room.pump_entity)
            if not pump_success:
                del self._manual_runs[room_id]
                return False
            
            # Wait for pump stabilization
            pump_delay = self._settings.get("pump_zone_delay", 3)
            await asyncio.sleep(pump_delay)
            
            # Activate zones
            zones_success = await self._activate_zones(room_id, room.zone_entities)
            if not zones_success:
                await self._deactivate_pump(room_id, room.pump_entity)
                del self._manual_runs[room_id]
                return False
            
            # Schedule automatic stop
            stop_time = dt_util.now() + timedelta(seconds=duration)
            cancel_callback = async_track_point_in_time(
                self.hass,
                lambda dt: self.hass.async_create_task(
                    self.async_stop_manual_run(room_id)
                ),
                stop_time
            )
            
            manual_state["cancel_callback"] = cancel_callback
            
            # Update daily totals
            self._daily_irrigation_totals[room_id] = (
                self._daily_irrigation_totals.get(room_id, 0) + duration
            )
            
            # Add to history
            await self.storage.async_add_history_event(
                room_id, "manual", duration, True
            )
            
            # Trigger data update
            await self.async_request_refresh()
            
            return True
            
        except Exception as e:
            _LOGGER.error("Error starting manual run for room %s: %s", room_id, e)
            
            # Cleanup on error
            if room_id in self._manual_runs:
                del self._manual_runs[room_id]
            
            return False

    async def async_stop_manual_run(self, room_id: str) -> bool:
        """Stop a manual irrigation run."""
        try:
            if room_id not in self._manual_runs:
                _LOGGER.warning("No manual run active for room %s", room_id)
                return False
            
            manual_state = self._manual_runs[room_id]
            room = self._rooms[room_id]
            
            _LOGGER.info("Stopping manual run for room %s", room_id)
            
            # Cancel scheduled stop if exists
            if "cancel_callback" in manual_state:
                manual_state["cancel_callback"]()
            
            # Deactivate zones and pump
            await self._deactivate_zones(room_id, room.zone_entities)
            await self._deactivate_pump(room_id, room.pump_entity)
            
            # Clean up state
            del self._manual_runs[room_id]
            
            # Trigger data update
            await self.async_request_refresh()
            
            return True
            
        except Exception as e:
            _LOGGER.error("Error stopping manual run for room %s: %s", room_id, e)
            return False

    async def async_stop_irrigation(self, room_id: str) -> bool:
        """Stop any active irrigation for a room."""
        try:
            stopped = False
            
            # Stop manual run if active
            if room_id in self._manual_runs:
                await self.async_stop_manual_run(room_id)
                stopped = True
            
            # Stop scheduled irrigation if active
            if room_id in self._active_irrigations:
                room = self._rooms[room_id]
                
                # Emergency stop - turn off all devices
                await self._deactivate_zones(room_id, room.zone_entities)
                await self._deactivate_pump(room_id, room.pump_entity)
                
                # Clean up state
                del self._active_irrigations[room_id]
                
                _LOGGER.info("Stopped active irrigation for room %s", room_id)
                stopped = True
            
            if stopped:
                # Trigger data update
                await self.async_request_refresh()
            
            return stopped
            
        except Exception as e:
            _LOGGER.error("Error stopping irrigation for room %s: %s", room_id, e)
            return False

    # Hardware Control Methods
    
    async def _activate_pump(self, room_id: str, pump_entity: str) -> bool:
        """Activate pump for a room."""
        try:
            # Check entity availability
            state = self.hass.states.get(pump_entity)
            if not state or state.state == "unavailable":
                _LOGGER.error("Pump entity %s is unavailable", pump_entity)
                return False
            
            # Turn on pump
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": pump_entity}
            )
            
            _LOGGER.debug("Activated pump %s for room %s", pump_entity, room_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to activate pump %s: %s", pump_entity, e)
            return False

    async def _deactivate_pump(self, room_id: str, pump_entity: str) -> bool:
        """Deactivate pump for a room."""
        try:
            # Turn off pump
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": pump_entity}
            )
            
            _LOGGER.debug("Deactivated pump %s for room %s", pump_entity, room_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to deactivate pump %s: %s", pump_entity, e)
            return False

    async def _activate_zones(self, room_id: str, zone_entities: List[str]) -> bool:
        """Activate all zones for a room."""
        try:
            if not zone_entities:
                _LOGGER.debug("No zones configured for room %s", room_id)
                return True
            
            success_count = 0
            
            for zone_entity in zone_entities:
                # Check entity availability
                state = self.hass.states.get(zone_entity)
                if not state or state.state == "unavailable":
                    _LOGGER.warning("Zone entity %s is unavailable", zone_entity)
                    continue
                
                try:
                    # Turn on zone
                    await self.hass.services.async_call(
                        "switch", "turn_on", {"entity_id": zone_entity}
                    )
                    success_count += 1
                    _LOGGER.debug("Activated zone %s for room %s", zone_entity, room_id)
                    
                except Exception as e:
                    _LOGGER.error("Failed to activate zone %s: %s", zone_entity, e)
            
            # Consider success if at least one zone activated
            return success_count > 0
            
        except Exception as e:
            _LOGGER.error("Failed to activate zones for room %s: %s", room_id, e)
            return False

    async def _deactivate_zones(self, room_id: str, zone_entities: List[str]) -> bool:
        """Deactivate all zones for a room."""
        try:
            if not zone_entities:
                return True
            
            for zone_entity in zone_entities:
                try:
                    # Turn off zone
                    await self.hass.services.async_call(
                        "switch", "turn_off", {"entity_id": zone_entity}
                    )
                    _LOGGER.debug("Deactivated zone %s for room %s", zone_entity, room_id)
                    
                except Exception as e:
                    _LOGGER.error("Failed to deactivate zone %s: %s", zone_entity, e)
            
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to deactivate zones for room %s: %s", room_id, e)
            return False 
   # Fail-Safe and Safety Mechanisms
    
    async def _check_fail_safes(self, room_id: str, duration: int) -> Dict[str, Any]:
        """Check all fail-safe conditions before allowing irrigation."""
        with IrrigationErrorHandler("fail_safe_check", self.irrigation_logger, suppress_exceptions=True):
            result = {"allowed": True, "reason": ""}
            
            try:
                # Check if fail-safes are enabled
                if not self._settings.get("fail_safe_enabled", True):
                    self.irrigation_logger.debug("Fail-safes disabled, allowing irrigation", room_id=room_id)
                    return result
                
                room = self._rooms.get(room_id)
                if not room:
                    error_result = {"allowed": False, "reason": "Room not found"}
                    self.irrigation_logger.fail_safe_trigger(room_id, "Room not found", "room_existence")
                    return error_result
                
                # Check light schedule integration
                light_check = await self._check_light_schedule(room_id, room)
                if not light_check["allowed"]:
                    self.irrigation_logger.fail_safe_trigger(
                        room_id, light_check["reason"], "light_schedule",
                        light_entity=room.light_entity
                    )
                    return light_check
                
                # Check entity availability
                entity_check = await self._check_entity_availability(room_id, room)
                if not entity_check["allowed"]:
                    self.irrigation_logger.fail_safe_trigger(
                        room_id, entity_check["reason"], "entity_availability"
                    )
                    return entity_check
                
                # Check over-watering prevention
                overwater_check = await self._check_overwatering_prevention(room_id, duration)
                if not overwater_check["allowed"]:
                    self.irrigation_logger.fail_safe_trigger(
                        room_id, overwater_check["reason"], "overwatering_prevention",
                        current_total=self._daily_irrigation_totals.get(room_id, 0),
                        requested_duration=duration
                    )
                    return overwater_check
                
                # Check for conflicting irrigations
                conflict_check = self._check_irrigation_conflicts(room_id)
                if not conflict_check["allowed"]:
                    self.irrigation_logger.fail_safe_trigger(
                        room_id, conflict_check["reason"], "irrigation_conflict"
                    )
                    return conflict_check
                
                self.irrigation_logger.debug("All fail-safe checks passed", room_id=room_id)
                return result
                
            except Exception as e:
                self._record_error("fail_safe_check", e, room_id=room_id)
                error_result = {"allowed": False, "reason": f"Fail-safe check error: {e}"}
                self.irrigation_logger.fail_safe_trigger(
                    room_id, f"Check error: {e}", "system_error", error=str(e)
                )
                return error_result

    async def _check_light_schedule(self, room_id: str, room: Room) -> Dict[str, Any]:
        """Check light schedule integration and validation."""
        try:
            # Skip if no light entity configured
            if not room.light_entity:
                return {"allowed": True, "reason": ""}
            
            # Get light entity state
            light_state = self.hass.states.get(room.light_entity)
            if not light_state:
                _LOGGER.warning("Light entity %s not found for room %s", room.light_entity, room_id)
                return {"allowed": True, "reason": ""}  # Allow if light entity missing
            
            if light_state.state == "unavailable":
                return {
                    "allowed": False, 
                    "reason": f"Light entity {room.light_entity} is unavailable"
                }
            
            # Check if lights are on (irrigation should only happen when lights are on)
            if light_state.state == "off":
                return {
                    "allowed": False,
                    "reason": "Irrigation blocked: lights are off (light schedule conflict)"
                }
            
            return {"allowed": True, "reason": ""}
            
        except Exception as e:
            _LOGGER.error("Error checking light schedule for room %s: %s", room_id, e)
            return {"allowed": False, "reason": f"Light schedule check error: {e}"}

    async def _check_entity_availability(self, room_id: str, room: Room) -> Dict[str, Any]:
        """Check availability of all required entities before irrigation."""
        try:
            unavailable_entities = []
            
            # Check pump entity
            pump_state = self.hass.states.get(room.pump_entity)
            if not pump_state or pump_state.state == "unavailable":
                unavailable_entities.append(f"pump: {room.pump_entity}")
            
            # Check zone entities
            for zone_entity in room.zone_entities:
                zone_state = self.hass.states.get(zone_entity)
                if not zone_state or zone_state.state == "unavailable":
                    unavailable_entities.append(f"zone: {zone_entity}")
            
            if unavailable_entities:
                return {
                    "allowed": False,
                    "reason": f"Unavailable entities: {', '.join(unavailable_entities)}"
                }
            
            return {"allowed": True, "reason": ""}
            
        except Exception as e:
            _LOGGER.error("Error checking entity availability for room %s: %s", room_id, e)
            return {"allowed": False, "reason": f"Entity availability check error: {e}"}

    async def _check_overwatering_prevention(self, room_id: str, duration: int) -> Dict[str, Any]:
        """Check over-watering prevention with daily limits."""
        try:
            max_daily = self._settings.get("max_daily_irrigation", 3600)  # Default 1 hour
            current_daily = self._daily_irrigation_totals.get(room_id, 0)
            
            if current_daily + duration > max_daily:
                remaining = max_daily - current_daily
                return {
                    "allowed": False,
                    "reason": f"Daily irrigation limit exceeded. Remaining: {remaining}s of {max_daily}s"
                }
            
            return {"allowed": True, "reason": ""}
            
        except Exception as e:
            _LOGGER.error("Error checking overwatering prevention for room %s: %s", room_id, e)
            return {"allowed": False, "reason": f"Overwatering check error: {e}"}

    def _check_irrigation_conflicts(self, room_id: str) -> Dict[str, Any]:
        """Check for conflicting irrigation activities."""
        try:
            # Check if irrigation is already active
            if room_id in self._active_irrigations:
                return {
                    "allowed": False,
                    "reason": "Scheduled irrigation already active for this room"
                }
            
            # Check if manual run is active
            if room_id in self._manual_runs:
                return {
                    "allowed": False,
                    "reason": "Manual irrigation run already active for this room"
                }
            
            return {"allowed": True, "reason": ""}
            
        except Exception as e:
            _LOGGER.error("Error checking irrigation conflicts for room %s: %s", room_id, e)
            return {"allowed": False, "reason": f"Conflict check error: {e}"}

    async def async_emergency_stop_all(self) -> Dict[str, bool]:
        """Emergency stop all irrigation activities."""
        results = {}
        
        try:
            _LOGGER.warning("Emergency stop initiated for all rooms")
            
            # Stop all active irrigations
            for room_id in list(self._active_irrigations.keys()):
                results[f"{room_id}_irrigation"] = await self.async_stop_irrigation(room_id)
            
            # Stop all manual runs
            for room_id in list(self._manual_runs.keys()):
                results[f"{room_id}_manual"] = await self.async_stop_manual_run(room_id)
            
            # Turn off all pumps and zones as safety measure
            for room_id, room in self._rooms.items():
                try:
                    await self._deactivate_zones(room_id, room.zone_entities)
                    await self._deactivate_pump(room_id, room.pump_entity)
                    results[f"{room_id}_safety_shutoff"] = True
                except Exception as e:
                    _LOGGER.error("Failed safety shutoff for room %s: %s", room_id, e)
                    results[f"{room_id}_safety_shutoff"] = False
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info("Emergency stop completed")
            return results
            
        except Exception as e:
            _LOGGER.error("Error during emergency stop: %s", e)
            return {"error": False}

    async def async_emergency_stop_room(self, room_id: str) -> bool:
        """Emergency stop for a specific room."""
        try:
            _LOGGER.warning("Emergency stop initiated for room %s", room_id)
            
            if room_id not in self._rooms:
                return False
            
            room = self._rooms[room_id]
            
            # Stop any active irrigation
            await self.async_stop_irrigation(room_id)
            
            # Safety shutoff - turn off all devices
            await self._deactivate_zones(room_id, room.zone_entities)
            await self._deactivate_pump(room_id, room.pump_entity)
            
            # Trigger data update
            await self.async_request_refresh()
            
            _LOGGER.info("Emergency stop completed for room %s", room_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error during emergency stop for room %s: %s", room_id, e)
            return False

    def get_fail_safe_status(self) -> Dict[str, Any]:
        """Get current fail-safe system status."""
        return {
            "enabled": self._settings.get("fail_safe_enabled", True),
            "emergency_stop_enabled": self._settings.get("emergency_stop_enabled", True),
            "max_daily_irrigation": self._settings.get("max_daily_irrigation", 3600),
            "daily_totals": self._daily_irrigation_totals.copy(),
            "active_irrigations": len(self._active_irrigations),
            "active_manual_runs": len(self._manual_runs)
        }

    async def async_validate_room_safety(self, room_id: str) -> Dict[str, Any]:
        """Validate safety conditions for a specific room."""
        if room_id not in self._rooms:
            return {"valid": False, "issues": ["Room not found"]}
        
        room = self._rooms[room_id]
        issues = []
        
        # Check entity availability
        missing_entities = await room.validate_entities_exist(self.hass)
        if missing_entities:
            issues.extend([f"Missing entity: {entity}" for entity in missing_entities])
        
        # Check light entity if configured
        if room.light_entity:
            light_state = self.hass.states.get(room.light_entity)
            if not light_state:
                issues.append(f"Light entity not found: {room.light_entity}")
            elif light_state.state == "unavailable":
                issues.append(f"Light entity unavailable: {room.light_entity}")
        
        # Check daily limits
        current_daily = self._daily_irrigation_totals.get(room_id, 0)
        max_daily = self._settings.get("max_daily_irrigation", 3600)
        if current_daily >= max_daily:
            issues.append(f"Daily irrigation limit reached: {current_daily}/{max_daily}s")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "daily_usage": current_daily,
            "daily_limit": max_daily,
            "remaining_daily": max(0, max_daily - current_daily)
        }

    # System Health and Monitoring
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        health = {
            "status": "healthy",
            "issues": [],
            "rooms_count": len(self._rooms),
            "active_irrigations": len(self._active_irrigations),
            "active_manual_runs": len(self._manual_runs),
            "scheduled_events": sum(len(events) for events in self._scheduled_events.values()),
            "fail_safe_enabled": self._settings.get("fail_safe_enabled", True),
            "daily_totals": self._daily_irrigation_totals.copy()
        }
        
        # Check for issues
        issues = []
        
        # Check for long-running irrigations
        now = dt_util.now()
        for room_id, irrigation_state in self._active_irrigations.items():
            start_time = irrigation_state.get("start_time")
            if start_time and (now - start_time).total_seconds() > 7200:  # 2 hours
                issues.append(f"Long-running irrigation in room {room_id}")
        
        # Check for long-running manual runs
        for room_id, manual_state in self._manual_runs.items():
            start_time = manual_state.get("start_time")
            if start_time and (now - start_time).total_seconds() > 3600:  # 1 hour
                issues.append(f"Long-running manual run in room {room_id}")
        
        # Check daily limits
        max_daily = self._settings.get("max_daily_irrigation", 3600)
        for room_id, daily_total in self._daily_irrigation_totals.items():
            if daily_total >= max_daily:
                issues.append(f"Daily limit reached for room {room_id}")
        
        if issues:
            health["status"] = "warning" if len(issues) < 3 else "critical"
            health["issues"] = issues
        
        return health

    def _update_logging_level(self, level: str) -> None:
        """Update logging level for the irrigation addon."""
        try:
            import logging
            
            # Map string levels to logging constants
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR
            }
            
            if level in level_map:
                # Update logger for this module and related modules
                loggers = [
                    logging.getLogger(__name__),
                    logging.getLogger("custom_components.irrigation_addon"),
                    logging.getLogger("custom_components.irrigation_addon.coordinator"),
                    logging.getLogger("custom_components.irrigation_addon.storage"),
                    logging.getLogger("custom_components.irrigation_addon.services"),
                    logging.getLogger("custom_components.irrigation_addon.config_flow"),
                ]
                
                for logger in loggers:
                    logger.setLevel(level_map[level])
                
                _LOGGER.info("Logging level updated to %s", level)
            else:
                _LOGGER.warning("Invalid logging level: %s", level)
                
        except Exception as e:
            _LOGGER.error("Failed to update logging level: %s", e)

    def should_send_notification(self, notification_type: str = "general") -> bool:
        """Check if notifications should be sent based on settings."""
        if not self._settings.get("notifications_enabled", True):
            return False
        
        if notification_type == "error" and not self._settings.get("error_notifications", True):
            return False
        
        return True

    async def send_notification(self, message: str, title: str = "Irrigation System", 
                              notification_type: str = "general") -> None:
        """Send a notification if enabled in settings."""
        if not self.should_send_notification(notification_type):
            return
        
        try:
            # Send persistent notification to Home Assistant
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"irrigation_{notification_type}_{hash(message)}",
                }
            )
            
            _LOGGER.debug("Notification sent: %s", message)
            
        except Exception as e:
            _LOGGER.error("Failed to send notification: %s", e)

    async def send_error_notification(self, message: str, room_id: str = None) -> None:
        """Send an error notification if enabled."""
        title = f"Irrigation Error"
        if room_id:
            room_name = self._rooms.get(room_id, {}).get("name", room_id)
            title += f" - {room_name}"
        
        await self.send_notification(message, title, "error")

    # Error Tracking and Recovery Methods
    
    def _record_error(self, operation: str, error: Exception, **context) -> None:
        """Record an error for tracking and analysis."""
        error_info = {
            "timestamp": dt_util.now().isoformat(),
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        
        # Add to error history
        self._last_errors.append(error_info)
        if len(self._last_errors) > self._max_error_history:
            self._last_errors.pop(0)
        
        # Update error counts
        error_key = f"{operation}:{type(error).__name__}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        
        # Log structured error
        self.irrigation_logger.error(
            f"Error in {operation}: {error}",
            error=error,
            operation=operation,
            **context
        )
    
    async def _attempt_error_recovery(self, operation: str, error: Exception, 
                                    room_id: str = None, max_attempts: int = 3) -> bool:
        """Attempt to recover from an error with retry logic."""
        from .exceptions import ErrorRecovery
        
        if not ErrorRecovery.is_recoverable_error(error):
            self.irrigation_logger.warning(
                f"Error not recoverable: {operation}",
                error_type=type(error).__name__,
                room_id=room_id
            )
            return False
        
        for attempt in range(1, max_attempts + 1):
            if not ErrorRecovery.should_retry(error, attempt, max_attempts):
                break
            
            delay = ErrorRecovery.get_retry_delay(attempt)
            self.irrigation_logger.info(
                f"Attempting recovery for {operation} (attempt {attempt}/{max_attempts})",
                operation=operation,
                attempt=attempt,
                delay=delay,
                room_id=room_id
            )
            
            await asyncio.sleep(delay)
            
            try:
                # Attempt recovery based on operation type
                if operation == "hardware_control" and room_id:
                    # Try to reset hardware state
                    room = self._rooms.get(room_id)
                    if room:
                        await self._emergency_hardware_reset(room_id, room)
                        return True
                
                elif operation == "entity_availability":
                    # Wait and check if entities become available
                    await asyncio.sleep(5)  # Additional wait for entity recovery
                    if room_id:
                        room = self._rooms.get(room_id)
                        if room:
                            missing = await room.validate_entities_exist(self.hass)
                            if not missing:
                                return True
                
                elif operation == "scheduling":
                    # Try to reschedule events
                    if room_id:
                        room = self._rooms.get(room_id)
                        if room:
                            await self._schedule_room_events(room_id, room)
                            return True
                
            except Exception as recovery_error:
                self.irrigation_logger.warning(
                    f"Recovery attempt {attempt} failed for {operation}",
                    recovery_error=str(recovery_error),
                    room_id=room_id
                )
                continue
        
        self.irrigation_logger.error(
            f"All recovery attempts failed for {operation}",
            operation=operation,
            room_id=room_id,
            attempts=max_attempts
        )
        return False
    
    async def _emergency_hardware_reset(self, room_id: str, room: Room) -> None:
        """Emergency reset of hardware devices for a room."""
        try:
            self.irrigation_logger.warning(f"Emergency hardware reset for room {room_id}")
            
            # Turn off all zones first
            for zone_entity in room.zone_entities:
                try:
                    await self.hass.services.async_call(
                        "switch", "turn_off", {"entity_id": zone_entity}
                    )
                except Exception as e:
                    self.irrigation_logger.error(
                        f"Failed to turn off zone {zone_entity} during emergency reset",
                        error=e, room_id=room_id, entity_id=zone_entity
                    )
            
            # Turn off pump
            try:
                await self.hass.services.async_call(
                    "switch", "turn_off", {"entity_id": room.pump_entity}
                )
            except Exception as e:
                self.irrigation_logger.error(
                    f"Failed to turn off pump {room.pump_entity} during emergency reset",
                    error=e, room_id=room_id, entity_id=room.pump_entity
                )
            
            # Clear any active irrigation state
            self._active_irrigations.pop(room_id, None)
            self._manual_runs.pop(room_id, None)
            
            self.irrigation_logger.info(f"Emergency hardware reset completed for room {room_id}")
            
        except Exception as e:
            self.irrigation_logger.critical(
                f"Emergency hardware reset failed for room {room_id}",
                error=e, room_id=room_id
            )
            raise EmergencyStopError(
                f"room {room_id}",
                failed_operations=["emergency_hardware_reset"],
                underlying_error=e
            )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and diagnostics."""
        return {
            "total_errors": len(self._last_errors),
            "error_counts": self._error_counts.copy(),
            "recent_errors": self._last_errors[-10:],  # Last 10 errors
            "error_rate": self._calculate_error_rate(),
            "most_common_errors": self._get_most_common_errors()
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate per hour based on recent errors."""
        if not self._last_errors:
            return 0.0
        
        now = dt_util.now()
        hour_ago = now - timedelta(hours=1)
        
        recent_errors = [
            error for error in self._last_errors
            if datetime.fromisoformat(error["timestamp"]) > hour_ago
        ]
        
        return len(recent_errors)
    
    def _get_most_common_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most common error types."""
        sorted_errors = sorted(
            self._error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"error_type": error_type, "count": count}
            for error_type, count in sorted_errors[:limit]
        ]
    
    async def get_comprehensive_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic information."""
        try:
            system_info = await self.diagnostic_collector.collect_system_info()
            
            diagnostics = {
                "system_info": system_info,
                "coordinator_status": {
                    "rooms_count": len(self._rooms),
                    "active_irrigations": len(self._active_irrigations),
                    "active_manual_runs": len(self._manual_runs),
                    "scheduled_events": sum(len(events) for events in self._scheduled_events.values()),
                    "daily_totals": self._daily_irrigation_totals.copy()
                },
                "error_statistics": self.get_error_statistics(),
                "performance_metrics": self.performance_tracker.get_all_metrics(),
                "system_health": self.get_system_health(),
                "fail_safe_status": self.get_fail_safe_status()
            }
            
            # Add room-specific diagnostics
            room_diagnostics = {}
            for room_id in self._rooms:
                room_diagnostics[room_id] = await self.diagnostic_collector.collect_room_diagnostics(
                    room_id, self
                )
            
            diagnostics["room_diagnostics"] = room_diagnostics
            
            return diagnostics
            
        except Exception as e:
            self.irrigation_logger.error("Failed to collect comprehensive diagnostics", error=e)
            return {"error": str(e)}
    
    async def export_diagnostics_file(self) -> str:
        """Export diagnostics to a file and return the file path."""
        try:
            diagnostics = await self.get_comprehensive_diagnostics()
            return self.diagnostic_collector.export_diagnostics(diagnostics)
        except Exception as e:
            self.irrigation_logger.error("Failed to export diagnostics file", error=e)
            return ""