import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN

class WeatherBlendFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id('default')
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title='Weather Blend', data=user_input)
        schema = vol.Schema({
            vol.Required('stations'): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Optional('max_age_minutes', default=15): vol.All(vol.Coerce(int), vol.Range(min=2, max=120)),
        })
        return self.async_show_form(step_id='user', data_schema=schema, description_placeholders={'example': 'sensor.station_a_temperature,sensor.station_b_temperature'})
