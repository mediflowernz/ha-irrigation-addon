"""Sensor entities for the Irrigation Addon integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import IrrigationCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Create sensors for each room
    for room_id, room in coordinator.rooms.items():
        # Room status sensor
        entities.append(IrrigationRoomStatusSensor(coordinator, entry, room_id))
        
        # Room irrigation progress sensor
        entities.append(IrrigationProgressSensor(coordinator, entry, room_id))
        
        # Daily irrigation total sensor
        entities.append(DailyIrrigationTotalSensor(coordinator, entry, room_id))
        
        # Next event sensor
        entities.append(NextEventSensor(coordinator, entry, room_id))
        
        # Last event sensor
        entities.append(LastEventSensor(coordinator, entry, room_id))
        
        # Environmental sensors (if configured)
        if room.sensors.get("soil_rh"):
            entities.append(SoilMoistureSensor(coordinator, entry, room_id))
        
        if room.sensors.get("temperature"):
            entities.append(TemperatureSensor(coordinator, entry, room_id))
        
        if room.sensors.get("ec"):
            entities.append(EConductivitySensor(coordinator, entry, room_id))
    
    # System-wide diagnostic sensors
    entities.extend([
        SystemHealthSensor(coordinator, entry),
        ActiveIrrigationsSensor(coordinator, entry),
        FailSafeStatusSensor(coordinator, entry),
        ErrorRateSensor(coordinator, entry),
        PerformanceMetricsSensor(coordinator, entry),
        IrrigationSuccessRateSensor(coordinator, entry),
        SystemUptimeSensor(coordinator, entry),
    ])
    
    async_add_entities(entities)


class IrrigationSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for irrigation sensors."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: Optional[str] = None,
    ) -> None:
        """Initialize the sensor."""
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


class IrrigationRoomStatusSensor(IrrigationSensorBase):
    """Sensor for room irrigation status."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_status"
        self._attr_name = "Status"
        self._attr_icon = "mdi:sprinkler-variant"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        status = self.coordinator.get_room_status(self.room_id)
        
        if status.get("active_irrigation"):
            return "irrigating"
        elif status.get("manual_run"):
            return "manual_run"
        else:
            return "idle"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.get_room_status(self.room_id)
        
        attributes = {
            "daily_total_seconds": status.get("daily_total", 0),
            "daily_total_minutes": round(status.get("daily_total", 0) / 60, 1),
        }
        
        # Add active irrigation details
        if status.get("active_irrigation_details"):
            details = status["active_irrigation_details"]
            attributes.update({
                "event_type": details.get("event_type"),
                "current_shot": details.get("current_shot", 0) + 1,  # 1-based for display
                "total_shots": details.get("total_shots", 0),
                "progress_percent": round(details.get("progress", 0) * 100, 1),
            })
        
        # Add manual run details
        if status.get("manual_run_details"):
            details = status["manual_run_details"]
            attributes.update({
                "manual_duration": details.get("duration", 0),
                "manual_remaining": details.get("remaining", 0),
            })
        
        return attributes


class IrrigationProgressSensor(IrrigationSensorBase):
    """Sensor for irrigation progress percentage."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_progress"
        self._attr_name = "Progress"
        self._attr_icon = "mdi:progress-clock"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the progress percentage."""
        status = self.coordinator.get_room_status(self.room_id)
        
        if status.get("active_irrigation_details"):
            return round(status["active_irrigation_details"].get("progress", 0) * 100, 1)
        
        return None


class DailyIrrigationTotalSensor(IrrigationSensorBase):
    """Sensor for daily irrigation total."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_daily_total"
        self._attr_name = "Daily Total"
        self._attr_icon = "mdi:water-pump"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self) -> int:
        """Return the daily irrigation total in seconds."""
        status = self.coordinator.get_room_status(self.room_id)
        return status.get("daily_total", 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        daily_total = self.native_value
        max_daily = self.coordinator.settings.get("max_daily_irrigation", 3600)
        
        return {
            "daily_total_minutes": round(daily_total / 60, 1),
            "daily_limit_seconds": max_daily,
            "daily_limit_minutes": round(max_daily / 60, 1),
            "remaining_seconds": max(0, max_daily - daily_total),
            "remaining_minutes": round(max(0, max_daily - daily_total) / 60, 1),
            "usage_percentage": round((daily_total / max_daily) * 100, 1) if max_daily > 0 else 0,
        }


class NextEventSensor(IrrigationSensorBase):
    """Sensor for next scheduled irrigation event."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_next_event"
        self._attr_name = "Next Event"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the next event timestamp."""
        status = self.coordinator.get_room_status(self.room_id)
        next_events = status.get("next_events", {})
        
        # Return the earliest next event
        if next_events:
            earliest = min(next_events.values(), key=lambda x: x if x else datetime.max)
            return earliest if earliest != datetime.max else None
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.get_room_status(self.room_id)
        next_events = status.get("next_events", {})
        
        attributes = {}
        for event_type, next_time in next_events.items():
            if next_time:
                attributes[f"next_{event_type.lower()}"] = next_time.isoformat()
        
        return attributes


class LastEventSensor(IrrigationSensorBase):
    """Sensor for last irrigation event."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_last_event"
        self._attr_name = "Last Event"
        self._attr_icon = "mdi:clock-check-outline"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the last event timestamp."""
        status = self.coordinator.get_room_status(self.room_id)
        last_events = status.get("last_events", {})
        
        # Return the most recent last event
        if last_events:
            latest = max(last_events.values(), key=lambda x: x if x else datetime.min)
            return latest if latest != datetime.min else None
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.get_room_status(self.room_id)
        last_events = status.get("last_events", {})
        
        attributes = {}
        for event_type, last_time in last_events.items():
            if last_time:
                attributes[f"last_{event_type.lower()}"] = last_time.isoformat()
        
        return attributes


class SoilMoistureSensor(IrrigationSensorBase):
    """Sensor for soil moisture (RH)."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_soil_moisture"
        self._attr_name = "Soil Moisture"
        self._attr_icon = "mdi:water-percent"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.HUMIDITY

    @property
    def native_value(self) -> float | None:
        """Return the soil moisture value."""
        if not self.coordinator.data:
            return None
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        soil_rh_data = sensor_data.get("soil_rh", {})
        
        if soil_rh_data.get("unavailable"):
            return None
        
        return soil_rh_data.get("value")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data:
            return False
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        soil_rh_data = sensor_data.get("soil_rh", {})
        
        return not soil_rh_data.get("unavailable", True)


class TemperatureSensor(IrrigationSensorBase):
    """Sensor for temperature."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_temperature"
        self._attr_name = "Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        if not self.coordinator.data:
            return None
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        temp_data = sensor_data.get("temperature", {})
        
        if temp_data.get("unavailable"):
            return None
        
        return temp_data.get("value")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data:
            return False
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        temp_data = sensor_data.get("temperature", {})
        
        return not temp_data.get("unavailable", True)


class EConductivitySensor(IrrigationSensorBase):
    """Sensor for electrical conductivity."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        room_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, room_id)
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}_ec"
        self._attr_name = "EC"
        self._attr_icon = "mdi:flash"
        self._attr_native_unit_of_measurement = "µS/cm"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the EC value."""
        if not self.coordinator.data:
            return None
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        ec_data = sensor_data.get("ec", {})
        
        if ec_data.get("unavailable"):
            return None
        
        return ec_data.get("value")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data:
            return False
        
        sensor_data = self.coordinator.data.get("sensor_data", {}).get(self.room_id, {})
        ec_data = sensor_data.get("ec", {})
        
        return not ec_data.get("unavailable", True)


class SystemHealthSensor(IrrigationSensorBase):
    """Sensor for system health status."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_system_health"
        self._attr_name = "System Health"
        self._attr_icon = "mdi:heart-pulse"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the system health status."""
        health = self.coordinator.get_system_health()
        return health.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        health = self.coordinator.get_system_health()
        
        return {
            "rooms_count": health.get("rooms_count", 0),
            "active_irrigations": health.get("active_irrigations", 0),
            "active_manual_runs": health.get("active_manual_runs", 0),
            "scheduled_events": health.get("scheduled_events", 0),
            "fail_safe_enabled": health.get("fail_safe_enabled", False),
            "issues": health.get("issues", []),
        }


class ActiveIrrigationsSensor(IrrigationSensorBase):
    """Sensor for number of active irrigations."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_active_irrigations"
        self._attr_name = "Active Irrigations"
        self._attr_icon = "mdi:sprinkler-variant"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int:
        """Return the number of active irrigations."""
        health = self.coordinator.get_system_health()
        return health.get("active_irrigations", 0) + health.get("active_manual_runs", 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        health = self.coordinator.get_system_health()
        
        return {
            "scheduled_irrigations": health.get("active_irrigations", 0),
            "manual_runs": health.get("active_manual_runs", 0),
        }


class FailSafeStatusSensor(IrrigationSensorBase):
    """Sensor for fail-safe system status."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fail_safe_status"
        self._attr_name = "Fail Safe Status"
        self._attr_icon = "mdi:shield-check"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the fail-safe status."""
        fail_safe = self.coordinator.get_fail_safe_status()
        return "enabled" if fail_safe.get("enabled", False) else "disabled"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        fail_safe = self.coordinator.get_fail_safe_status()
        
        return {
            "emergency_stop_enabled": fail_safe.get("emergency_stop_enabled", False),
            "max_daily_irrigation": fail_safe.get("max_daily_irrigation", 0),
            "active_irrigations": fail_safe.get("active_irrigations", 0),
            "active_manual_runs": fail_safe.get("active_manual_runs", 0),
        }


class ErrorRateSensor(IrrigationSensorBase):
    """Sensor for system error rate."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_error_rate"
        self._attr_name = "Error Rate"
        self._attr_icon = "mdi:alert-circle"
        self._attr_native_unit_of_measurement = "errors/hour"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the error rate per hour."""
        error_stats = self.coordinator.get_error_statistics()
        return error_stats.get("error_rate", 0.0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        error_stats = self.coordinator.get_error_statistics()
        
        return {
            "total_errors": error_stats.get("total_errors", 0),
            "most_common_errors": error_stats.get("most_common_errors", []),
            "recent_error_count": len(error_stats.get("recent_errors", [])),
        }


class PerformanceMetricsSensor(IrrigationSensorBase):
    """Sensor for system performance metrics."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_performance_metrics"
        self._attr_name = "Performance"
        self._attr_icon = "mdi:speedometer"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the overall performance status."""
        metrics = self.coordinator.performance_tracker.get_all_metrics()
        
        # Calculate average response time
        sensor_update_stats = metrics.get("sensor_data_update_duration", {})
        avg_update_time = sensor_update_stats.get("avg", 0)
        
        if avg_update_time < 1.0:
            return "excellent"
        elif avg_update_time < 3.0:
            return "good"
        elif avg_update_time < 5.0:
            return "fair"
        else:
            return "poor"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return performance metrics as attributes."""
        metrics = self.coordinator.performance_tracker.get_all_metrics()
        
        attributes = {}
        for metric_name, stats in metrics.items():
            if stats:
                attributes[f"{metric_name}_avg"] = round(stats.get("avg", 0), 3)
                attributes[f"{metric_name}_max"] = round(stats.get("max", 0), 3)
                attributes[f"{metric_name}_count"] = stats.get("count", 0)
        
        return attributes


class IrrigationSuccessRateSensor(IrrigationSensorBase):
    """Sensor for irrigation success rate."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_success_rate"
        self._attr_name = "Success Rate"
        self._attr_icon = "mdi:check-circle"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the irrigation success rate percentage."""
        try:
            # Get performance metrics from storage
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't await here
                # Fall back to error-based calculation
                error_stats = self.coordinator.get_error_statistics()
                error_rate = error_stats.get("error_rate", 0.0)
                
                if error_rate == 0:
                    return 100.0
                elif error_rate < 1:
                    return 95.0
                elif error_rate < 5:
                    return 85.0
                else:
                    return max(50.0, 100.0 - (error_rate * 5))
            else:
                # We can use async methods
                metrics = loop.run_until_complete(
                    self.coordinator.storage.async_get_performance_metrics()
                )
                irrigation_metrics = metrics.get("irrigation_cycles", {})
                return irrigation_metrics.get("success_rate", 0.0)
        except Exception:
            return 0.0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                metrics = loop.run_until_complete(
                    self.coordinator.storage.async_get_performance_metrics()
                )
                irrigation_metrics = metrics.get("irrigation_cycles", {})
                
                return {
                    "total_attempts": irrigation_metrics.get("total_attempts", 0),
                    "successful_cycles": irrigation_metrics.get("successful_cycles", 0),
                    "failed_cycles": irrigation_metrics.get("failed_cycles", 0),
                    "average_duration": round(irrigation_metrics.get("average_duration", 0), 1),
                }
        except Exception:
            pass
        
        # Fallback to error-based attributes
        error_stats = self.coordinator.get_error_statistics()
        return {
            "total_operations": "N/A",
            "successful_operations": "N/A", 
            "failed_operations": error_stats.get("total_errors", 0),
            "error_rate_per_hour": error_stats.get("error_rate", 0.0),
        }


class SystemUptimeSensor(IrrigationSensorBase):
    """Sensor for system uptime."""

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_uptime"
        self._attr_name = "Uptime"
        self._attr_icon = "mdi:clock-time-eight"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._start_time = dt_util.now()

    @property
    def native_value(self) -> int:
        """Return the uptime in seconds."""
        uptime = dt_util.now() - self._start_time
        return int(uptime.total_seconds())

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        uptime_seconds = self.native_value
        uptime_minutes = uptime_seconds // 60
        uptime_hours = uptime_minutes // 60
        uptime_days = uptime_hours // 24
        
        return {
            "uptime_minutes": uptime_minutes,
            "uptime_hours": uptime_hours,
            "uptime_days": uptime_days,
            "start_time": self._start_time.isoformat(),
            "uptime_formatted": f"{uptime_days}d {uptime_hours % 24}h {uptime_minutes % 60}m",
        }