"""Data models for the Irrigation Addon integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .const import EVENT_TYPE_P1, EVENT_TYPE_P2

_LOGGER = logging.getLogger(__name__)


@dataclass
class Shot:
    """Represents a single irrigation shot within an event."""
    
    duration: int  # Duration in seconds
    interval_after: int = 0  # Interval after this shot in seconds
    
    def __post_init__(self) -> None:
        """Validate shot data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate shot parameters."""
        if self.duration <= 0:
            raise ValueError("Shot duration must be greater than 0 seconds")
        
        if self.duration > 3600:  # 1 hour max
            raise ValueError("Shot duration cannot exceed 3600 seconds (1 hour)")
        
        if self.interval_after < 0:
            raise ValueError("Shot interval cannot be negative")
        
        if self.interval_after > 86400:  # 24 hours max
            raise ValueError("Shot interval cannot exceed 86400 seconds (24 hours)")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert shot to dictionary for storage."""
        return {
            "duration": self.duration,
            "interval_after": self.interval_after
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Shot:
        """Create shot from dictionary."""
        return cls(
            duration=data["duration"],
            interval_after=data.get("interval_after", 0)
        )


@dataclass
class IrrigationEvent:
    """Represents an irrigation event (P1 or P2) with multiple shots."""
    
    event_type: str  # P1 or P2
    shots: List[Shot] = field(default_factory=list)
    schedule: str = ""  # Cron expression
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate event data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate event parameters."""
        if self.event_type not in [EVENT_TYPE_P1, EVENT_TYPE_P2]:
            raise ValueError(f"Event type must be {EVENT_TYPE_P1} or {EVENT_TYPE_P2}")
        
        if not self.shots:
            raise ValueError("Event must have at least one shot")
        
        if len(self.shots) > 20:  # Reasonable limit
            raise ValueError("Event cannot have more than 20 shots")
        
        # Validate cron expression format if provided
        if self.schedule and not self._is_valid_cron(self.schedule):
            raise ValueError(f"Invalid cron expression: {self.schedule}")
        
        # Validate all shots
        for i, shot in enumerate(self.shots):
            try:
                shot.validate()
            except ValueError as e:
                raise ValueError(f"Shot {i + 1} validation failed: {e}")
    
    def _is_valid_cron(self, cron_expr: str) -> bool:
        """Validate cron expression format."""
        # Basic cron validation - 5 fields separated by spaces
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        
        # Each part should be valid cron field (numbers, *, /, -, ,)
        cron_pattern = r'^[\d\*\-\,\/]+$'
        return all(re.match(cron_pattern, part) for part in parts)
    
    def add_shot(self, shot: Shot) -> None:
        """Add a shot to the event."""
        if len(self.shots) >= 20:
            raise ValueError("Cannot add more than 20 shots to an event")
        
        shot.validate()
        self.shots.append(shot)
    
    def remove_shot(self, index: int) -> None:
        """Remove a shot by index."""
        if index < 0 or index >= len(self.shots):
            raise ValueError(f"Invalid shot index: {index}")
        
        self.shots.pop(index)
        
        if not self.shots:
            raise ValueError("Event must have at least one shot")
    
    def get_total_duration(self) -> int:
        """Calculate total duration of all shots including intervals."""
        if not self.shots:
            return 0
        
        total = sum(shot.duration for shot in self.shots)
        total += sum(shot.interval_after for shot in self.shots[:-1])  # No interval after last shot
        return total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "event_type": self.event_type,
            "shots": [shot.to_dict() for shot in self.shots],
            "schedule": self.schedule,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IrrigationEvent:
        """Create event from dictionary."""
        shots = [Shot.from_dict(shot_data) for shot_data in data.get("shots", [])]
        
        last_run = None
        if data.get("last_run"):
            try:
                last_run = datetime.fromisoformat(data["last_run"])
            except ValueError:
                _LOGGER.warning("Invalid last_run datetime format: %s", data["last_run"])
        
        next_run = None
        if data.get("next_run"):
            try:
                next_run = datetime.fromisoformat(data["next_run"])
            except ValueError:
                _LOGGER.warning("Invalid next_run datetime format: %s", data["next_run"])
        
        return cls(
            event_type=data["event_type"],
            shots=shots,
            schedule=data.get("schedule", ""),
            enabled=data.get("enabled", True),
            last_run=last_run,
            next_run=next_run
        )


@dataclass
class Room:
    """Represents a growing room with irrigation configuration."""
    
    room_id: str
    name: str
    pump_entity: str
    zone_entities: List[str] = field(default_factory=list)
    light_entity: Optional[str] = None
    sensors: Dict[str, str] = field(default_factory=dict)  # sensor_type -> entity_id
    events: List[IrrigationEvent] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate room data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate room configuration."""
        if not self.room_id:
            raise ValueError("Room ID cannot be empty")
        
        if not self.name:
            raise ValueError("Room name cannot be empty")
        
        if not self.pump_entity:
            raise ValueError("Room must have a pump entity")
        
        # Validate entity ID format (basic check)
        if not self._is_valid_entity_id(self.pump_entity):
            raise ValueError(f"Invalid pump entity ID format: {self.pump_entity}")
        
        # Validate zone entities
        for zone in self.zone_entities:
            if not self._is_valid_entity_id(zone):
                raise ValueError(f"Invalid zone entity ID format: {zone}")
        
        # Validate light entity if provided
        if self.light_entity and not self._is_valid_entity_id(self.light_entity):
            raise ValueError(f"Invalid light entity ID format: {self.light_entity}")
        
        # Validate sensor entities
        valid_sensor_types = ["soil_rh", "temperature", "ec", "ph", "humidity"]
        for sensor_type, entity_id in self.sensors.items():
            if sensor_type not in valid_sensor_types:
                raise ValueError(f"Invalid sensor type: {sensor_type}")
            
            if not self._is_valid_entity_id(entity_id):
                raise ValueError(f"Invalid sensor entity ID format: {entity_id}")
        
        # Validate events
        for i, event in enumerate(self.events):
            try:
                event.validate()
            except ValueError as e:
                raise ValueError(f"Event {i + 1} validation failed: {e}")
    
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Validate Home Assistant entity ID format."""
        # Basic entity ID validation: domain.entity_name
        pattern = r'^[a-z_]+\.[a-z0-9_]+$'
        return bool(re.match(pattern, entity_id))
    
    async def validate_entities_exist(self, hass: HomeAssistant) -> List[str]:
        """Validate that all configured entities exist in Home Assistant."""
        entity_reg = er.async_get(hass)
        missing_entities = []
        
        # Check pump entity
        if not entity_reg.async_get(self.pump_entity):
            if self.pump_entity not in hass.states.async_entity_ids():
                missing_entities.append(f"pump: {self.pump_entity}")
        
        # Check zone entities
        for zone in self.zone_entities:
            if not entity_reg.async_get(zone):
                if zone not in hass.states.async_entity_ids():
                    missing_entities.append(f"zone: {zone}")
        
        # Check light entity
        if self.light_entity:
            if not entity_reg.async_get(self.light_entity):
                if self.light_entity not in hass.states.async_entity_ids():
                    missing_entities.append(f"light: {self.light_entity}")
        
        # Check sensor entities
        for sensor_type, entity_id in self.sensors.items():
            if not entity_reg.async_get(entity_id):
                if entity_id not in hass.states.async_entity_ids():
                    missing_entities.append(f"sensor ({sensor_type}): {entity_id}")
        
        return missing_entities
    
    def add_event(self, event: IrrigationEvent) -> None:
        """Add an irrigation event to the room."""
        # Check if event type already exists
        existing_types = [e.event_type for e in self.events]
        if event.event_type in existing_types:
            raise ValueError(f"Event type {event.event_type} already exists for this room")
        
        event.validate()
        self.events.append(event)
    
    def remove_event(self, event_type: str) -> None:
        """Remove an irrigation event by type."""
        self.events = [e for e in self.events if e.event_type != event_type]
    
    def get_event(self, event_type: str) -> Optional[IrrigationEvent]:
        """Get an irrigation event by type."""
        for event in self.events:
            if event.event_type == event_type:
                return event
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert room to dictionary for storage."""
        return {
            "room_id": self.room_id,
            "name": self.name,
            "pump_entity": self.pump_entity,
            "zone_entities": self.zone_entities,
            "light_entity": self.light_entity,
            "sensors": self.sensors,
            "events": [event.to_dict() for event in self.events]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Room:
        """Create room from dictionary."""
        events = [IrrigationEvent.from_dict(event_data) for event_data in data.get("events", [])]
        
        return cls(
            room_id=data["room_id"],
            name=data["name"],
            pump_entity=data["pump_entity"],
            zone_entities=data.get("zone_entities", []),
            light_entity=data.get("light_entity"),
            sensors=data.get("sensors", {}),
            events=events
        )


# Validation schemas for external use
SHOT_SCHEMA = vol.Schema({
    vol.Required("duration"): vol.All(int, vol.Range(min=1, max=3600)),
    vol.Optional("interval_after", default=0): vol.All(int, vol.Range(min=0, max=86400))
})

EVENT_SCHEMA = vol.Schema({
    vol.Required("event_type"): vol.In([EVENT_TYPE_P1, EVENT_TYPE_P2]),
    vol.Required("shots"): [SHOT_SCHEMA],
    vol.Optional("schedule", default=""): str,
    vol.Optional("enabled", default=True): bool
})

ROOM_SCHEMA = vol.Schema({
    vol.Required("room_id"): str,
    vol.Required("name"): str,
    vol.Required("pump_entity"): str,
    vol.Optional("zone_entities", default=[]): [str],
    vol.Optional("light_entity"): str,
    vol.Optional("sensors", default={}): {
        vol.Optional("soil_rh"): str,
        vol.Optional("temperature"): str,
        vol.Optional("ec"): str,
        vol.Optional("ph"): str,
        vol.Optional("humidity"): str
    },
    vol.Optional("events", default=[]): [EVENT_SCHEMA]
})