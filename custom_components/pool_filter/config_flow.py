"""Config flow for the Pool Filter integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_POWER,
    CONF_FILTER_POWER,
    CONF_FILTER_SWITCH,
    CONF_GRID_IMPORT,
    CONF_HOUSE_CONSUMPTION,
    CONF_LOOKBACK_DAYS,
    CONF_MAX_GRID_IMPORT,
    CONF_PV_POWER,
    CONF_SOLAR_MARGIN,
    CONF_TARGET_HOURS,
    CONF_TOP_UP_END,
    CONF_TOP_UP_START,
    DOMAIN,
)


class PoolFilterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pool Filter."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            title = user_input.get(CONF_NAME, "Pool Filter")
            return self.async_create_entry(title=title, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Pool Filter"): str,
                vol.Required(CONF_FILTER_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Required(CONF_PV_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_HOUSE_CONSUMPTION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_GRID_IMPORT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_BATTERY_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_FILTER_POWER, default=1150): vol.Coerce(int),
                vol.Required(CONF_SOLAR_MARGIN, default=300): vol.Coerce(int),
                vol.Required(CONF_MAX_GRID_IMPORT, default=100): vol.Coerce(int),
                vol.Required(CONF_TARGET_HOURS, default=4): vol.Coerce(float),
                vol.Required(CONF_LOOKBACK_DAYS, default=2): vol.Coerce(int),
                vol.Required(CONF_TOP_UP_START, default="14:30"): str,
                vol.Required(CONF_TOP_UP_END, default="16:30"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema)
