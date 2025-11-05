# Irrigation Addon for Home Assistant

A comprehensive Home Assistant irrigation addon designed specifically for professional cannabis cultivation. This integration provides automated irrigation control with advanced scheduling, real-time monitoring, and fail-safe mechanisms.

## Features

- **Multi-Room Management**: Control irrigation across multiple growing rooms
- **Advanced Scheduling**: Create P1 and P2 irrigation events with multiple shots
- **Real-Time Monitoring**: Monitor soil RH, temperature, and EC sensors
- **Manual Control**: Manual run capabilities with timer control
- **Fail-Safe Mechanisms**: Light schedule integration and over-watering prevention
- **Professional UI**: Custom web panel optimized for cannabis cultivation
- **Home Assistant Integration**: Full integration with HA entities and automations

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the "+" button
4. Search for "Irrigation Addon"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Extract the files to `custom_components/irrigation_addon/` in your Home Assistant configuration directory
3. Restart Home Assistant

## Configuration

After installation, add the integration through the Home Assistant UI:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Irrigation Addon"
4. Follow the setup wizard

## Requirements

- Home Assistant 2023.1.0 or newer
- Pump and zone entities (switches) configured in Home Assistant
- Optional: Light schedule entities for fail-safe integration
- Optional: Environmental sensors (soil RH, temperature, EC)

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/irrigation-addon/ha-irrigation-addon).