# Installation Guide

This guide provides detailed instructions for installing the Irrigation Addon for Home Assistant.

## Table of Contents

- [Prerequisites](#prerequisites)
- [HACS Installation (Recommended)](#hacs-installation-recommended)
- [Manual Installation](#manual-installation)
- [Initial Configuration](#initial-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Updating](#updating)

## Prerequisites

### Home Assistant Requirements

- **Home Assistant**: Version 2023.1.0 or newer
- **HACS**: Version 1.6.0 or newer (for HACS installation)
- **Python**: 3.9 or newer (usually included with HA)

### Hardware Requirements

**Minimum Setup:**
- At least one switch entity for pump control
- Home Assistant instance with network connectivity

**Recommended Setup:**
- Multiple switch entities for pumps and zones
- Environmental sensors (soil moisture, temperature, EC)
- Light entities for fail-safe integration
- Stable network connection for real-time updates

### Entity Requirements

Before installation, ensure you have the following entities configured in Home Assistant:

**Required:**
- **Pump entities**: `switch.pump_name` (one per room)

**Optional but Recommended:**
- **Zone entities**: `switch.zone_name` (multiple per room)
- **Light entities**: `light.light_name` or `switch.light_name`
- **Sensor entities**: 
  - `sensor.soil_moisture_name`
  - `sensor.temperature_name`
  - `sensor.ec_name`

## HACS Installation (Recommended)

### Step 1: Install HACS

If you don't have HACS installed:

1. Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant
3. Complete HACS setup through the UI

### Step 2: Add Custom Repository

1. **Open HACS**:
   - Go to HACS in your Home Assistant sidebar
   - Click on "Integrations"

2. **Add Repository**:
   - Click the three dots menu (⋮) in the top right
   - Select "Custom repositories"
   - Add the following:
     ```
     URL: https://github.com/irrigation-addon/ha-irrigation-addon
     Category: Integration
     ```
   - Click "Add"

### Step 3: Install Integration

1. **Search for Integration**:
   - In HACS Integrations, click the "+" button
   - Search for "Irrigation Addon"
   - Click on the integration

2. **Install**:
   - Click "Install"
   - Select the latest version
   - Click "Install" again

3. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Wait for restart to complete

## Manual Installation

### Step 1: Download Files

1. **Download Release**:
   - Go to [GitHub Releases](https://github.com/irrigation-addon/ha-irrigation-addon/releases)
   - Download the latest `irrigation_addon.zip`

2. **Extract Files**:
   - Extract the ZIP file
   - You should see a `custom_components/irrigation_addon/` folder

### Step 2: Copy Files

1. **Locate HA Config Directory**:
   ```
   # Common locations:
   /config/                    # Home Assistant OS
   ~/.homeassistant/           # Manual installation
   /usr/share/hassio/homeassistant/  # Supervised
   ```

2. **Create Directory Structure**:
   ```bash
   mkdir -p /config/custom_components/
   ```

3. **Copy Integration Files**:
   ```bash
   cp -r irrigation_addon/ /config/custom_components/
   ```

4. **Verify Structure**:
   ```
   /config/custom_components/irrigation_addon/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   ├── coordinator.py
   ├── models.py
   ├── storage.py
   ├── services.py
   ├── sensor.py
   ├── switch.py
   ├── exceptions.py
   ├── logging_utils.py
   ├── services.yaml
   ├── strings.json
   ├── translations/
   │   └── en.json
   └── www/
       ├── irrigation-panel.html
       ├── irrigation-panel.js
       └── irrigation-panel.css
   ```

### Step 3: Set Permissions

```bash
# Ensure Home Assistant can read the files
chown -R homeassistant:homeassistant /config/custom_components/irrigation_addon/
chmod -R 755 /config/custom_components/irrigation_addon/
```

### Step 4: Restart Home Assistant

Restart Home Assistant to load the new integration.

## Initial Configuration

### Step 1: Add Integration

1. **Navigate to Integrations**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"

2. **Find Irrigation Addon**:
   - Search for "Irrigation Addon"
   - Click on it to start setup

### Step 2: Basic Setup

1. **Integration Name**:
   - Enter a name for your irrigation system
   - Default: "Irrigation System"

2. **Initial Settings**:
   - **Sensor Update Interval**: 30 seconds (recommended)
   - **Pump-Zone Delay**: 3 seconds (safety delay)
   - **Enable Fail-Safe**: Yes (recommended for safety)

3. **Complete Setup**:
   - Click "Submit"
   - Integration will be added to your system

### Step 3: Configure First Room

1. **Access Irrigation Panel**:
   - Look for "Irrigation" in your sidebar
   - Click to open the panel

2. **Add Room**:
   - Click "Add Room" button
   - Enter room details:
     ```
     Name: "Veg Room 1"
     Pump Entity: switch.veg_pump_1
     Zone Entities: switch.veg_zone_1a, switch.veg_zone_1b
     Light Entity: light.veg_lights_1 (optional)
     ```

3. **Add Sensors** (optional):
   ```
   Soil RH: sensor.veg_soil_rh_1
   Temperature: sensor.veg_temp_1
   EC: sensor.veg_ec_1
   ```

4. **Save Configuration**:
   - Click "Save Room"
   - Room will appear in dashboard

### Step 4: Create First Event

1. **Navigate to Events**:
   - Click "Manage Events" for your room
   - Click "Add Event"

2. **Configure P1 Event**:
   ```
   Event Type: P1
   Schedule: 0 8,20 * * *  (8 AM and 8 PM daily)
   Enabled: Yes
   ```

3. **Add Shots**:
   ```
   Shot 1: 30 seconds, 5 minute interval
   Shot 2: 45 seconds, 5 minute interval  
   Shot 3: 30 seconds, no interval
   ```

4. **Save Event**:
   - Click "Save Event"
   - Event will be scheduled automatically

## Verification

### Step 1: Check Integration Status

1. **Integration Page**:
   - Go to Settings → Devices & Services
   - Find "Irrigation Addon"
   - Should show "Configured" status

2. **Check Entities**:
   - Click on the integration
   - Verify entities are created:
     - `sensor.irrigation_status_[room_name]`
     - `switch.irrigation_manual_[room_name]`

### Step 2: Test Manual Run

1. **Access Panel**:
   - Go to Irrigation panel in sidebar
   - Find your configured room

2. **Start Manual Run**:
   - Click "Manual Run" button
   - Set duration to 10 seconds (for testing)
   - Click "Start"

3. **Verify Operation**:
   - Pump should turn on first
   - Zones should activate after 3-second delay
   - Should stop automatically after 10 seconds

### Step 3: Check Logs

1. **Enable Debug Logging** (temporary):
   ```yaml
   # Add to configuration.yaml
   logger:
     logs:
       custom_components.irrigation_addon: debug
   ```

2. **Check Logs**:
   - Go to Settings → System → Logs
   - Look for irrigation_addon entries
   - Should see successful initialization messages

## Troubleshooting

### Integration Not Loading

**Problem**: Integration doesn't appear in available integrations.

**Solutions**:
1. **Check File Structure**:
   ```bash
   ls -la /config/custom_components/irrigation_addon/
   # Should show all required files
   ```

2. **Check Manifest**:
   ```bash
   cat /config/custom_components/irrigation_addon/manifest.json
   # Should be valid JSON
   ```

3. **Check Logs**:
   - Look for Python import errors
   - Verify all dependencies are installed

4. **Clear Cache**:
   - Clear browser cache
   - Restart Home Assistant

### Entity Validation Errors

**Problem**: Cannot select pump or zone entities during setup.

**Solutions**:
1. **Verify Entity Existence**:
   - Go to Developer Tools → States
   - Search for your entity IDs
   - Ensure they exist and are available

2. **Check Entity Domain**:
   - Pumps must be `switch` entities
   - Zones must be `switch` entities
   - Lights can be `light` or `switch` entities

3. **Test Entity Control**:
   - Manually turn entities on/off in HA
   - Verify they respond correctly

### Manual Run Not Working

**Problem**: Manual run starts but irrigation doesn't happen.

**Solutions**:
1. **Check Entity States**:
   ```yaml
   # In Developer Tools → States
   switch.pump_entity: "off"  # Should be controllable
   ```

2. **Verify Fail-Safe Settings**:
   - Check if lights are off (if light entity configured)
   - Verify daily limits not exceeded
   - Check entity availability

3. **Test Entities Manually**:
   - Turn pump on/off manually in HA
   - Verify physical hardware responds

### Panel Not Loading

**Problem**: Irrigation panel shows blank page or errors.

**Solutions**:
1. **Clear Browser Cache**:
   - Hard refresh (Ctrl+F5)
   - Clear all browser data for HA

2. **Check Browser Console**:
   - Open Developer Tools (F12)
   - Look for JavaScript errors
   - Check network requests

3. **Verify Files**:
   ```bash
   ls -la /config/custom_components/irrigation_addon/www/
   # Should show HTML, JS, and CSS files
   ```

## Updating

### HACS Update

1. **Check for Updates**:
   - Go to HACS → Integrations
   - Look for update notification on Irrigation Addon

2. **Update**:
   - Click "Update" button
   - Select new version
   - Click "Install"

3. **Restart**:
   - Restart Home Assistant
   - Verify functionality after update

### Manual Update

1. **Backup Configuration**:
   - Export current configuration from panel
   - Note current settings

2. **Download New Version**:
   - Get latest release from GitHub
   - Extract files

3. **Replace Files**:
   ```bash
   # Backup current installation
   cp -r /config/custom_components/irrigation_addon/ /config/irrigation_addon_backup/
   
   # Replace with new files
   rm -rf /config/custom_components/irrigation_addon/
   cp -r new_irrigation_addon/ /config/custom_components/irrigation_addon/
   ```

4. **Restart and Verify**:
   - Restart Home Assistant
   - Check that configuration is preserved
   - Test functionality

### Version Management

Check current version:
- Go to Settings → Devices & Services
- Click on Irrigation Addon integration
- Version shown in integration details

Update version tracking:
```bash
# Use included script
python /config/custom_components/irrigation_addon/scripts/update_version.py 1.0.1
```

---

## Post-Installation

### Recommended Next Steps

1. **Configure Backup**:
   - Set up regular HA backups
   - Export irrigation configuration periodically

2. **Set Up Monitoring**:
   - Create automations for irrigation alerts
   - Monitor system health sensors

3. **Optimize Settings**:
   - Adjust update intervals based on needs
   - Fine-tune fail-safe parameters

4. **Documentation**:
   - Document your specific configuration
   - Note any custom automations

### Getting Help

If you encounter issues:

1. **Check Documentation**: [GitHub Wiki](https://github.com/irrigation-addon/ha-irrigation-addon/wiki)
2. **Search Issues**: [GitHub Issues](https://github.com/irrigation-addon/ha-irrigation-addon/issues)
3. **Create Issue**: Include logs, configuration, and steps to reproduce
4. **Community Support**: [Home Assistant Community Forum](https://community.home-assistant.io/)

### Legal Compliance

Remember to ensure your use of this irrigation system complies with all local laws and regulations, especially if used for cannabis cultivation.