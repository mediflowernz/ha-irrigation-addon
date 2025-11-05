# Services Documentation

The Irrigation Addon exposes several services that can be used in Home Assistant automations, scripts, and manual service calls.

## Table of Contents

- [Service Overview](#service-overview)
- [Manual Control Services](#manual-control-services)
- [Event Management Services](#event-management-services)
- [Shot Management Services](#shot-management-services)
- [System Control Services](#system-control-services)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)

## Service Overview

All services are exposed under the `irrigation_addon` domain and can be called from:
- Home Assistant automations
- Scripts
- Developer Tools → Services
- REST API calls
- Node-RED (if installed)

### Service Naming Convention

Services follow the pattern: `irrigation_addon.<action_name>`

### Common Parameters

Most services accept these common parameters:
- `room_id`: String identifier for the target room
- `event_type`: Either "P1" or "P2" for event-specific operations

## Manual Control Services

### `irrigation_addon.start_manual_run`

Starts a manual irrigation cycle for a specific room.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "veg_room_1"

duration: integer (required)
  description: Duration in seconds (1-3600)
  example: 300
```

**Example:**
```yaml
service: irrigation_addon.start_manual_run
data:
  room_id: "veg_room_1"
  duration: 180  # 3 minutes
```

**Behavior:**
- Activates pump and all configured zones for the room
- Respects pump-to-zone delay setting
- Checks fail-safe conditions before starting
- Automatically stops after specified duration
- Can be stopped early with `stop_irrigation` service

**Fail-Safe Checks:**
- Light schedule (if configured)
- Entity availability
- Daily irrigation limits
- Existing active irrigation

---

### `irrigation_addon.stop_irrigation`

Stops any active irrigation for a specific room.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "flower_room_2"
```

**Example:**
```yaml
service: irrigation_addon.stop_irrigation
data:
  room_id: "flower_room_2"
```

**Behavior:**
- Immediately turns off all zones for the room
- Turns off pump after 3-second delay
- Cancels any remaining shots in active event
- Logs stop reason and duration
- Safe to call even if no irrigation is active

---

### `irrigation_addon.emergency_stop_all`

Emergency stop for all rooms and irrigation activities.

**Parameters:**
```yaml
# No parameters required
```

**Example:**
```yaml
service: irrigation_addon.emergency_stop_all
```

**Behavior:**
- Stops all active irrigation in all rooms
- Disables all scheduled events temporarily
- Logs emergency stop event
- Requires manual re-enabling of events
- Use for system-wide emergencies only

## Event Management Services

### `irrigation_addon.enable_event`

Enables or disables a specific irrigation event.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "veg_room_1"

event_type: string (required)
  description: Event type to modify
  options: ["P1", "P2"]

enabled: boolean (required)
  description: Enable (true) or disable (false) the event
  example: true
```

**Example:**
```yaml
service: irrigation_addon.enable_event
data:
  room_id: "veg_room_1"
  event_type: "P1"
  enabled: false  # Disable P1 events
```

**Behavior:**
- Immediately affects event scheduling
- Disabled events won't trigger automatically
- Manual runs still work when events are disabled
- Event configuration is preserved when disabled

---

### `irrigation_addon.update_event_schedule`

Updates the schedule (cron expression) for an event.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "flower_room_1"

event_type: string (required)
  description: Event type to modify
  options: ["P1", "P2"]

schedule: string (required)
  description: Cron expression for scheduling
  example: "0 8,20 * * *"
```

**Example:**
```yaml
service: irrigation_addon.update_event_schedule
data:
  room_id: "flower_room_1"
  event_type: "P2"
  schedule: "0 12 * * 1,3,5"  # Noon on Mon, Wed, Fri
```

**Behavior:**
- Validates cron expression before applying
- Takes effect immediately for future events
- Does not affect currently running irrigation
- Logs schedule change for audit trail

## Shot Management Services

### `irrigation_addon.add_shot_to_event`

Adds a new shot to an existing event.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "veg_room_1"

event_type: string (required)
  description: Event type to modify
  options: ["P1", "P2"]

duration: integer (required)
  description: Shot duration in seconds (1-3600)
  example: 45

interval_after: integer (optional)
  description: Interval after this shot in seconds (0-7200)
  default: 0
  example: 300

position: integer (optional)
  description: Position to insert shot (0-based index)
  default: -1 (append to end)
  example: 1
```

**Example:**
```yaml
service: irrigation_addon.add_shot_to_event
data:
  room_id: "veg_room_1"
  event_type: "P1"
  duration: 60
  interval_after: 300  # 5 minutes
  position: 1  # Insert as second shot
```

**Behavior:**
- Adds shot at specified position or end of list
- Validates duration and interval values
- Takes effect for next scheduled event
- Maximum 10 shots per event

---

### `irrigation_addon.remove_shot_from_event`

Removes a shot from an event by position.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "flower_room_2"

event_type: string (required)
  description: Event type to modify
  options: ["P1", "P2"]

position: integer (required)
  description: Position of shot to remove (0-based index)
  example: 2
```

**Example:**
```yaml
service: irrigation_addon.remove_shot_from_event
data:
  room_id: "flower_room_2"
  event_type: "P2"
  position: 0  # Remove first shot
```

**Behavior:**
- Removes shot at specified position
- Remaining shots shift positions
- Minimum 1 shot must remain in event
- Takes effect for next scheduled event

---

### `irrigation_addon.update_shot`

Updates an existing shot's parameters.

**Parameters:**
```yaml
room_id: string (required)
  description: Unique identifier of the room
  example: "veg_room_1"

event_type: string (required)
  description: Event type to modify
  options: ["P1", "P2"]

position: integer (required)
  description: Position of shot to update (0-based index)
  example: 1

duration: integer (optional)
  description: New duration in seconds
  example: 90

interval_after: integer (optional)
  description: New interval in seconds
  example: 600
```

**Example:**
```yaml
service: irrigation_addon.update_shot
data:
  room_id: "veg_room_1"
  event_type: "P1"
  position: 1
  duration: 90  # Update to 90 seconds
  interval_after: 600  # Update to 10 minutes
```

**Behavior:**
- Updates only specified parameters
- Validates new values before applying
- Takes effect for next scheduled event
- Logs changes for audit trail

## System Control Services

### `irrigation_addon.reload_configuration`

Reloads the integration configuration from storage.

**Parameters:**
```yaml
# No parameters required
```

**Example:**
```yaml
service: irrigation_addon.reload_configuration
```

**Behavior:**
- Reloads all room configurations
- Reloads system settings
- Restarts coordinator with new configuration
- Use after manual configuration file changes

---

### `irrigation_addon.reset_daily_limits`

Resets daily irrigation counters for all rooms.

**Parameters:**
```yaml
room_id: string (optional)
  description: Specific room to reset, or all rooms if omitted
  example: "veg_room_1"
```

**Example:**
```yaml
service: irrigation_addon.reset_daily_limits
data:
  room_id: "veg_room_1"  # Reset only this room
```

**Behavior:**
- Resets irrigation event counters
- Allows additional irrigation if limits were reached
- Logs reset action with timestamp
- Automatic reset occurs at midnight

---

### `irrigation_addon.export_configuration`

Exports current configuration to a downloadable file.

**Parameters:**
```yaml
include_history: boolean (optional)
  description: Include irrigation history in export
  default: false
  example: true
```

**Example:**
```yaml
service: irrigation_addon.export_configuration
data:
  include_history: true
```

**Behavior:**
- Creates JSON export of all configuration
- Optionally includes irrigation history
- File available in `/config/www/irrigation_export.json`
- Use for backup or migration purposes

## Usage Examples

### Automation Examples

#### Skip Irrigation on Rainy Days

```yaml
automation:
  - alias: "Skip irrigation when raining"
    trigger:
      - platform: state
        entity_id: weather.home
        attribute: condition
        to: "rainy"
    action:
      - service: irrigation_addon.enable_event
        data:
          room_id: "outdoor_garden"
          event_type: "P1"
          enabled: false
      - service: irrigation_addon.enable_event
        data:
          room_id: "outdoor_garden"
          event_type: "P2"
          enabled: false
```

#### Extra Watering on Hot Days

```yaml
automation:
  - alias: "Extra watering when hot"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        above: 90
        for:
          minutes: 30
    action:
      - service: irrigation_addon.start_manual_run
        data:
          room_id: "greenhouse"
          duration: 300  # 5 minutes extra
```

#### Adjust Schedule for Growth Stage

```yaml
automation:
  - alias: "Switch to flowering schedule"
    trigger:
      - platform: state
        entity_id: input_select.growth_stage
        to: "flowering"
    action:
      - service: irrigation_addon.update_event_schedule
        data:
          room_id: "main_room"
          event_type: "P1"
          schedule: "0 9,21 * * *"  # Twice daily for flowering
```

### Script Examples

#### Weekly Maintenance Script

```yaml
script:
  weekly_irrigation_maintenance:
    alias: "Weekly Irrigation Maintenance"
    sequence:
      - service: irrigation_addon.reset_daily_limits
      - service: irrigation_addon.export_configuration
        data:
          include_history: true
      - service: notify.admin
        data:
          message: "Weekly irrigation maintenance completed"
```

#### Emergency Shutdown Script

```yaml
script:
  irrigation_emergency_shutdown:
    alias: "Emergency Irrigation Shutdown"
    sequence:
      - service: irrigation_addon.emergency_stop_all
      - service: notify.all_devices
        data:
          message: "EMERGENCY: All irrigation stopped"
          title: "Irrigation Alert"
      - service: persistent_notification.create
        data:
          title: "Irrigation Emergency Stop"
          message: "All irrigation has been stopped. Check system before restarting."
```

## Error Handling

### Common Error Responses

**Room Not Found:**
```yaml
error: "Room 'invalid_room' not found"
code: "room_not_found"
```

**Invalid Event Type:**
```yaml
error: "Event type must be 'P1' or 'P2'"
code: "invalid_event_type"
```

**Duration Out of Range:**
```yaml
error: "Duration must be between 1 and 3600 seconds"
code: "invalid_duration"
```

**Entity Unavailable:**
```yaml
error: "Pump entity 'switch.pump_1' is unavailable"
code: "entity_unavailable"
```

**Fail-Safe Prevention:**
```yaml
error: "Irrigation prevented by fail-safe: lights are off"
code: "fail_safe_prevention"
```

### Error Handling in Automations

```yaml
automation:
  - alias: "Handle irrigation service errors"
    trigger:
      - platform: event
        event_type: call_service
        event_data:
          domain: irrigation_addon
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.service_data.get('error') is not none }}"
    action:
      - service: notify.admin
        data:
          message: "Irrigation service error: {{ trigger.event.data.service_data.error }}"
```

### Retry Logic Example

```yaml
script:
  start_irrigation_with_retry:
    alias: "Start Irrigation with Retry"
    sequence:
      - repeat:
          count: 3
          sequence:
            - service: irrigation_addon.start_manual_run
              data:
                room_id: "main_room"
                duration: 180
              continue_on_error: true
            - condition: template
              value_template: "{{ not states('sensor.irrigation_status_main_room') == 'error' }}"
            - stop: "Irrigation started successfully"
      - service: notify.admin
        data:
          message: "Failed to start irrigation after 3 attempts"
```

---

## Service Testing

### Using Developer Tools

1. Go to **Developer Tools** → **Services**
2. Select service from dropdown: `irrigation_addon.start_manual_run`
3. Enter service data in YAML format:
   ```yaml
   room_id: "test_room"
   duration: 30
   ```
4. Click **Call Service**

### Using REST API

```bash
# Start manual run via REST API
curl -X POST \
  http://homeassistant.local:8123/api/services/irrigation_addon/start_manual_run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "veg_room_1",
    "duration": 180
  }'
```

### Service Response Monitoring

Monitor service calls in Home Assistant logs:

```yaml
logger:
  logs:
    custom_components.irrigation_addon.services: debug
```

This will log all service calls, parameters, and results for debugging purposes.