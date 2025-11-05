"""Custom exceptions for the Irrigation Addon integration."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from homeassistant.exceptions import HomeAssistantError


class IrrigationError(HomeAssistantError):
    """Base exception for irrigation system errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None) -> None:
        """Initialize irrigation error."""
        super().__init__(message)
        self.error_code = error_code or "IRRIGATION_ERROR"
        self.details = details or {}
        self.user_message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": str(self),
            "user_message": self.user_message,
            "details": self.details
        }


class EntityUnavailableError(IrrigationError):
    """Raised when required entities are unavailable."""
    
    def __init__(self, entities: List[str], room_id: str = None) -> None:
        """Initialize entity unavailable error."""
        entity_list = ", ".join(entities)
        message = f"Required entities are unavailable: {entity_list}"
        if room_id:
            message = f"Room {room_id}: {message}"
        
        super().__init__(
            message=message,
            error_code="ENTITY_UNAVAILABLE",
            details={
                "unavailable_entities": entities,
                "room_id": room_id,
                "recovery_action": "Check entity availability in Home Assistant"
            }
        )
        self.entities = entities
        self.room_id = room_id
        self.user_message = f"Cannot start irrigation: {entity_list} not available"


class LightScheduleConflictError(IrrigationError):
    """Raised when irrigation conflicts with light schedule."""
    
    def __init__(self, room_id: str, light_entity: str, light_state: str = None) -> None:
        """Initialize light schedule conflict error."""
        message = f"Room {room_id}: Irrigation blocked by light schedule"
        if light_state:
            message += f" (lights are {light_state})"
        
        super().__init__(
            message=message,
            error_code="LIGHT_SCHEDULE_CONFLICT",
            details={
                "room_id": room_id,
                "light_entity": light_entity,
                "light_state": light_state,
                "recovery_action": "Wait for lights to turn on or disable light schedule integration"
            }
        )
        self.room_id = room_id
        self.light_entity = light_entity
        self.user_message = "Irrigation blocked: lights are off (check light schedule)"


class OverWateringError(IrrigationError):
    """Raised when daily irrigation limits would be exceeded."""
    
    def __init__(self, room_id: str, current_total: int, requested_duration: int, daily_limit: int) -> None:
        """Initialize over-watering error."""
        remaining = max(0, daily_limit - current_total)
        message = f"Room {room_id}: Daily irrigation limit would be exceeded"
        
        super().__init__(
            message=message,
            error_code="OVERWATERING_PREVENTION",
            details={
                "room_id": room_id,
                "current_daily_total": current_total,
                "requested_duration": requested_duration,
                "daily_limit": daily_limit,
                "remaining_allowance": remaining,
                "recovery_action": f"Reduce duration to {remaining}s or wait until tomorrow"
            }
        )
        self.room_id = room_id
        self.current_total = current_total
        self.requested_duration = requested_duration
        self.daily_limit = daily_limit
        self.user_message = f"Daily limit exceeded. Only {remaining}s remaining of {daily_limit}s allowed"


class IrrigationConflictError(IrrigationError):
    """Raised when irrigation conflicts with existing operations."""
    
    def __init__(self, room_id: str, conflict_type: str, details: str = None) -> None:
        """Initialize irrigation conflict error."""
        message = f"Room {room_id}: {conflict_type} already in progress"
        if details:
            message += f" ({details})"
        
        super().__init__(
            message=message,
            error_code="IRRIGATION_CONFLICT",
            details={
                "room_id": room_id,
                "conflict_type": conflict_type,
                "additional_details": details,
                "recovery_action": "Stop existing irrigation before starting new one"
            }
        )
        self.room_id = room_id
        self.conflict_type = conflict_type
        self.user_message = f"Cannot start: {conflict_type.lower()} already running"


class HardwareControlError(IrrigationError):
    """Raised when hardware control operations fail."""
    
    def __init__(self, device_type: str, entity_id: str, operation: str, room_id: str = None, 
                 underlying_error: Exception = None) -> None:
        """Initialize hardware control error."""
        message = f"Failed to {operation} {device_type} {entity_id}"
        if room_id:
            message = f"Room {room_id}: {message}"
        
        details = {
            "device_type": device_type,
            "entity_id": entity_id,
            "operation": operation,
            "room_id": room_id,
            "recovery_action": f"Check {device_type} entity status and Home Assistant connectivity"
        }
        
        if underlying_error:
            details["underlying_error"] = str(underlying_error)
            details["underlying_error_type"] = type(underlying_error).__name__
        
        super().__init__(
            message=message,
            error_code="HARDWARE_CONTROL_ERROR",
            details=details
        )
        self.device_type = device_type
        self.entity_id = entity_id
        self.operation = operation
        self.room_id = room_id
        self.underlying_error = underlying_error
        self.user_message = f"Hardware error: Cannot {operation} {device_type}"


class ConfigurationError(IrrigationError):
    """Raised when configuration is invalid or incomplete."""
    
    def __init__(self, config_type: str, issue: str, room_id: str = None, 
                 field_name: str = None, field_value: Any = None) -> None:
        """Initialize configuration error."""
        message = f"Configuration error in {config_type}: {issue}"
        if room_id:
            message = f"Room {room_id}: {message}"
        
        details = {
            "config_type": config_type,
            "issue": issue,
            "room_id": room_id,
            "recovery_action": "Review and correct configuration"
        }
        
        if field_name:
            details["field_name"] = field_name
            details["field_value"] = field_value
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details
        )
        self.config_type = config_type
        self.issue = issue
        self.room_id = room_id
        self.user_message = f"Configuration issue: {issue}"


class SchedulingError(IrrigationError):
    """Raised when scheduling operations fail."""
    
    def __init__(self, operation: str, room_id: str = None, event_type: str = None, 
                 schedule_expr: str = None, underlying_error: Exception = None) -> None:
        """Initialize scheduling error."""
        message = f"Scheduling error: {operation}"
        if room_id and event_type:
            message += f" for {event_type} event in room {room_id}"
        
        details = {
            "operation": operation,
            "room_id": room_id,
            "event_type": event_type,
            "recovery_action": "Check cron expression format and system time"
        }
        
        if schedule_expr:
            details["schedule_expression"] = schedule_expr
        
        if underlying_error:
            details["underlying_error"] = str(underlying_error)
            details["underlying_error_type"] = type(underlying_error).__name__
        
        super().__init__(
            message=message,
            error_code="SCHEDULING_ERROR",
            details=details
        )
        self.operation = operation
        self.room_id = room_id
        self.event_type = event_type
        self.underlying_error = underlying_error
        self.user_message = f"Scheduling failed: {operation}"


class StorageError(IrrigationError):
    """Raised when storage operations fail."""
    
    def __init__(self, operation: str, data_type: str = None, underlying_error: Exception = None) -> None:
        """Initialize storage error."""
        message = f"Storage error: {operation}"
        if data_type:
            message += f" for {data_type}"
        
        details = {
            "operation": operation,
            "data_type": data_type,
            "recovery_action": "Check file system permissions and available disk space"
        }
        
        if underlying_error:
            details["underlying_error"] = str(underlying_error)
            details["underlying_error_type"] = type(underlying_error).__name__
        
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            details=details
        )
        self.operation = operation
        self.data_type = data_type
        self.underlying_error = underlying_error
        self.user_message = f"Storage error: Cannot {operation}"


class ValidationError(IrrigationError):
    """Raised when data validation fails."""
    
    def __init__(self, field_name: str, field_value: Any, validation_rule: str, 
                 context: str = None) -> None:
        """Initialize validation error."""
        message = f"Validation failed for {field_name}: {validation_rule}"
        if context:
            message = f"{context}: {message}"
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={
                "field_name": field_name,
                "field_value": field_value,
                "validation_rule": validation_rule,
                "context": context,
                "recovery_action": f"Correct {field_name} to meet validation requirements"
            }
        )
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule
        self.user_message = f"Invalid {field_name}: {validation_rule}"


class ServiceError(IrrigationError):
    """Raised when service operations fail."""
    
    def __init__(self, service_name: str, operation: str, underlying_error: Exception = None) -> None:
        """Initialize service error."""
        message = f"Service error in {service_name}: {operation}"
        
        details = {
            "service_name": service_name,
            "operation": operation,
            "recovery_action": "Check service parameters and system state"
        }
        
        if underlying_error:
            details["underlying_error"] = str(underlying_error)
            details["underlying_error_type"] = type(underlying_error).__name__
        
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            details=details
        )
        self.service_name = service_name
        self.operation = operation
        self.underlying_error = underlying_error
        self.user_message = f"Service failed: {operation}"


class EmergencyStopError(IrrigationError):
    """Raised when emergency stop operations fail."""
    
    def __init__(self, scope: str, failed_operations: List[str] = None, 
                 underlying_error: Exception = None) -> None:
        """Initialize emergency stop error."""
        message = f"Emergency stop failed for {scope}"
        if failed_operations:
            message += f": {', '.join(failed_operations)}"
        
        details = {
            "scope": scope,
            "failed_operations": failed_operations or [],
            "recovery_action": "Manual intervention may be required to stop irrigation devices"
        }
        
        if underlying_error:
            details["underlying_error"] = str(underlying_error)
            details["underlying_error_type"] = type(underlying_error).__name__
        
        super().__init__(
            message=message,
            error_code="EMERGENCY_STOP_ERROR",
            details=details
        )
        self.scope = scope
        self.failed_operations = failed_operations or []
        self.underlying_error = underlying_error
        self.user_message = f"Emergency stop failed - manual intervention may be needed"


# Error recovery utilities
class ErrorRecovery:
    """Utilities for error recovery and retry logic."""
    
    @staticmethod
    def is_recoverable_error(error: Exception) -> bool:
        """Check if an error is potentially recoverable."""
        recoverable_types = [
            EntityUnavailableError,
            HardwareControlError,
            StorageError,
            ServiceError
        ]
        
        # Check if it's a recoverable irrigation error
        if isinstance(error, IrrigationError):
            return type(error) in recoverable_types
        
        # Check for common recoverable Home Assistant errors
        if isinstance(error, HomeAssistantError):
            error_msg = str(error).lower()
            recoverable_keywords = [
                "timeout",
                "connection",
                "network",
                "temporary",
                "unavailable"
            ]
            return any(keyword in error_msg for keyword in recoverable_keywords)
        
        return False
    
    @staticmethod
    def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
        """Calculate exponential backoff delay for retry attempts."""
        import math
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    @staticmethod
    def should_retry(error: Exception, attempt: int, max_attempts: int = 3) -> bool:
        """Determine if an operation should be retried."""
        if attempt >= max_attempts:
            return False
        
        return ErrorRecovery.is_recoverable_error(error)


# Error context manager for consistent error handling
class IrrigationErrorHandler:
    """Context manager for consistent error handling and logging."""
    
    def __init__(self, operation: str, logger, room_id: str = None, 
                 suppress_exceptions: bool = False):
        """Initialize error handler."""
        self.operation = operation
        self.logger = logger
        self.room_id = room_id
        self.suppress_exceptions = suppress_exceptions
        self.error = None
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and handle any exceptions."""
        if exc_type is None:
            return False
        
        self.error = exc_val
        
        # Log the error appropriately
        if isinstance(exc_val, IrrigationError):
            self.logger.error(
                "Irrigation error in %s: %s (Code: %s)", 
                self.operation, exc_val, exc_val.error_code
            )
            if exc_val.details:
                self.logger.debug("Error details: %s", exc_val.details)
        else:
            self.logger.error(
                "Unexpected error in %s: %s (%s)", 
                self.operation, exc_val, type(exc_val).__name__
            )
        
        # Return True to suppress the exception if requested
        return self.suppress_exceptions
    
    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        if isinstance(self.error, IrrigationError):
            return self.error.user_message
        elif self.error:
            return f"An error occurred during {self.operation}"
        return ""