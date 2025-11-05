"""Logging utilities for the Irrigation Addon integration."""
from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .exceptions import IrrigationError


class IrrigationLogger:
    """Enhanced logger for irrigation system with structured logging."""
    
    def __init__(self, name: str, hass: HomeAssistant = None):
        """Initialize irrigation logger."""
        self.logger = logging.getLogger(name)
        self.hass = hass
        self._log_buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = 1000
        
    def _create_log_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Create structured log entry."""
        entry = {
            "timestamp": dt_util.now().isoformat(),
            "level": level,
            "message": message,
            "component": "irrigation_addon"
        }
        
        # Add additional context
        if kwargs:
            entry.update(kwargs)
        
        # Add to buffer for diagnostics
        self._log_buffer.append(entry)
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer.pop(0)
        
        # Record system errors in storage if available
        if self.hass and level in ["ERROR", "CRITICAL"] and kwargs.get("error"):
            try:
                from .const import DOMAIN
                coordinators = self.hass.data.get(DOMAIN, {})
                for coordinator in coordinators.values():
                    if hasattr(coordinator, 'storage'):
                        # Schedule async error recording
                        self.hass.async_create_task(
                            coordinator.storage.async_record_system_error(
                                kwargs.get("error_type", "Unknown"),
                                message
                            )
                        )
                        break
            except Exception:
                pass  # Don't let error recording cause more errors
        
        return entry
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        entry = self._create_log_entry("DEBUG", message, **kwargs)
        self.logger.debug(message, extra={"structured_data": entry})
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        entry = self._create_log_entry("INFO", message, **kwargs)
        self.logger.info(message, extra={"structured_data": entry})
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        entry = self._create_log_entry("WARNING", message, **kwargs)
        self.logger.warning(message, extra={"structured_data": entry})
    
    def error(self, message: str, error: Exception = None, **kwargs) -> None:
        """Log error message with context and exception details."""
        entry = self._create_log_entry("ERROR", message, **kwargs)
        
        if error:
            entry["error_type"] = type(error).__name__
            entry["error_message"] = str(error)
            
            if isinstance(error, IrrigationError):
                entry["error_code"] = error.error_code
                entry["error_details"] = error.details
        
        self.logger.error(message, exc_info=error is not None, extra={"structured_data": entry})
    
    def critical(self, message: str, error: Exception = None, **kwargs) -> None:
        """Log critical message with context."""
        entry = self._create_log_entry("CRITICAL", message, **kwargs)
        
        if error:
            entry["error_type"] = type(error).__name__
            entry["error_message"] = str(error)
        
        self.logger.critical(message, exc_info=error is not None, extra={"structured_data": entry})
    
    def irrigation_event(self, event_type: str, room_id: str, status: str, 
                        duration: int = None, **kwargs) -> None:
        """Log irrigation-specific events."""
        entry = self._create_log_entry(
            "INFO", 
            f"Irrigation event: {event_type} for room {room_id} - {status}",
            event_type=event_type,
            room_id=room_id,
            status=status,
            duration=duration,
            category="irrigation_event",
            **kwargs
        )
        self.logger.info(entry["message"], extra={"structured_data": entry})
    
    def hardware_operation(self, device_type: str, entity_id: str, operation: str, 
                          success: bool, room_id: str = None, **kwargs) -> None:
        """Log hardware control operations."""
        status = "SUCCESS" if success else "FAILED"
        message = f"Hardware {operation}: {device_type} {entity_id} - {status}"
        if room_id:
            message = f"Room {room_id}: {message}"
        
        entry = self._create_log_entry(
            "INFO" if success else "ERROR",
            message,
            device_type=device_type,
            entity_id=entity_id,
            operation=operation,
            success=success,
            room_id=room_id,
            category="hardware_operation",
            **kwargs
        )
        
        if success:
            self.logger.info(entry["message"], extra={"structured_data": entry})
        else:
            self.logger.error(entry["message"], extra={"structured_data": entry})
    
    def fail_safe_trigger(self, room_id: str, reason: str, check_type: str, **kwargs) -> None:
        """Log fail-safe mechanism triggers."""
        entry = self._create_log_entry(
            "WARNING",
            f"Fail-safe triggered for room {room_id}: {reason}",
            room_id=room_id,
            reason=reason,
            check_type=check_type,
            category="fail_safe",
            **kwargs
        )
        self.logger.warning(entry["message"], extra={"structured_data": entry})
    
    def performance_metric(self, metric_name: str, value: Union[int, float], 
                          unit: str = None, **kwargs) -> None:
        """Log performance metrics."""
        entry = self._create_log_entry(
            "DEBUG",
            f"Performance metric: {metric_name} = {value}" + (f" {unit}" if unit else ""),
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            category="performance",
            **kwargs
        )
        self.logger.debug(entry["message"], extra={"structured_data": entry})
    
    def get_recent_logs(self, hours: int = 24, level: str = None, 
                       category: str = None) -> List[Dict[str, Any]]:
        """Get recent log entries with optional filtering."""
        cutoff_time = dt_util.now() - timedelta(hours=hours)
        
        filtered_logs = []
        for entry in self._log_buffer:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time < cutoff_time:
                    continue
                
                if level and entry.get("level") != level:
                    continue
                
                if category and entry.get("category") != category:
                    continue
                
                filtered_logs.append(entry)
            except (ValueError, KeyError):
                continue
        
        return filtered_logs
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the specified time period."""
        error_logs = self.get_recent_logs(hours=hours, level="ERROR")
        critical_logs = self.get_recent_logs(hours=hours, level="CRITICAL")
        
        error_counts = {}
        for log in error_logs + critical_logs:
            error_type = log.get("error_type", "Unknown")
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(error_logs),
            "total_critical": len(critical_logs),
            "error_types": error_counts,
            "recent_errors": (error_logs + critical_logs)[-10:]  # Last 10 errors
        }


class PerformanceTracker:
    """Track and log performance metrics for irrigation operations."""
    
    def __init__(self, logger: IrrigationLogger):
        """Initialize performance tracker."""
        self.logger = logger
        self._metrics: Dict[str, List[float]] = {}
        self._operation_times: Dict[str, datetime] = {}
    
    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation."""
        self._operation_times[operation_name] = dt_util.now()
    
    def end_operation(self, operation_name: str, **kwargs) -> float:
        """End timing an operation and log the duration."""
        if operation_name not in self._operation_times:
            return 0.0
        
        start_time = self._operation_times.pop(operation_name)
        duration = (dt_util.now() - start_time).total_seconds()
        
        # Store metric
        if operation_name not in self._metrics:
            self._metrics[operation_name] = []
        self._metrics[operation_name].append(duration)
        
        # Keep only last 100 measurements
        if len(self._metrics[operation_name]) > 100:
            self._metrics[operation_name].pop(0)
        
        # Log the metric
        self.logger.performance_metric(
            f"{operation_name}_duration",
            duration,
            "seconds",
            operation=operation_name,
            **kwargs
        )
        
        return duration
    
    def record_metric(self, metric_name: str, value: Union[int, float], 
                     unit: str = None, **kwargs) -> None:
        """Record a custom metric."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        
        self._metrics[metric_name].append(float(value))
        
        # Keep only last 100 measurements
        if len(self._metrics[metric_name]) > 100:
            self._metrics[metric_name].pop(0)
        
        self.logger.performance_metric(metric_name, value, unit, **kwargs)
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        if metric_name not in self._metrics or not self._metrics[metric_name]:
            return {}
        
        values = self._metrics[metric_name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1]
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all tracked metrics."""
        return {
            metric_name: self.get_metric_stats(metric_name)
            for metric_name in self._metrics
        }


class DiagnosticCollector:
    """Collect diagnostic information for troubleshooting."""
    
    def __init__(self, hass: HomeAssistant, logger: IrrigationLogger):
        """Initialize diagnostic collector."""
        self.hass = hass
        self.logger = logger
    
    async def collect_system_info(self) -> Dict[str, Any]:
        """Collect system diagnostic information."""
        try:
            # Get Home Assistant info
            ha_version = self.hass.config.version
            ha_config_dir = self.hass.config.config_dir
            
            # Get integration info
            integration_data = self.hass.data.get(DOMAIN, {})
            
            # Get entity states for irrigation entities
            irrigation_entities = []
            for state in self.hass.states.async_all():
                if any(keyword in state.entity_id.lower() for keyword in 
                      ["pump", "zone", "irrigation", "sprinkler"]):
                    irrigation_entities.append({
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "attributes": dict(state.attributes),
                        "last_updated": state.last_updated.isoformat()
                    })
            
            return {
                "timestamp": dt_util.now().isoformat(),
                "home_assistant": {
                    "version": ha_version,
                    "config_dir": ha_config_dir
                },
                "integration": {
                    "domain": DOMAIN,
                    "loaded_entries": len(integration_data),
                    "entities_found": len(irrigation_entities)
                },
                "irrigation_entities": irrigation_entities,
                "recent_logs": self.logger.get_recent_logs(hours=1),
                "error_summary": self.logger.get_error_summary(hours=24)
            }
        
        except Exception as e:
            self.logger.error("Failed to collect system info", error=e)
            return {"error": str(e)}
    
    async def collect_room_diagnostics(self, room_id: str, coordinator) -> Dict[str, Any]:
        """Collect diagnostic information for a specific room."""
        try:
            room = await coordinator.async_get_room(room_id)
            if not room:
                return {"error": f"Room {room_id} not found"}
            
            # Get entity states
            entity_states = {}
            
            # Check pump
            if room.pump_entity:
                pump_state = self.hass.states.get(room.pump_entity)
                entity_states["pump"] = {
                    "entity_id": room.pump_entity,
                    "state": pump_state.state if pump_state else "not_found",
                    "attributes": dict(pump_state.attributes) if pump_state else {},
                    "available": pump_state is not None and pump_state.state != "unavailable"
                }
            
            # Check zones
            entity_states["zones"] = []
            for zone_entity in room.zone_entities:
                zone_state = self.hass.states.get(zone_entity)
                entity_states["zones"].append({
                    "entity_id": zone_entity,
                    "state": zone_state.state if zone_state else "not_found",
                    "attributes": dict(zone_state.attributes) if zone_state else {},
                    "available": zone_state is not None and zone_state.state != "unavailable"
                })
            
            # Check light entity
            if room.light_entity:
                light_state = self.hass.states.get(room.light_entity)
                entity_states["light"] = {
                    "entity_id": room.light_entity,
                    "state": light_state.state if light_state else "not_found",
                    "attributes": dict(light_state.attributes) if light_state else {},
                    "available": light_state is not None and light_state.state != "unavailable"
                }
            
            # Check sensors
            entity_states["sensors"] = {}
            for sensor_type, sensor_entity in room.sensors.items():
                sensor_state = self.hass.states.get(sensor_entity)
                entity_states["sensors"][sensor_type] = {
                    "entity_id": sensor_entity,
                    "state": sensor_state.state if sensor_state else "not_found",
                    "attributes": dict(sensor_state.attributes) if sensor_state else {},
                    "available": sensor_state is not None and sensor_state.state != "unavailable"
                }
            
            # Get room status
            room_status = coordinator.get_room_status(room_id)
            
            # Get safety validation
            safety_validation = await coordinator.async_validate_room_safety(room_id)
            
            return {
                "timestamp": dt_util.now().isoformat(),
                "room_config": room.to_dict(),
                "entity_states": entity_states,
                "room_status": room_status,
                "safety_validation": safety_validation,
                "recent_logs": self.logger.get_recent_logs(
                    hours=24, 
                    category="irrigation_event"
                )
            }
        
        except Exception as e:
            self.logger.error(f"Failed to collect diagnostics for room {room_id}", error=e)
            return {"error": str(e)}
    
    def export_diagnostics(self, data: Dict[str, Any], filename: str = None) -> str:
        """Export diagnostic data to JSON file."""
        try:
            if not filename:
                timestamp = dt_util.now().strftime("%Y%m%d_%H%M%S")
                filename = f"irrigation_diagnostics_{timestamp}.json"
            
            # Create diagnostics directory if it doesn't exist
            diagnostics_dir = Path(self.hass.config.config_dir) / "irrigation_diagnostics"
            diagnostics_dir.mkdir(exist_ok=True)
            
            filepath = diagnostics_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Diagnostics exported to {filepath}")
            return str(filepath)
        
        except Exception as e:
            self.logger.error("Failed to export diagnostics", error=e)
            return ""


# Global logger instances
_loggers: Dict[str, IrrigationLogger] = {}

def get_irrigation_logger(name: str, hass: HomeAssistant = None) -> IrrigationLogger:
    """Get or create an irrigation logger instance."""
    if name not in _loggers:
        _loggers[name] = IrrigationLogger(name, hass)
    return _loggers[name]


# Decorator for automatic error handling and logging
def log_irrigation_operation(operation_name: str, logger: IrrigationLogger = None):
    """Decorator to automatically log irrigation operations."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_irrigation_logger(func.__module__)
            
            logger.debug(f"Starting {operation_name}", operation=operation_name)
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Completed {operation_name}", operation=operation_name)
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name}", error=e, operation=operation_name)
                raise
        
        def sync_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_irrigation_logger(func.__module__)
            
            logger.debug(f"Starting {operation_name}", operation=operation_name)
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation_name}", operation=operation_name)
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name}", error=e, operation=operation_name)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator