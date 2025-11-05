"""The Irrigation Addon integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import IrrigationCoordinator
from .services import IrrigationServices

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Irrigation Addon component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Irrigation Addon from a config entry."""
    _LOGGER.debug("Setting up Irrigation Addon integration")
    
    # Create coordinator
    coordinator = IrrigationCoordinator(hass, entry)
    
    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup coordinator (loads storage)
    await coordinator.async_setup()
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_register_services(hass, coordinator)
    
    # Register web panel
    _LOGGER.debug("Attempting to register irrigation panel...")
    await _async_register_panel(hass)
    
    _LOGGER.info("Irrigation Addon integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Irrigation Addon integration")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove coordinator from hass data
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if this was the last entry
        if not hass.data[DOMAIN]:
            _async_remove_services(hass)
            _async_remove_panel(hass)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    return True


async def _async_register_services(hass: HomeAssistant, coordinator: IrrigationCoordinator) -> None:
    """Register integration services."""
    try:
        # Create services handler if it doesn't exist
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        
        if "services" not in hass.data[DOMAIN]:
            services = IrrigationServices(hass)
            services.async_register_services()
            hass.data[DOMAIN]["services"] = services
            _LOGGER.info("Irrigation services registered")
        
    except Exception as e:
        _LOGGER.error("Failed to register services: %s", e)


def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    try:
        if DOMAIN in hass.data and "services" in hass.data[DOMAIN]:
            services = hass.data[DOMAIN]["services"]
            services.async_remove_services()
            del hass.data[DOMAIN]["services"]
            _LOGGER.info("Irrigation services removed")
            
    except Exception as e:
        _LOGGER.error("Failed to remove services: %s", e)


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the web panel."""
    import os
    
    try:
        # Check if panel files exist
        www_path = hass.config.path(f"custom_components/{DOMAIN}/www")
        html_file = os.path.join(www_path, "irrigation-panel.html")
        
        _LOGGER.debug(f"Checking for panel files at: {www_path}")
        _LOGGER.debug(f"HTML file exists: {os.path.exists(html_file)}")
        
        # Register static files for the web panel
        hass.http.register_static_path(
            f"/api/{DOMAIN}/www",
            www_path,
            cache_headers=False,
        )
        _LOGGER.debug("Static path registered successfully")
        
        # Register the irrigation panel in the sidebar using the correct method
        hass.components.frontend.async_register_built_in_panel(
            component_name="iframe",
            sidebar_title="Irrigation",
            sidebar_icon="mdi:sprinkler-variant",
            frontend_url_path="irrigation",
            config={
                "url": f"/api/{DOMAIN}/www/irrigation-panel.html"
            },
            require_admin=False,
        )
        
        _LOGGER.info("Irrigation panel registered successfully in sidebar")
        
    except Exception as e:
        _LOGGER.error("Failed to register irrigation panel: %s", e)
        # Try alternative registration method for older HA versions
        try:
            hass.components.frontend.async_register_built_in_panel(
                "iframe",
                "Irrigation",
                "mdi:sprinkler-variant",
                "irrigation",
                {"url": f"/api/{DOMAIN}/www/irrigation-panel.html"},
                require_admin=False,
            )
            _LOGGER.info("Irrigation panel registered with alternative method")
        except Exception as e2:
            _LOGGER.error("Alternative panel registration also failed: %s", e2)
            # Final fallback - try the simplest registration
            try:
                hass.components.frontend.async_register_built_in_panel(
                    "iframe",
                    "Irrigation",
                    "mdi:sprinkler-variant",
                    "irrigation",
                    {"url": f"/api/{DOMAIN}/www/irrigation-panel.html"}
                )
                _LOGGER.info("Irrigation panel registered with simple method")
            except Exception as e3:
                _LOGGER.error("All panel registration methods failed: %s", e3)


def _async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the web panel."""
    try:
        # Remove the panel from frontend
        hass.components.frontend.async_remove_panel("irrigation")
        _LOGGER.info("Irrigation panel removed successfully")
        
    except Exception as e:
        _LOGGER.error("Failed to remove irrigation panel: %s", e)