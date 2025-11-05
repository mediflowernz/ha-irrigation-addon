# Troubleshooting Guide

This guide covers common issues and their solutions for the Irrigation Addon.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Irrigation Not Working](#irrigation-not-working)
- [Web Panel Issues](#web-panel-issues)
- [Performance Problems](#performance-problems)
- [Debug and Logging](#debug-and-logging)
- [FAQ](#faq)

## Installation Issues

### Integration Not Appearing in HACS

**Symptoms:**
- Cannot find "Irrigation Addon" in HACS
- Search returns no results

**Solutions:**
1. **Add Custom Repository:**
   ```
   URL: https://github.com/irrigation-addon/ha-irrigation-addon
   Category: Integration
   ```

2. **Refresh HACS:**
   - Go to HACS → Three dots menu → Reload

3. **Check HACS Version:**
   - Ensure HACS is updated to latest version
   - Minimum HACS version: 1.6.0

### Integration Won't Load After Installation

**Symptoms:**
- Integration appears in HACS but not in HA integrations
- Error messages in logs about missing files

**Solutions:**
1. **Verify File Structure:**
   ```
   custom_components/
   └── irrigation_addon/
       ├── __init__.py
       ├── manifest.json
       ├── config_flow.py
       └── ... (other files)
   ```

2. **Check Permissions:**
   - Ensure HA can read the files
   - On Linux: `chown -R homeassistant:homeassistant custom_components/`

3. **Restart Home Assistant:**
   - Full restart required after installation
   - Check logs during startup for errors

### Dependency Issues

**Symptoms:**
- Import errors in logs
- Missing module errors

**Solutions:**
1. **Check Requirements:**
   - Ensure `croniter>=1.3.0` is installed
   - HA should install automatically

2. **Manual Installation:**
   ```bash
   pip install croniter>=1.3.0
   ```

3. **Check Python Version:**
   - Ensure HA is running Python 3.9+

## Configuration Problems

### Cannot Add Integration

**Symptoms:**
- "Add Integration" doesn't show Irrigation Addon
- Setup wizard doesn't appear

**Solutions:**
1. **Clear Browser Cache:**
   - Hard refresh (Ctrl+F5)
   - Clear HA frontend cache

2. **Check Integration Status:**
   - Look for errors in HA logs
   - Verify manifest.json is valid

3. **Restart and Retry:**
   - Restart HA completely
   - Wait 2-3 minutes before trying again

### Entity Validation Errors

**Symptoms:**
- "Entity not found" errors during setup
- Cannot select pump or zone entities

**Solutions:**
1. **Verify Entity Existence:**
   ```yaml
   # Check in Developer Tools → States
   switch.veg_pump_1: "on"  # Should exist
   ```

2. **Check Entity Domain:**
   - Pumps must be `switch` entities
   - Zones must be `switch` entities
   - Lights can be `light` or `switch` entities

3. **Entity Availability:**
   - Ensure entities are not `unavailable` or `unknown`
   - Check underlying device connectivity

### Room Configuration Issues

**Symptoms:**
- Cannot save room configuration
- Settings not persisting

**Solutions:**
1. **Check Storage Permissions:**
   - Ensure HA can write to `.storage/` directory
   - Check disk space availability

2. **Validate Configuration:**
   - Room names must be unique
   - At least one pump entity required
   - Entity IDs must be valid

3. **Reset Configuration:**
   - Delete integration and re-add
   - Check `.storage/irrigation_addon_*` files

## Irrigation Not Working

### Events Not Triggering

**Symptoms:**
- Scheduled events don't start
- No irrigation activity at scheduled times

**Solutions:**
1. **Verify Event Schedule:**
   ```
   # Check cron expression
   "0 8,20 * * *"  # 8 AM and 8 PM daily
   
   # Test with online cron validator
   https://crontab.guru/
   ```

2. **Check Event Status:**
   - Ensure events are enabled
   - Verify room configuration is complete

3. **Light Schedule Conflicts:**
   - Check if lights are off during scheduled time
   - Disable fail-safe temporarily for testing

4. **Time Zone Issues:**
   - Verify HA time zone matches local time
   - Check system clock accuracy

### Manual Run Not Working

**Symptoms:**
- Manual run button doesn't respond
- Timer starts but irrigation doesn't begin

**Solutions:**
1. **Entity State Check:**
   ```yaml
   # Verify in Developer Tools
   switch.veg_pump_1: "off"  # Should be controllable
   switch.veg_zone_1: "off"  # Should be available
   ```

2. **Check Entity Control:**
   - Test pump/zone entities manually in HA
   - Verify entities respond to state changes

3. **Review Fail-Safes:**
   - Check light schedule integration
   - Verify daily limits not exceeded
   - Look for entity availability issues

### Irrigation Stops Unexpectedly

**Symptoms:**
- Irrigation starts but stops before completion
- Partial shot execution

**Solutions:**
1. **Check Entity Availability:**
   - Monitor entity states during irrigation
   - Look for connectivity issues

2. **Power/Hardware Issues:**
   - Verify pump power supply
   - Check relay/switch functionality
   - Monitor for hardware failures

3. **Review Logs:**
   ```yaml
   # Enable debug logging
   logger:
     logs:
       custom_components.irrigation_addon: debug
   ```

## Web Panel Issues

### Panel Not Loading

**Symptoms:**
- Blank page when accessing irrigation panel
- "Failed to load" errors

**Solutions:**
1. **Clear Browser Cache:**
   - Hard refresh (Ctrl+F5)
   - Clear all browser data for HA

2. **Check Browser Console:**
   - Open Developer Tools (F12)
   - Look for JavaScript errors
   - Check network requests

3. **Verify Panel Registration:**
   - Check HA logs for panel registration errors
   - Ensure `www/` files are present

### Real-Time Updates Not Working

**Symptoms:**
- Sensor data not updating
- Status changes not reflected immediately

**Solutions:**
1. **WebSocket Connection:**
   - Check browser network tab for WebSocket errors
   - Verify HA WebSocket is working

2. **Coordinator Updates:**
   - Check coordinator update interval
   - Look for coordinator errors in logs

3. **Network Issues:**
   - Verify stable network connection
   - Check for proxy/firewall issues

### UI Elements Not Responding

**Symptoms:**
- Buttons don't work
- Forms don't submit
- Drag-and-drop not functioning

**Solutions:**
1. **Browser Compatibility:**
   - Use modern browser (Chrome, Firefox, Safari)
   - Disable browser extensions temporarily

2. **JavaScript Errors:**
   - Check browser console for errors
   - Look for conflicting custom cards/themes

3. **Mobile Issues:**
   - Try desktop browser
   - Check responsive design breakpoints

## Performance Problems

### Slow Response Times

**Symptoms:**
- Long delays when starting irrigation
- Slow UI updates
- Timeouts during operations

**Solutions:**
1. **Reduce Update Frequency:**
   ```yaml
   # In settings, increase update intervals
   Sensor Update Interval: 60 seconds  # Default: 30
   ```

2. **Check System Resources:**
   - Monitor HA CPU/memory usage
   - Check database size and performance

3. **Network Optimization:**
   - Ensure stable network connection
   - Minimize network latency to devices

### High CPU Usage

**Symptoms:**
- HA becomes slow when irrigation is active
- High CPU usage in system monitor

**Solutions:**
1. **Optimize Polling:**
   - Increase sensor update intervals
   - Reduce number of monitored entities

2. **Check Loops:**
   - Look for infinite loops in logs
   - Monitor coordinator update frequency

3. **Database Cleanup:**
   - Purge old irrigation logs
   - Optimize HA database

## Debug and Logging

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.irrigation_addon: debug
    custom_components.irrigation_addon.coordinator: debug
    custom_components.irrigation_addon.config_flow: debug
```

### Important Log Messages

**Successful Operations:**
```
INFO: Irrigation event P1 started for room veg_room_1
INFO: Shot 1/3 completed (30s) for room veg_room_1
INFO: Irrigation cycle completed for room veg_room_1
```

**Warnings:**
```
WARNING: Irrigation prevented - lights off for room veg_room_1
WARNING: Daily limit reached for room veg_room_1 (5/5 events)
WARNING: Entity switch.veg_pump_1 unavailable, skipping irrigation
```

**Errors:**
```
ERROR: Failed to start pump switch.veg_pump_1: Entity not found
ERROR: Irrigation timeout for room veg_room_1 after 300 seconds
ERROR: WebSocket connection failed for real-time updates
```

### Log Analysis Tools

1. **Home Assistant Logs:**
   - Settings → System → Logs
   - Filter by "irrigation_addon"

2. **Log Files:**
   ```bash
   # Direct log file access
   tail -f /config/home-assistant.log | grep irrigation_addon
   ```

3. **External Tools:**
   - Use log analysis tools for pattern detection
   - Set up log monitoring/alerting

## FAQ

### Q: Can I use this with non-cannabis plants?

**A:** Yes, the addon works with any irrigation system. The cannabis-specific features are optional optimizations.

### Q: How many rooms can I configure?

**A:** There's no hard limit, but performance may degrade with many rooms (50+). Monitor system resources.

### Q: Can I backup my configuration?

**A:** Yes, configuration is stored in HA's `.storage/` directory. Back up these files:
- `.storage/irrigation_addon_rooms`
- `.storage/irrigation_addon_settings`

### Q: Does this work with Zigbee/Z-Wave devices?

**A:** Yes, as long as the devices appear as switch entities in Home Assistant.

### Q: Can I run irrigation during lights-off?

**A:** Yes, disable the fail-safe in settings or don't configure light entities.

### Q: How do I update the integration?

**A:** Through HACS (automatic) or manually replace files and restart HA.

### Q: Can I use this with existing irrigation controllers?

**A:** Yes, if your controller exposes switch entities to Home Assistant.

### Q: What happens if Home Assistant restarts during irrigation?

**A:** Active irrigation will stop. The system will resume normal scheduling after restart.

### Q: Can I integrate with other HA automations?

**A:** Yes, use the exposed services and sensor entities in your automations.

### Q: Is there a mobile app?

**A:** The web panel is responsive and works well on mobile browsers. No dedicated app needed.

---

## Getting Help

If you can't resolve your issue:

1. **Check GitHub Issues:** [Search existing issues](https://github.com/irrigation-addon/ha-irrigation-addon/issues)
2. **Create New Issue:** Include logs, configuration, and steps to reproduce
3. **Community Forum:** Post in [Home Assistant Community](https://community.home-assistant.io/)
4. **Documentation:** Review [full documentation](https://github.com/irrigation-addon/ha-irrigation-addon/wiki)

When reporting issues, always include:
- Home Assistant version
- Irrigation Addon version
- Relevant log entries
- Configuration details (remove sensitive info)
- Steps to reproduce the problem