"""Test data models and validation."""
import pytest
from datetime import datetime
from custom_components.irrigation_addon.models import Shot, IrrigationEvent, Room
from custom_components.irrigation_addon.const import EVENT_TYPE_P1, EVENT_TYPE_P2


class TestShot:
    """Test Shot data model."""

    def test_shot_creation_valid(self):
        """Test creating a valid shot."""
        shot = Shot(duration=30, interval_after=60)
        assert shot.duration == 30
        assert shot.interval_after == 60

    def test_shot_creation_minimal(self):
        """Test creating a shot with minimal parameters."""
        shot = Shot(duration=45)
        assert shot.duration == 45
        assert shot.interval_after == 0

    def test_shot_validation_invalid_duration(self):
        """Test shot validation with invalid duration."""
        with pytest.raises(ValueError, match="Shot duration must be greater than 0"):
            Shot(duration=0)
        
        with pytest.raises(ValueError, match="Shot duration cannot exceed 3600"):
            Shot(duration=3601)

    def test_shot_validation_invalid_interval(self):
        """Test shot validation with invalid interval."""
        with pytest.raises(ValueError, match="Shot interval cannot be negative"):
            Shot(duration=30, interval_after=-1)
        
        with pytest.raises(ValueError, match="Shot interval cannot exceed 86400"):
            Shot(duration=30, interval_after=86401)

    def test_shot_to_dict(self):
        """Test converting shot to dictionary."""
        shot = Shot(duration=30, interval_after=60)
        data = shot.to_dict()
        
        assert data == {
            "duration": 30,
            "interval_after": 60
        }

    def test_shot_from_dict(self):
        """Test creating shot from dictionary."""
        data = {"duration": 45, "interval_after": 120}
        shot = Shot.from_dict(data)
        
        assert shot.duration == 45
        assert shot.interval_after == 120

    def test_shot_from_dict_minimal(self):
        """Test creating shot from dictionary with minimal data."""
        data = {"duration": 30}
        shot = Shot.from_dict(data)
        
        assert shot.duration == 30
        assert shot.interval_after == 0


class TestIrrigationEvent:
    """Test IrrigationEvent data model."""

    def test_event_creation_valid(self):
        """Test creating a valid irrigation event."""
        shots = [Shot(duration=30), Shot(duration=45)]
        event = IrrigationEvent(
            event_type=EVENT_TYPE_P1,
            shots=shots,
            schedule="0 8 * * *",
            enabled=True
        )
        
        assert event.event_type == EVENT_TYPE_P1
        assert len(event.shots) == 2
        assert event.schedule == "0 8 * * *"
        assert event.enabled is True

    def test_event_validation_invalid_type(self):
        """Test event validation with invalid type."""
        with pytest.raises(ValueError, match="Event type must be P1 or P2"):
            IrrigationEvent(event_type="P3", shots=[Shot(duration=30)])

    def test_event_validation_no_shots(self):
        """Test event validation with no shots."""
        with pytest.raises(ValueError, match="Event must have at least one shot"):
            IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[])

    def test_event_validation_too_many_shots(self):
        """Test event validation with too many shots."""
        shots = [Shot(duration=30) for _ in range(21)]
        with pytest.raises(ValueError, match="Event cannot have more than 20 shots"):
            IrrigationEvent(event_type=EVENT_TYPE_P1, shots=shots)

    def test_event_validation_invalid_cron(self):
        """Test event validation with invalid cron expression."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            IrrigationEvent(
                event_type=EVENT_TYPE_P1,
                shots=[Shot(duration=30)],
                schedule="invalid cron"
            )

    def test_event_add_shot(self):
        """Test adding a shot to an event."""
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        new_shot = Shot(duration=45)
        
        event.add_shot(new_shot)
        assert len(event.shots) == 2
        assert event.shots[1].duration == 45

    def test_event_add_shot_limit_exceeded(self):
        """Test adding shot when limit is exceeded."""
        shots = [Shot(duration=30) for _ in range(20)]
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=shots)
        
        with pytest.raises(ValueError, match="Cannot add more than 20 shots"):
            event.add_shot(Shot(duration=30))

    def test_event_remove_shot(self):
        """Test removing a shot from an event."""
        shots = [Shot(duration=30), Shot(duration=45)]
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=shots)
        
        event.remove_shot(0)
        assert len(event.shots) == 1
        assert event.shots[0].duration == 45

    def test_event_remove_shot_invalid_index(self):
        """Test removing shot with invalid index."""
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        
        with pytest.raises(ValueError, match="Invalid shot index"):
            event.remove_shot(5)

    def test_event_remove_last_shot(self):
        """Test removing the last shot from an event."""
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        
        with pytest.raises(ValueError, match="Event must have at least one shot"):
            event.remove_shot(0)

    def test_event_get_total_duration(self):
        """Test calculating total event duration."""
        shots = [
            Shot(duration=30, interval_after=60),
            Shot(duration=45, interval_after=30),
            Shot(duration=20)  # No interval after last shot
        ]
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=shots)
        
        # Total: 30 + 45 + 20 + 60 + 30 = 185 seconds
        assert event.get_total_duration() == 185

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        shots = [Shot(duration=30)]
        event = IrrigationEvent(
            event_type=EVENT_TYPE_P1,
            shots=shots,
            schedule="0 8 * * *",
            enabled=True
        )
        
        data = event.to_dict()
        assert data["event_type"] == EVENT_TYPE_P1
        assert len(data["shots"]) == 1
        assert data["schedule"] == "0 8 * * *"
        assert data["enabled"] is True

    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        data = {
            "event_type": EVENT_TYPE_P2,
            "shots": [{"duration": 30, "interval_after": 0}],
            "schedule": "0 20 * * *",
            "enabled": False
        }
        
        event = IrrigationEvent.from_dict(data)
        assert event.event_type == EVENT_TYPE_P2
        assert len(event.shots) == 1
        assert event.shots[0].duration == 30
        assert event.schedule == "0 20 * * *"
        assert event.enabled is False


class TestRoom:
    """Test Room data model."""

    def test_room_creation_valid(self):
        """Test creating a valid room."""
        room = Room(
            room_id="room1",
            name="Test Room",
            pump_entity="switch.pump1",
            zone_entities=["switch.zone1", "switch.zone2"],
            light_entity="light.grow_light",
            sensors={"soil_rh": "sensor.soil_moisture", "temperature": "sensor.temp"}
        )
        
        assert room.room_id == "room1"
        assert room.name == "Test Room"
        assert room.pump_entity == "switch.pump1"
        assert len(room.zone_entities) == 2
        assert room.light_entity == "light.grow_light"
        assert len(room.sensors) == 2

    def test_room_validation_empty_id(self):
        """Test room validation with empty ID."""
        with pytest.raises(ValueError, match="Room ID cannot be empty"):
            Room(room_id="", name="Test", pump_entity="switch.pump1")

    def test_room_validation_empty_name(self):
        """Test room validation with empty name."""
        with pytest.raises(ValueError, match="Room name cannot be empty"):
            Room(room_id="room1", name="", pump_entity="switch.pump1")

    def test_room_validation_no_pump(self):
        """Test room validation with no pump entity."""
        with pytest.raises(ValueError, match="Room must have a pump entity"):
            Room(room_id="room1", name="Test", pump_entity="")

    def test_room_validation_invalid_entity_format(self):
        """Test room validation with invalid entity format."""
        with pytest.raises(ValueError, match="Invalid pump entity ID format"):
            Room(room_id="room1", name="Test", pump_entity="invalid_entity")

    def test_room_validation_invalid_sensor_type(self):
        """Test room validation with invalid sensor type."""
        with pytest.raises(ValueError, match="Invalid sensor type"):
            Room(
                room_id="room1",
                name="Test",
                pump_entity="switch.pump1",
                sensors={"invalid_sensor": "sensor.test"}
            )

    def test_room_add_event(self):
        """Test adding an event to a room."""
        room = Room(room_id="room1", name="Test", pump_entity="switch.pump1")
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        
        room.add_event(event)
        assert len(room.events) == 1
        assert room.events[0].event_type == EVENT_TYPE_P1

    def test_room_add_duplicate_event_type(self):
        """Test adding duplicate event type to a room."""
        room = Room(room_id="room1", name="Test", pump_entity="switch.pump1")
        event1 = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        event2 = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=45)])
        
        room.add_event(event1)
        with pytest.raises(ValueError, match="Event type P1 already exists"):
            room.add_event(event2)

    def test_room_remove_event(self):
        """Test removing an event from a room."""
        room = Room(room_id="room1", name="Test", pump_entity="switch.pump1")
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        
        room.add_event(event)
        room.remove_event(EVENT_TYPE_P1)
        assert len(room.events) == 0

    def test_room_get_event(self):
        """Test getting an event from a room."""
        room = Room(room_id="room1", name="Test", pump_entity="switch.pump1")
        event = IrrigationEvent(event_type=EVENT_TYPE_P1, shots=[Shot(duration=30)])
        
        room.add_event(event)
        retrieved_event = room.get_event(EVENT_TYPE_P1)
        assert retrieved_event is not None
        assert retrieved_event.event_type == EVENT_TYPE_P1

    def test_room_get_nonexistent_event(self):
        """Test getting a non-existent event from a room."""
        room = Room(room_id="room1", name="Test", pump_entity="switch.pump1")
        
        retrieved_event = room.get_event(EVENT_TYPE_P1)
        assert retrieved_event is None

    def test_room_to_dict(self):
        """Test converting room to dictionary."""
        room = Room(
            room_id="room1",
            name="Test Room",
            pump_entity="switch.pump1",
            zone_entities=["switch.zone1"],
            sensors={"soil_rh": "sensor.moisture"}
        )
        
        data = room.to_dict()
        assert data["room_id"] == "room1"
        assert data["name"] == "Test Room"
        assert data["pump_entity"] == "switch.pump1"
        assert len(data["zone_entities"]) == 1
        assert data["sensors"]["soil_rh"] == "sensor.moisture"

    def test_room_from_dict(self):
        """Test creating room from dictionary."""
        data = {
            "room_id": "room2",
            "name": "Test Room 2",
            "pump_entity": "switch.pump2",
            "zone_entities": ["switch.zone2a", "switch.zone2b"],
            "light_entity": "light.grow_light2",
            "sensors": {"temperature": "sensor.temp2"},
            "events": []
        }
        
        room = Room.from_dict(data)
        assert room.room_id == "room2"
        assert room.name == "Test Room 2"
        assert room.pump_entity == "switch.pump2"
        assert len(room.zone_entities) == 2
        assert room.light_entity == "light.grow_light2"
        assert room.sensors["temperature"] == "sensor.temp2"