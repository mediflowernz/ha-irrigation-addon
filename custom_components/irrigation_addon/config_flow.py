"""Config flow for Irrigation Addon integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    DOMAIN,
    DEFAULT_PUMP_ZONE_DELAY,
    DEFAULT_SENSOR_UPDATE_INTERVAL,
    DEFAULT_MANUAL_DURATION,
    DEFAULT_FAIL_SAFE_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("name", default="Irrigation System"): str,
})

STEP_SETTINGS_DATA_SCHEMA = vol.Schema({
    vol.Optional("pump_zone_delay", default=DEFAULT_PUMP_ZONE_DELAY): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=30)
    ),
    vol.Optional("sensor_update_interval", default=DEFAULT_SENSOR_UPDATE_INTERVAL): vol.All(
        vol.Coerce(int), vol.Range(min=10, max=300)
    ),
    vol.Optional("default_manual_duration", default=DEFAULT_MANUAL_DURATION): vol.All(
        vol.Coerce(int), vol.Range(min=30, max=3600)
    ),
    vol.Optional("fail_safe_enabled", default=DEFAULT_FAIL_SAFE_ENABLED): bool,
})


class IrrigationAddonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Irrigation Addon."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._name: str | None = None
        self._settings: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if integration is already configured
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            self._name = user_input["name"]
            return await self.async_step_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the settings step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._settings = user_input
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="settings",
            data_schema=STEP_SETTINGS_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "name": self._name,
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the confirmation step."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={
                    "name": self._name,
                    "settings": self._settings,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._name,
                "pump_zone_delay": str(self._settings.get("pump_zone_delay", DEFAULT_PUMP_ZONE_DELAY)),
                "sensor_update_interval": str(self._settings.get("sensor_update_interval", DEFAULT_SENSOR_UPDATE_INTERVAL)),
                "default_manual_duration": str(self._settings.get("default_manual_duration", DEFAULT_MANUAL_DURATION)),
                "fail_safe_enabled": "Yes" if self._settings.get("fail_safe_enabled", DEFAULT_FAIL_SAFE_ENABLED) else "No",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> IrrigationAddonOptionsFlow:
        """Create the options flow."""
        return IrrigationAddonOptionsFlow(config_entry)


class IrrigationAddonOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Irrigation Addon."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._settings: dict[str, Any] = {}
        self._selected_room_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_settings()

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle settings options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    "settings": user_input,
                },
            )

        # Get current settings from config entry
        current_settings = self.config_entry.data.get("settings", {})
        
        options_schema = vol.Schema({
            vol.Optional(
                "pump_zone_delay", 
                default=current_settings.get("pump_zone_delay", DEFAULT_PUMP_ZONE_DELAY)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            vol.Optional(
                "sensor_update_interval", 
                default=current_settings.get("sensor_update_interval", DEFAULT_SENSOR_UPDATE_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            vol.Optional(
                "default_manual_duration", 
                default=current_settings.get("default_manual_duration", DEFAULT_MANUAL_DURATION)
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Optional(
                "fail_safe_enabled", 
                default=current_settings.get("fail_safe_enabled", DEFAULT_FAIL_SAFE_ENABLED)
            ): bool,
        })

        return self.async_show_form(
            step_id="settings",
            data_schema=options_schema,
            errors=errors,
        )

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle room management."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_room":
                return await self.async_step_add_room()
            elif action == "edit_room":
                selected_room = user_input.get("selected_room")
                if selected_room:
                    self._selected_room_id = selected_room.split(":")[0]
                    return await self.async_step_edit_room()
            elif action == "delete_room":
                selected_room = user_input.get("selected_room")
                if selected_room:
                    self._selected_room_id = selected_room.split(":")[0]
                    return await self.async_step_delete_room()

        # Get current rooms
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        rooms = coordinator.storage.get_rooms()

        room_options = [f"{room_id}: {room.name}" for room_id, room in rooms.items()]
        
        room_schema = vol.Schema({
            vol.Required("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "add_room", "label": "Add New Room"},
                        {"value": "edit_room", "label": "Edit Existing Room"},
                        {"value": "delete_room", "label": "Delete Room"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        if room_options:
            room_schema = room_schema.extend({
                vol.Optional("selected_room"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=room_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            })

        return self.async_show_form(
            step_id="rooms",
            data_schema=room_schema,
        )

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new room."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate room name is unique
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            existing_rooms = coordinator.storage.get_rooms()
            
            room_name = user_input["room_name"].strip()
            if any(room.name.lower() == room_name.lower() for room in existing_rooms.values()):
                errors["room_name"] = "duplicate_room"
            
            # Validate pump entity
            pump_entity = user_input["pump_entity"]
            if not pump_entity:
                errors["pump_entity"] = "no_pump_entity"
            elif not await _validate_entity_exists(self.hass, pump_entity):
                errors["pump_entity"] = "invalid_pump_entity"
            
            # Validate zone entities
            zone_entities = user_input.get("zone_entities", [])
            for zone_entity in zone_entities:
                if not await _validate_entity_exists(self.hass, zone_entity):
                    errors["zone_entities"] = "invalid_zone_entity"
                    break
            
            # Validate optional entities
            light_entity = user_input.get("light_entity")
            if light_entity and not await _validate_entity_exists(self.hass, light_entity):
                errors["light_entity"] = "invalid_light_entity"
            
            # Validate sensor entities
            sensor_fields = ["soil_rh_sensor", "temperature_sensor", "ec_sensor"]
            for field in sensor_fields:
                sensor_entity = user_input.get(field)
                if sensor_entity and not await _validate_entity_exists(self.hass, sensor_entity):
                    errors[field] = "invalid_sensor_entity"
            
            if not errors:
                # Create the room
                room_data = {
                    "name": room_name,
                    "pump_entity": pump_entity,
                    "zone_entities": zone_entities,
                    "light_entity": light_entity,
                    "sensors": {
                        "soil_rh": user_input.get("soil_rh_sensor"),
                        "temperature": user_input.get("temperature_sensor"),
                        "ec": user_input.get("ec_sensor"),
                    }
                }
                
                # Remove None values from sensors
                room_data["sensors"] = {k: v for k, v in room_data["sensors"].items() if v}
                
                await coordinator.storage.add_room(room_data)
                await coordinator.async_request_refresh()
                
                return self.async_create_entry(title="", data={})

        # Get available entities for selectors
        switch_entities = await _get_entities_by_domain(self.hass, "switch")
        light_entities = await _get_entities_by_domain(self.hass, "light")
        sensor_entities = await _get_entities_by_domain(self.hass, "sensor")

        add_room_schema = vol.Schema({
            vol.Required("room_name"): str,
            vol.Required("pump_entity"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=switch_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("zone_entities", default=[]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=switch_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=True,
                )
            ),
            vol.Optional("light_entity"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=light_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("soil_rh_sensor"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("temperature_sensor"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("ec_sensor"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="add_room",
            data_schema=add_room_schema,
            errors=errors,
        )

    async def async_step_edit_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle editing an existing room."""
        errors: dict[str, str] = {}
        
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        rooms = coordinator.storage.get_rooms()
        
        if self._selected_room_id not in rooms:
            errors["base"] = "room_not_found"
            return await self.async_step_rooms()
        
        current_room = rooms[self._selected_room_id]

        if user_input is not None:
            # Validate room name is unique (excluding current room)
            room_name = user_input["room_name"].strip()
            if any(
                room.name.lower() == room_name.lower() 
                for room_id, room in rooms.items() 
                if room_id != self._selected_room_id
            ):
                errors["room_name"] = "duplicate_room"
            
            # Validate pump entity
            pump_entity = user_input["pump_entity"]
            if not pump_entity:
                errors["pump_entity"] = "no_pump_entity"
            elif not await _validate_entity_exists(self.hass, pump_entity):
                errors["pump_entity"] = "invalid_pump_entity"
            
            # Validate zone entities
            zone_entities = user_input.get("zone_entities", [])
            for zone_entity in zone_entities:
                if not await _validate_entity_exists(self.hass, zone_entity):
                    errors["zone_entities"] = "invalid_zone_entity"
                    break
            
            # Validate optional entities
            light_entity = user_input.get("light_entity")
            if light_entity and not await _validate_entity_exists(self.hass, light_entity):
                errors["light_entity"] = "invalid_light_entity"
            
            # Validate sensor entities
            sensor_fields = ["soil_rh_sensor", "temperature_sensor", "ec_sensor"]
            for field in sensor_fields:
                sensor_entity = user_input.get(field)
                if sensor_entity and not await _validate_entity_exists(self.hass, sensor_entity):
                    errors[field] = "invalid_sensor_entity"
            
            if not errors:
                # Update the room
                room_data = {
                    "name": room_name,
                    "pump_entity": pump_entity,
                    "zone_entities": zone_entities,
                    "light_entity": light_entity,
                    "sensors": {
                        "soil_rh": user_input.get("soil_rh_sensor"),
                        "temperature": user_input.get("temperature_sensor"),
                        "ec": user_input.get("ec_sensor"),
                    }
                }
                
                # Remove None values from sensors
                room_data["sensors"] = {k: v for k, v in room_data["sensors"].items() if v}
                
                await coordinator.storage.update_room(self._selected_room_id, room_data)
                await coordinator.async_request_refresh()
                
                return self.async_create_entry(title="", data={})

        # Get available entities for selectors
        switch_entities = await _get_entities_by_domain(self.hass, "switch")
        light_entities = await _get_entities_by_domain(self.hass, "light")
        sensor_entities = await _get_entities_by_domain(self.hass, "sensor")

        edit_room_schema = vol.Schema({
            vol.Required("room_name", default=current_room.name): str,
            vol.Required("pump_entity", default=current_room.pump_entity): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=switch_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("zone_entities", default=current_room.zone_entities): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=switch_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=True,
                )
            ),
            vol.Optional("light_entity", default=current_room.light_entity): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=light_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("soil_rh_sensor", default=current_room.sensors.get("soil_rh")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("temperature_sensor", default=current_room.sensors.get("temperature")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("ec_sensor", default=current_room.sensors.get("ec")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=sensor_entities,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_room",
            data_schema=edit_room_schema,
            errors=errors,
            description_placeholders={
                "room_name": current_room.name,
            },
        )

    async def async_step_delete_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle deleting a room."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        rooms = coordinator.storage.get_rooms()
        
        if self._selected_room_id not in rooms:
            return await self.async_step_rooms()
        
        current_room = rooms[self._selected_room_id]

        if user_input is not None:
            if user_input.get("confirm_delete"):
                await coordinator.storage.delete_room(self._selected_room_id)
                await coordinator.async_request_refresh()
                return self.async_create_entry(title="", data={})
            else:
                return await self.async_step_rooms()

        delete_room_schema = vol.Schema({
            vol.Required("confirm_delete", default=False): bool,
        })

        return self.async_show_form(
            step_id="delete_room",
            data_schema=delete_room_schema,
            description_placeholders={
                "room_name": current_room.name,
            },
        )


async def _validate_entity_exists(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate that an entity exists in Home Assistant."""
    entity_registry = async_get_entity_registry(hass)
    
    # Check if entity exists in registry
    if entity_registry.async_get(entity_id):
        return True
    
    # Check if entity exists in states
    state = hass.states.get(entity_id)
    return state is not None


async def _get_entities_by_domain(hass: HomeAssistant, domain: str) -> list[str]:
    """Get all entities for a specific domain."""
    entity_registry = async_get_entity_registry(hass)
    entities = []
    
    for entity in entity_registry.entities.values():
        if entity.entity_id.startswith(f"{domain}."):
            entities.append(entity.entity_id)
    
    # Also check current states for entities not in registry
    for entity_id in hass.states.async_entity_ids(domain):
        if entity_id not in entities:
            entities.append(entity_id)
    
    return sorted(entities)