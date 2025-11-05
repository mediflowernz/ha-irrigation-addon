# Configuration Examples

This document provides detailed configuration examples for various irrigation setups and scenarios.

## Table of Contents

- [Basic Setups](#basic-setups)
- [Advanced Configurations](#advanced-configurations)
- [Scheduling Examples](#scheduling-examples)
- [Automation Integration](#automation-integration)
- [Fail-Safe Configurations](#fail-safe-configurations)
- [Multi-Room Scenarios](#multi-room-scenarios)

## Basic Setups

### Single Room with Basic Pump

**Scenario:** Simple setup with one pump and no zones.

```yaml
Room Configuration:
  Name: "Basic Grow Room"
  Pump: switch.grow_pump
  Zones: [] # No zones
  Light: light.grow_lights
  Sensors:
    Soil RH: sensor.soil_moisture
```

**P1 Event (Daily Watering):**
```yaml
Schedule: "0 8,20 * * *"  # 8 AM and 8 PM
Shots:
  - Duration: 60 seconds
    Interval: 0 seconds
```

### Single Room with Multiple Zones

**Scenario:** One pump feeding multiple zones for different plant areas.

```yaml
Room Configuration:
  Name: "Multi-Zone Room"
  Pump: switch.main_pump
  Zones: 
    - switch.zone_seedlings
    - switch.zone_veg_plants
    - switch.zone_flowering
  Light: light.full_spectrum_led
  Sensors:
    Soil RH: sensor.average_soil_rh
    Temperature: sensor.room_temp
    EC: sensor.nutrient_ec
```

**P1 Event (Staggered Watering):**
```yaml
Schedule: "0 7,19 * * *"  # 7 AM and 7 PM
Shots:
  - Duration: 45 seconds  # All zones get water
    Interval: 300 seconds # 5 minute break
  - Duration: 30 seconds  # Second round
    Interval: 300 seconds
  - Duration: 15 seconds  # Final light watering
    Interval: 0 seconds
```

## Advanced Configurations

### Hydroponic System with Nutrient Cycling

**Scenario:** Hydroponic setup with separate nutrient and water pumps.

```yaml
Room Configuration:
  Name: "Hydro Room A"
  Pump: switch.nutrient_pump
  Zones:
    - switch.hydro_table_1
    - switch.hydro_table_2
  Light: switch.led_array_a
  Sensors:
    Soil RH: sensor.water_level
    Temperature: sensor.nutrient_temp
    EC: sensor.nutrient_ec
```

**P1 Event (Nutrient Feed):**
```yaml
Schedule: "0 6,12,18 * * *"  # Every 6 hours
Shots:
  - Duration: 120 seconds  # Long nutrient cycle
    Interval: 900 seconds  # 15 minute drain period
  - Duration: 60 seconds   # Flush cycle
    Interval: 0 seconds
```

**P2 Event (Water Only):**
```yaml
Schedule: "0 9,15,21 * * *"  # Between nutrient feeds
Shots:
  - Duration: 30 seconds   # Quick water cycle
    Interval: 0 seconds
```

### Aeroponic System with Frequent Misting

**Scenario:** High-frequency misting system for aeroponic growing.

```yaml
Room Configuration:
  Name: "Aero Room"
  Pump: switch.mist_pump
  Zones:
    - switch.mist_zone_upper
    - switch.mist_zone_lower
  Light: light.aero_leds
  Sensors:
    Soil RH: sensor.root_chamber_humidity
    Temperature: sensor.root_temp
```

**P1 Event (Frequent Misting):**
```yaml
Schedule: "*/15 6-22 * * *"  # Every 15 minutes, 6 AM to 10 PM
Shots:
  - Duration: 5 seconds    # Short mist burst
    Interval: 300 seconds  # 5 minute interval
  - Duration: 3 seconds    # Follow-up mist
    Interval: 0 seconds
```

## Scheduling Examples

### Vegetative Stage Schedule

**Scenario:** 18/6 light cycle with frequent watering.

```yaml
# Lights on: 6 AM to 12 AM (18 hours)
Light Schedule: switch.veg_lights

P1 Event (Main Watering):
  Schedule: "0 8,14,20 * * *"  # 8 AM, 2 PM, 8 PM
  Shots:
    - Duration: 45 seconds
      Interval: 600 seconds  # 10 minutes
    - Duration: 30 seconds
      Interval: 0 seconds

P2 Event (Light Feeding):
  Schedule: "0 11,17,23 * * *"  # Between main waterings
  Shots:
    - Duration: 15 seconds
      Interval: 0 seconds
```

### Flowering Stage Schedule

**Scenario:** 12/12 light cycle with reduced watering frequency.

```yaml
# Lights on: 6 AM to 6 PM (12 hours)
Light Schedule: switch.flower_lights

P1 Event (Main Watering):
  Schedule: "0 9,21 * * *"  # 9 AM and 9 PM
  Shots:
    - Duration: 60 seconds
      Interval: 900 seconds  # 15 minutes
    - Duration: 45 seconds
      Interval: 600 seconds  # 10 minutes
    - Duration: 30 seconds
      Interval: 0 seconds

P2 Event (Nutrient Boost):
  Schedule: "0 15 * * 1,3,5"  # 3 PM on Mon, Wed, Fri
  Shots:
    - Duration: 90 seconds   # Longer nutrient feed
      Interval: 0 seconds
```

### Seasonal Adjustments

**Scenario:** Different schedules for different seasons.

```yaml
# Summer Schedule (More frequent due to heat)
P1 Event - Summer:
  Schedule: "0 6,10,14,18,22 * * *"  # Every 4 hours
  Shots:
    - Duration: 30 seconds
      Interval: 300 seconds
    - Duration: 20 seconds
      Interval: 0 seconds

# Winter Schedule (Less frequent, cooler temps)
P1 Event - Winter:
  Schedule: "0 8,16 * * *"  # Twice daily
  Shots:
    - Duration: 45 seconds
      Interval: 600 seconds
    - Duration: 30 seconds
      Interval: 0 seconds
```

## Automation Integration

### Soil Moisture-Based Irrigation

**Scenario:** Adjust irrigation based on soil moisture readings.

```yaml
# Automation to skip irrigation if soil is wet
automation:
  - alias: "Skip irrigation if soil wet"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.soil_moisture_1
        above: 75  # Skip if above 75% moisture
    action:
      - service: irrigation_addon.enable_event
        data:
          room_id: "veg_room_1"
          event_type: "P1"
          enabled: false

  - alias: "Re-enable irrigation when soil dries"
    trigger:
      - platform: numeric_state
        entity_id: sensor.soil_moisture_1
        below: 60
    action:
      - service: irrigation_addon.enable_event
        data:
          room_id: "veg_room_1"
          event_type: "P1"
          enabled: true
```

### Temperature-Based Adjustments

**Scenario:** Increase watering frequency during hot weather.

```yaml
automation:
  - alias: "Extra watering on hot days"
    trigger:
      - platform: numeric_state
        entity_id: sensor.room_temperature
        above: 85  # Above 85°F
        for:
          minutes: 30
    action:
      - service: irrigation_addon.start_manual_run
        data:
          room_id: "flower_room_1"
          duration: 120  # 2 minutes extra water

  - alias: "Reduce watering on cool days"
    trigger:
      - platform: numeric_state
        entity_id: sensor.room_temperature
        below: 70  # Below 70°F
        for:
          hours: 2
    action:
      - service: irrigation_addon.enable_event
        data:
          room_id: "flower_room_1"
          event_type: "P2"
          enabled: false  # Disable secondary watering
```

### Light Cycle Integration

**Scenario:** Coordinate irrigation with light schedules.

```yaml
automation:
  - alias: "Pre-lights watering"
    trigger:
      - platform: state
        entity_id: light.grow_lights
        to: "on"
    action:
      - delay: "00:05:00"  # Wait 5 minutes after lights on
      - service: irrigation_addon.start_manual_run
        data:
          room_id: "main_room"
          duration: 180

  - alias: "Post-lights watering"
    trigger:
      - platform: state
        entity_id: light.grow_lights
        to: "off"
    action:
      - delay: "00:30:00"  # Wait 30 minutes after lights off
      - service: irrigation_addon.start_manual_run
        data:
          room_id: "main_room"
          duration: 90
```

## Fail-Safe Configurations

### Conservative Fail-Safe Setup

**Scenario:** Maximum safety with multiple checks.

```yaml
Settings:
  Fail-Safe Enabled: true
  Daily Irrigation Limit: 8 events per room
  Pump-Zone Delay: 5 seconds  # Extra safety delay
  
Room Configuration:
  Light Entity: light.grow_lights  # Required for light checks
  
Automation for Additional Safety:
  - Monitor pump current draw
  - Check water reservoir levels
  - Verify drainage system operation
```

### Minimal Fail-Safe Setup

**Scenario:** Basic safety for experienced users.

```yaml
Settings:
  Fail-Safe Enabled: false  # Disabled for manual control
  Daily Irrigation Limit: 20 events per room
  Pump-Zone Delay: 3 seconds
  
Room Configuration:
  Light Entity: null  # No light integration
  
Manual Override Available:
  - Emergency stop always available
  - Manual run with extended timers
```

## Multi-Room Scenarios

### Commercial Grow Operation

**Scenario:** Multiple rooms with different growth stages.

```yaml
# Seedling Room
Room 1:
  Name: "Seedlings"
  Pump: switch.seedling_pump
  Zones: [switch.seed_tray_1, switch.seed_tray_2]
  Schedule: "0 */4 * * *"  # Every 4 hours
  Shot Duration: 15 seconds

# Vegetative Room
Room 2:
  Name: "Vegetative"
  Pump: switch.veg_pump
  Zones: [switch.veg_zone_a, switch.veg_zone_b]
  Schedule: "0 8,14,20 * * *"  # 3 times daily
  Shot Duration: 45 seconds

# Flowering Room 1
Room 3:
  Name: "Flower A"
  Pump: switch.flower_pump_a
  Zones: [switch.flower_zone_1, switch.flower_zone_2]
  Schedule: "0 9,21 * * *"  # Twice daily
  Shot Duration: 60 seconds

# Flowering Room 2
Room 4:
  Name: "Flower B"
  Pump: switch.flower_pump_b
  Zones: [switch.flower_zone_3, switch.flower_zone_4]
  Schedule: "0 10,22 * * *"  # Offset timing
  Shot Duration: 60 seconds
```

### Home Grow Setup

**Scenario:** Small-scale home growing with 2-3 rooms.

```yaml
# Veg Tent
Room 1:
  Name: "Veg Tent"
  Pump: switch.veg_tent_pump
  Zones: []  # Single zone
  Light: light.veg_tent_led
  Schedule: "0 8,20 * * *"
  
# Flower Tent
Room 2:
  Name: "Flower Tent"
  Pump: switch.flower_tent_pump
  Zones: []  # Single zone
  Light: light.flower_tent_led
  Schedule: "0 9,21 * * *"

# Mother Plant Area
Room 3:
  Name: "Mothers"
  Pump: switch.mother_pump
  Zones: [switch.mother_zone_1]
  Light: light.mother_area_t5
  Schedule: "0 12 * * *"  # Once daily
```

## Troubleshooting Configurations

### Debug Configuration

**Scenario:** Setup for troubleshooting issues.

```yaml
Settings:
  Sensor Update Interval: 10 seconds  # Faster updates
  Logging Level: DEBUG
  
Room Configuration:
  All entities configured for full monitoring
  
Automation:
  - Log all irrigation events
  - Monitor entity state changes
  - Alert on failures
```

### Test Configuration

**Scenario:** Safe testing setup for new installations.

```yaml
Settings:
  Daily Irrigation Limit: 2 events  # Limited for testing
  Default Shot Duration: 5 seconds  # Very short for safety
  
Room Configuration:
  Test with non-critical pumps first
  Monitor all operations closely
  
Testing Protocol:
  1. Test manual runs first
  2. Verify all entities respond
  3. Test emergency stop
  4. Gradually increase durations
```

---

## Configuration Tips

### Best Practices

1. **Start Conservative:** Begin with shorter durations and fewer events
2. **Monitor Closely:** Watch first few irrigation cycles carefully  
3. **Test Emergency Stop:** Verify emergency controls work before leaving unattended
4. **Backup Configuration:** Export settings before major changes
5. **Document Changes:** Keep notes on what works for your setup

### Common Mistakes

1. **Over-watering:** Too frequent or too long irrigation cycles
2. **No Fail-safes:** Disabling safety features without proper monitoring
3. **Wrong Entities:** Using incorrect entity types (not switches)
4. **Timing Conflicts:** Overlapping schedules between rooms
5. **No Testing:** Not testing configuration before production use

### Optimization Guidelines

1. **Sensor Placement:** Position sensors for representative readings
2. **Drainage:** Ensure proper drainage to prevent over-watering
3. **Pump Sizing:** Match pump capacity to system requirements
4. **Network Reliability:** Ensure stable network for remote monitoring
5. **Power Backup:** Consider UPS for critical systems