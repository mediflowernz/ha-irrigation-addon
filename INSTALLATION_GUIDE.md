# Installation Guide - Home Assistant Custom Integration

## ⚠️ Important: This is a Custom Integration, NOT an Add-on

This is a **Home Assistant Custom Integration** that adds irrigation control functionality to your Home Assistant instance. It is **NOT** a Home Assistant Add-on.

## Installation Methods

### Method 1: HACS (Recommended)

1. **Install HACS** (if not already installed):
   - Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)

2. **Add Custom Repository**:
   - Open HACS in Home Assistant
   - Go to **Integrations**
   - Click the **three dots** in the top right corner
   - Select **Custom repositories**
   - Add this URL: `https://github.com/mediflowernz/ha-irrigation-addon`
   - Category: **Integration**
   - Click **Add**

3. **Install the Integration**:
   - Search for "Irrigation Addon" in HACS
   - Click **Download**
   - Restart Home Assistant

4. **Add the Integration**:
   - Go to **Settings** → **Devices & Services**
   - Click **Add Integration**
   - Search for "Irrigation Addon"
   - Follow the setup wizard

### Method 2: Manual Installation

1. **Download the Integration**:
   - Download the latest release from [GitHub Releases](https://github.com/mediflowernz/ha-irrigation-addon/releases)
   - Or clone: `git clone https://github.com/mediflowernz/ha-irrigation-addon.git`

2. **Copy Files**:
   ```
   # Copy the integration folder to your Home Assistant config directory
   /config/custom_components/irrigation_addon/
   ```

3. **Restart Home Assistant**

4. **Add the Integration**:
   - Go to **Settings** → **Devices & Services**
   - Click **Add Integration**
   - Search for "Irrigation Addon"
   - Follow the setup wizard

## Verification

After installation, you should see:

1. **Integration Added**: In Settings → Devices & Services
2. **New Entities**: Switches and sensors for your irrigation system
3. **Services Available**: New irrigation services in Developer Tools
4. **Web Panel**: Irrigation dashboard accessible from sidebar

## Troubleshooting

### "Not a valid add-on repository" Error

This error occurs when trying to install this as an **Add-on** instead of a **Custom Integration**:

- ❌ **Wrong**: Adding to Home Assistant Add-on Store
- ✅ **Correct**: Installing via HACS as a Custom Integration

### Integration Not Found

If the integration doesn't appear after installation:

1. **Check File Location**:
   ```
   /config/custom_components/irrigation_addon/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   └── ... (other files)
   ```

2. **Check Logs**:
   - Go to Settings → System → Logs
   - Look for "irrigation_addon" errors

3. **Restart Required**:
   - Always restart Home Assistant after manual installation

### HACS Not Finding Repository

If HACS can't find the repository:

1. **Check URL**: Ensure you're using `https://github.com/mediflowernz/ha-irrigation-addon`
2. **Category**: Must be set to "Integration"
3. **Repository Access**: Repository must be public (it is)

## Requirements

- **Home Assistant**: 2023.1.0 or newer
- **Python**: 3.8 or newer (included with Home Assistant)
- **Dependencies**: Automatically installed (croniter)

## Hardware Requirements

- **Pump Control**: Switch entities (relays, smart switches)
- **Zone Control**: Switch entities for irrigation zones
- **Sensors**: Optional soil moisture, temperature sensors
- **Lights**: Optional light entities for schedule integration

## Next Steps

After installation:

1. **Configure Rooms**: Add your growing rooms
2. **Set up Hardware**: Configure pump and zone entities
3. **Create Events**: Set up P1/P2 irrigation schedules
4. **Test System**: Run manual irrigation tests
5. **Enable Automation**: Set up automated schedules

## Support

- **Documentation**: [GitHub Repository](https://github.com/mediflowernz/ha-irrigation-addon)
- **Issues**: [Report Problems](https://github.com/mediflowernz/ha-irrigation-addon/issues)
- **Discussions**: [Community Support](https://github.com/mediflowernz/ha-irrigation-addon/discussions)

## Legal Notice

This software is designed for legal cannabis cultivation in jurisdictions where it is permitted. Users are responsible for compliance with local laws and regulations.