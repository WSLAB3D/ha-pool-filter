"""Config flow for the Pool Filter integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_PERCENTAGE,
    CONF_BATTERY_POWER,
    CONF_COUNTDOWN_ENTITY,
    CONF_FILTER_POWER,
    CONF_FILTER_SWITCH,
    CONF_GRID_IMPORT,
    CONF_HOUSE_CONSUMPTION,
    CONF_LOOKBACK_DAYS,
    CONF_MAX_GRID_IMPORT,
    CONF_MIN_BATTERY_PERCENTAGE,
    CONF_NOTIFY_SERVICE,
    CONF_PV_POWER,
    CONF_SOLAR_MARGIN,
    CONF_TARGET_HOURS,
    CONF_TOP_UP_END,
    CONF_TOP_UP_START,
    DOMAIN,
)


def _build_schema(defaults: dict | None = None) -> vol.Schema:
    """Build the config/options schema with optional defaults."""
    if defaults is None:
        defaults = {}

    return vol.Schema(
        {
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, "Pool Filter")): str,
            vol.Required(
                CONF_FILTER_SWITCH, default=defaults.get(CONF_FILTER_SWITCH, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Required(
                CONF_PV_POWER, default=defaults.get(CONF_PV_POWER, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_HOUSE_CONSUMPTION, default=defaults.get(CONF_HOUSE_CONSUMPTION, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_GRID_IMPORT, default=defaults.get(CONF_GRID_IMPORT, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_BATTERY_POWER, default=defaults.get(CONF_BATTERY_POWER, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_BATTERY_PERCENTAGE, default=defaults.get(CONF_BATTERY_PERCENTAGE, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_COUNTDOWN_ENTITY, default=defaults.get(CONF_COUNTDOWN_ENTITY, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")
            ),
            vol.Optional(
                CONF_NOTIFY_SERVICE, default=defaults.get(CONF_NOTIFY_SERVICE, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_MIN_BATTERY_PERCENTAGE,
                default=defaults.get(CONF_MIN_BATTERY_PERCENTAGE, 20),
            ): vol.Coerce(int),
            vol.Required(
                CONF_FILTER_POWER, default=defaults.get(CONF_FILTER_POWER, 1150)
            ): vol.Coerce(int),
            vol.Required(
                CONF_SOLAR_MARGIN, default=defaults.get(CONF_SOLAR_MARGIN, 300)
            ): vol.Coerce(int),
            vol.Required(
                CONF_MAX_GRID_IMPORT, default=defaults.get(CONF_MAX_GRID_IMPORT, 100)
            ): vol.Coerce(int),
            vol.Required(
                CONF_TARGET_HOURS, default=defaults.get(CONF_TARGET_HOURS, 4)
            ): vol.Coerce(float),
            vol.Required(
                CONF_LOOKBACK_DAYS, default=defaults.get(CONF_LOOKBACK_DAYS, 2)
            ): vol.Coerce(int),
            vol.Required(
                CONF_TOP_UP_START, default=defaults.get(CONF_TOP_UP_START, "14:30")
            ): str,
            vol.Required(
                CONF_TOP_UP_END, default=defaults.get(CONF_TOP_UP_END, "16:30")
            ): str,
        }
    )


class PoolFilterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pool Filter."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PoolFilterOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            title = user_input.get(CONF_NAME, "Pool Filter")
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_build_schema())


class PoolFilterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Pool Filter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            new_data = dict(self.entry.data)
            new_data.update(user_input)
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init", data_schema=_build_schema(self.entry.data)
        )
