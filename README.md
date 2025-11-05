# Irrigation Addon for Home Assistant

[![Tests](https://github.com/mediflowernz/ha-irrigation-addon/workflows/Tests/badge.svg)](https://github.com/mediflowernz/ha-irrigation-addon/actions)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/release/mediflowernz/ha-irrigation-addon.svg)](https://github.com/mediflowernz/ha-irrigation-addon/releases)

A comprehensive **Home Assistant Custom Integration** designed specifically for professional cannabis cultivation. This integration provides automated irrigation control with advanced scheduling, real-time monitoring, and fail-safe mechanisms across multiple growing rooms.

> **⚠️ Important**: This is a **Custom Integration**, not a Home Assistant Add-on. Install via HACS or manual installation.

## Features

### 🏠 Multi-Room Management
- Control irrigation across multiple growing rooms
- Individual pump and zone configuration per room
- Room-specific sensor monitoring and settings

### ⏰ Advanced Scheduling
- Create P1 and P2 irrigation events with multiple shots
- Cron-based scheduling for precise timing control
- Shot-level configuration with duration and intervals
- Enable/disable events without losing configuration

### 📊 Real-Time Monitoring
- Live soil relative humidity (RH) monitoring
- Temperature and electrical conductivity (EC) sensors
- Real-time status updates via WebSocket
- Historical event tracking and logging

### 🎮 Manual Control
- Manual run capabilities with timer control
- Emergency stop functionality for all rooms
- Quick-access controls on main dashboard
- Progress indicators during active irrigation

### 🛡️ Fail-Safe Mechanisms
- Light schedule integration prevents irrigation during lights-off
- Over-watering prevention with daily limits
- Entity availability checks before activation

## 📦 Installation

### HACS (Recommended)
1. Install [HACS](https://hacs.xyz/) if not already installed
2. Go to HACS → Integrations
3. Click the three dots → Custom repositories
4. Add: `https://github.com/mediflowernz/ha-irrigation-addon`
5. Category: Integration
6. Install "Irrigation Addon"
7. Restart Home Assistant
8. Add integration via Settings → Devices & Services

### Manual Installation
1. Download from [releases](https://github.com/mediflowernz/ha-irrigation-addon/releases)
2. Copy `custom_components/irrigation_addon/` to your HA config directory
3. Restart Home Assistant
4. Add integration via Settings → Devices & Services

> **📖 Detailed Guide**: See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for complete instructions
- Comprehensive error handling and recovery

### 🎨 Professional Interface
- Custom web panel optimized for cannabis cultivation
- Responsive design for desktop and mobile
- Drag-and-drop shot reordering
- Intuitive event and shot management

### 🔧 Home Assistant Integration
- Full integration with HA entities and automations
- Exposed services for advanced automation
- Sensor and switch entities for monitoring
- Configuration flow with validation

## Installation

### HACS (Recommended)

1. **Install HACS** if you haven't already
2. **Add Custom Repository**:
   - Go to HACS → Integrations
   - Click the three dots menu → Custom repositories
   - Add `https://github.com/irrigation-addon/ha-irrigation-addon`
   - Select category "Integration"
3. **Install Integration**:
   - Search for "Irrigation Addon" in HACS
   - Click "Install"
   - Restart Home Assistant

### Manual Installation

1. **Download** the latest release from [GitHub releases](https://github.com/irrigation-addon/ha-irrigation-addon/releases)
2. **Extract** the `irrigation_addon.zip` file
3. **Copy** the `custom_components/irrigation_addon/` folder to your Home Assistant `custom_components/` directory
4. **Restart** Home Assistant

## Quick Start

### 1. Add Integration

After installation:
1. Go to **Settings** → **Devices & Services**
2. Click **"Add Integration"**
3. Search for **"Irrigation Addon"**
4. Follow the setup wizard

### 2. Configure Your First Room

1. **Open the Irrigation Panel** from the sidebar
2. **Add a Room**:
   - Click "Add Room"
   - Enter room name (e.g., "Veg Room 1")
   - Select pump entity (switch)
   - Add zone entities (switches)
   - Optional: Select light entity and sensors
3. **Save Configuration**

### 3. Create Irrigation Events

1. **Navigate to Event Management**
2. **Create P1 Event** (primary watering):
   - Set schedule (e.g., "0 8,20 * * *" for 8 AM and 8 PM daily)
   - Add shots with duration and intervals
3. **Create P2 Event** (secondary/feeding):
   - Configure different schedule and shots
4. **Enable Events** and monitor execution

## Configuration Examples

### Basic Room Setup

```yaml
# Example room configuration
Room: "Veg Room 1"
Pump: switch.veg_pump_1
Zones: 
  - switch.veg_zone_1a
  - switch.veg_zone_1b
Light: light.veg_lights_1
Sensors:
  Soil RH: sensor.veg_soil_rh_1
  Temperature: sensor.veg_temp_1
  EC: sensor.veg_ec_1
```

### P1 Event Example (Morning/Evening Watering)

```yaml
Schedule: "0 8,20 * * *"  # 8 AM and 8 PM daily
Shots:
  - Duration: 30 seconds, Interval: 5 minutes
  - Duration: 45 seconds, Interval: 5 minutes  
  - Duration: 30 seconds, Interval: 0 seconds
```

### P2 Event Example (Nutrient Feeding)

```yaml
Schedule: "0 12 * * 1,3,5"  # Noon on Mon, Wed, Fri
Shots:
  - Duration: 60 seconds, Interval: 10 minutes
  - Duration: 90 seconds, Interval: 0 seconds
```

### Advanced Cron Schedules

```yaml
# Every 4 hours during lights-on (6 AM to 10 PM)
"0 6,10,14,18,22 * * *"

# Twice daily with different weekend schedule
"0 8,20 * * 1-5"  # Weekdays
"0 9,19 * * 6,7"  # Weekends

# Every other day at specific times
"0 8,20 */2 * *"
```

## Services

The integration exposes several services for automation:

### `irrigation_addon.start_manual_run`

Start manual irrigation for a specific room.

```yaml
service: irrigation_addon.start_manual_run
data:
  room_id: "veg_room_1"
  duration: 300  # seconds
```

### `irrigation_addon.stop_irrigation`

Stop active irrigation for a room.

```yaml
service: irrigation_addon.stop_irrigation
data:
  room_id: "veg_room_1"
```

### `irrigation_addon.enable_event`

Enable or disable an irrigation event.

```yaml
service: irrigation_addon.enable_event
data:
  room_id: "veg_room_1"
  event_type: "P1"
  enabled: true
```

### `irrigation_addon.add_shot_to_event`

Add a shot to an existing event.

```yaml
service: irrigation_addon.add_shot_to_event
data:
  room_id: "veg_room_1"
  event_type: "P1"
  duration: 45
  interval: 300
```

## Automation Examples

### Stop Irrigation When Lights Turn Off

```yaml
automation:
  - alias: "Stop irrigation when lights off"
    trigger:
      - platform: state
        entity_id: light.veg_lights_1
        to: "off"
    action:
      - service: irrigation_addon.stop_irrigation
        data:
          room_id: "veg_room_1"
```

### Adjust Irrigation Based on Soil Moisture

```yaml
automation:
  - alias: "Skip irrigation if soil is wet"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.veg_soil_rh_1
        below: 70
    action:
      - service: irrigation_addon.start_manual_run
        data:
          room_id: "veg_room_1"
          duration: 180
```

## Troubleshooting

### Common Issues

#### Integration Not Loading
- **Check logs**: Look for errors in Home Assistant logs
- **Verify installation**: Ensure files are in correct directory
- **Restart required**: Always restart HA after installation

#### Entities Not Found
- **Entity validation**: Check that pump/zone entities exist in HA
- **Entity states**: Ensure entities are available (not unavailable/unknown)
- **Permissions**: Verify HA can control the entities

#### Irrigation Not Starting
- **Light schedule**: Check if fail-safe is preventing irrigation
- **Entity availability**: Verify pump and zone entities are available
- **Daily limits**: Check if over-watering prevention is active
- **Event schedule**: Verify cron expression is correct

#### Web Panel Not Loading
- **Clear cache**: Clear browser cache and reload
- **Check network**: Ensure WebSocket connection is working
- **Frontend errors**: Check browser console for JavaScript errors

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.irrigation_addon: debug
```

### Log Analysis

Common log patterns to look for:

```
# Successful irrigation start
INFO: Starting irrigation event P1 for room veg_room_1

# Fail-safe prevention
WARNING: Irrigation prevented - lights are off for room veg_room_1

# Entity unavailable
ERROR: Pump entity switch.veg_pump_1 is unavailable

# Over-watering prevention
WARNING: Daily irrigation limit reached for room veg_room_1
```

## Hardware Requirements

### Minimum Setup
- **Pump**: One switch entity per room (relay, smart switch, etc.)
- **Home Assistant**: Version 2023.1.0 or newer

### Recommended Setup
- **Zones**: Multiple zone switches for precise control
- **Sensors**: Soil RH, temperature, and EC sensors
- **Lights**: Light entities for fail-safe integration
- **Network**: Stable network connection for real-time updates

### Compatible Hardware
- **Relays**: Sonoff, Shelly, ESP32-based relays
- **Sensors**: Xiaomi, Sonoff, custom ESP32 sensors
- **Pumps**: Any 12V/24V water pumps with relay control
- **Valves**: Solenoid valves for zone control

## Development

### Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Local Development

```bash
# Clone repository
git clone https://github.com/mediflowernz/ha-irrigation-addon.git

# Install in development mode
ln -s $(pwd)/custom_components/irrigation_addon /path/to/homeassistant/custom_components/

# Enable debug logging
# Add logger configuration to configuration.yaml
```

### Testing

```bash
# Run tests (when available)
python -m pytest tests/

# Validate manifest
python scripts/validate_manifest.py

# Update version
python scripts/update_version.py 1.0.1
```

## Support

- **Documentation**: [GitHub Wiki](https://github.com/mediflowernz/ha-irrigation-addon/wiki)
- **Issues**: [GitHub Issues](https://github.com/mediflowernz/ha-irrigation-addon/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mediflowernz/ha-irrigation-addon/discussions)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Home Assistant community for the excellent platform
- HACS for making custom integrations accessible
- Cannabis cultivation community for inspiration and feedback

---

**⚠️ Legal Notice**: This software is designed for legal cannabis cultivation in jurisdictions where it is permitted. Users are responsible for compliance with local laws and regulations.