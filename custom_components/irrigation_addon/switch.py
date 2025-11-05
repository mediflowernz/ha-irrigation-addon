"""Switch entities for the Irrigation Addon integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import IrrigationCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Create switches for each room
    for room_id, room in coordinator.rooms.items():
        # Manual irrigation control switch
        entities.append(ManualIrrigationSwitch(coordinator, entry, room_id))
        
        # Room emergency stop switch
        entities.append(RoomEmergencyStopSwitch(coordinator, entry, room_id))
        
        # Event enable/disable switches for each event type
        for event in room.events:
            entities.append(EventControlSwitch(coordinator, entry, room_id, event.event_type))
    
    # System-wide switches
    entities.extend([
        FailSafeSwitch(coordinator, entry),
        EmergencyStopSwitch(coordinator, entry),
    ])
    
    async_add_entities(entities)


class IrrigationSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base class for irrigation switches."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: Optional[str] = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entry = entry
        self.room_id = room_id
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self.room_id:
            room = self.coordinator.rooms.get(self.room_id)
            room_name = room.name if room else f"Room {self.room_id}"
            return DeviceInfo(
                identifiers={(DOMAIN, f"room_{self.room_id}")},
                name=f"Irrigation - {room_name}",
                manufacturer="Irrigation Addon",
                model="Room Controller",
                via_device=(DOMAIN, self.entry.entry_id),
            )
        else:
            return DeviceInfo(
                identifiers={(DOMAIN, self.entry.entry_id)},
                name="Irrigation System",
                manufacturer="Irrigation Addon",
                model="System Controller",
            )


class ManualIrrigationSwitch(IrrigationSwitchBase):
    """Switch for manual irrigation control."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_manual_irrigation"
        self._attr_name = "Manual Irrigation"
        self._attr_icon = "mdi:sprinkler-variant"

    @property
    def is_on(self) -> bool:
        """Return true if manual irrigation is running."""
        status = self.coordinator.get_room_status(self.room_id)
        return status.get("manual_run", False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.get_room_status(self.room_id)
        
        attributes = {}
        
        if status.get("manual_run_details"):
            details = status["manual_run_details"]
            attributes.update({
                "duration": details.get("duration", 0),
                "remaining": details.get("remaining", 0),
                "start_time": details.get("start_time"),
            })
        
        # Add default manual duration from settings
        default_duration = self.coordinator.settings.get("default_manual_duration", 300)
        attributes["default_duration"] = default_duration
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on manual irrigation."""
        try:
            # Use default duration from settings
            duration = self.coordinator.settings.get("default_manual_duration", 300)
            
            success = await self.coordinator.async_start_manual_run(self.room_id, duration)
            
            if not success:
                raise HomeAssistantError(f"Failed to start manual irrigation for room {self.room_id}")
            
            # Request coordinator update
            await self.coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Error turning on manual irrigation for room %s: %s", self.room_id, e)
            raise HomeAssistantError(f"Failed to start manual irrigation: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off manual irrigation."""
        try:
            success = await self.coordinator.async_stop_manual_run(self.room_id)
            
            if not success:
                _LOGGER.warning("No manual irrigation was running for room %s", self.room_id)
            
            # Request coordinator update
            await self.coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Error turning off manual irrigation for room %s: %s", self.room_id, e)
            raise HomeAssistantError(f"Failed to stop manual irrigation: {e}")


class EventControlSwitch(IrrigationSwitchBase):
    """Switch for enabling/disabling irrigation events."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
        event_type: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, room_id)
        self.event_type = event_type
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_event_{event_type.lower()}"
        self._attr_name = f"{event_type} Event"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def is_on(self) -> bool:
        """Return true if the event is enabled."""
        room = self.coordinator.rooms.get(self.room_id)
        if not room:
            return False
        
        event = room.get_event(self.event_type)
        return event.enabled if event else False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        room = self.coordinator.rooms.get(self.room_id)
        if not room:
            return {}
        
        event = room.get_event(self.event_type)
        if not event:
            return {}
        
        attributes = {
            "event_type": self.event_type,
            "schedule": event.schedule,
            "shots_count": len(event.shots),
            "total_duration": event.get_total_duration(),
        }
        
        if event.next_run:
            attributes["next_run"] = event.next_run.isoformat()
        
        if event.last_run:
            attributes["last_run"] = event.last_run.isoformat()
        
        # Add shot details
        shot_details = []
        for i, shot in enumerate(event.shots):
            shot_details.append({
                "index": i,
                "duration": shot.duration,
                "interval_after": shot.interval_after,
            })
        attributes["shots"] = shot_details
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the irrigation event."""
        try:
            room = await self.coordinator.async_get_room(self.room_id)
            if not room:
                raise HomeAssistantError(f"Room {self.room_id} not found")
            
            event = room.get_event(self.event_type)
            if not event:
                raise HomeAssistantError(f"Event {self.event_type} not found for room {self.room_id}")
            
            # Enable the event
            event.enabled = True
            
            # Save updated room
            await self.coordinator.async_update_room(room)
            
        except Exception as e:
            _LOGGER.error("Error enabling event %s for room %s: %s", self.event_type, self.room_id, e)
            raise HomeAssistantError(f"Failed to enable event: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the irrigation event."""
        try:
            room = await self.coordinator.async_get_room(self.room_id)
            if not room:
                raise HomeAssistantError(f"Room {self.room_id} not found")
            
            event = room.get_event(self.event_type)
            if not event:
                raise HomeAssistantError(f"Event {self.event_type} not found for room {self.room_id}")
            
            # Disable the event
            event.enabled = False
            
            # Save updated room
            await self.coordinator.async_update_room(room)
            
        except Exception as e:
            _LOGGER.error("Error disabling event %s for room %s: %s", self.event_type, self.room_id, e)
            raise HomeAssistantError(f"Failed to disable event: {e}")


class FailSafeSwitch(IrrigationSwitchBase):
    """Switch for enabling/disabling fail-safe mechanisms."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fail_safe"
        self._attr_name = "Fail Safe"
        self._attr_icon = "mdi:shield-check"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return true if fail-safe is enabled."""
        return self.coordinator.settings.get("fail_safe_enabled", True)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        fail_safe = self.coordinator.get_fail_safe_status()
        
        return {
            "max_daily_irrigation": fail_safe.get("max_daily_irrigation", 0),
            "emergency_stop_enabled": fail_safe.get("emergency_stop_enabled", True),
            "active_irrigations": fail_safe.get("active_irrigations", 0),
            "active_manual_runs": fail_safe.get("active_manual_runs", 0),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable fail-safe mechanisms."""
        try:
            await self.coordinator.async_update_settings({"fail_safe_enabled": True})
            
        except Exception as e:
            _LOGGER.error("Error enabling fail-safe: %s", e)
            raise HomeAssistantError(f"Failed to enable fail-safe: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable fail-safe mechanisms."""
        try:
            await self.coordinator.async_update_settings({"fail_safe_enabled": False})
            
        except Exception as e:
            _LOGGER.error("Error disabling fail-safe: %s", e)
            raise HomeAssistantError(f"Failed to disable fail-safe: {e}")


class EmergencyStopSwitch(IrrigationSwitchBase):
    """Switch for emergency stop functionality."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_emergency_stop"
        self._attr_name = "Emergency Stop"
        self._attr_icon = "mdi:stop-circle"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return false - this is a momentary switch."""
        # Emergency stop is always "off" - it's a momentary action
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        health = self.coordinator.get_system_health()
        
        return {
            "active_irrigations": health.get("active_irrigations", 0),
            "active_manual_runs": health.get("active_manual_runs", 0),
            "total_active": health.get("active_irrigations", 0) + health.get("active_manual_runs", 0),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Execute emergency stop for all rooms."""
        try:
            _LOGGER.warning("Emergency stop activated via switch")
            
            results = await self.coordinator.async_emergency_stop_all()
            
            # Check if any operations failed
            failed_operations = [op for op, success in results.items() if not success]
            if failed_operations:
                _LOGGER.warning("Some emergency stop operations failed: %s", failed_operations)
                raise HomeAssistantError(f"Emergency stop partially failed: {failed_operations}")
            
            _LOGGER.info("Emergency stop completed successfully")
            
        except Exception as e:
            _LOGGER.error("Error during emergency stop: %s", e)
            raise HomeAssistantError(f"Emergency stop failed: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off does nothing - this is a momentary switch."""
        # Emergency stop switch doesn't have an "off" action
        pass


class RoomEmergencyStopSwitch(IrrigationSwitchBase):
    """Switch for room-specific emergency stop."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_emergency_stop"
        self._attr_name = "Emergency Stop"
        self._attr_icon = "mdi:stop-circle"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return false - this is a momentary switch."""
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.get_room_status(self.room_id)
        
        return {
            "active_irrigation": status.get("active_irrigation", False),
            "manual_run": status.get("manual_run", False),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Execute emergency stop for this room."""
        try:
            _LOGGER.warning("Emergency stop activated for room %s via switch", self.room_id)
            
            success = await self.coordinator.async_emergency_stop_room(self.room_id)
            
            if not success:
                raise HomeAssistantError(f"Emergency stop failed for room {self.room_id}")
            
            _LOGGER.info("Emergency stop completed for room %s", self.room_id)
            
        except Exception as e:
            _LOGGER.error("Error during emergency stop for room %s: %s", self.room_id, e)
            raise HomeAssistantError(f"Emergency stop failed: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off does nothing - this is a momentary switch."""
        pass