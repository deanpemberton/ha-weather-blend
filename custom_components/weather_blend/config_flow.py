"""Private station configuration through the HA UI only."""
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN

PREFIX = re.compile(r"^sensor\.[a-z0-9_]+$")

def parse_stations(text):
    """Line syntax: sensor.prefix,weight. Weights optional, defaults equal."""
    stations = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = [s.strip().rstrip("_") for s in raw.split(",")]
        if len(parts) not in (1, 2) or not PREFIX.fullmatch(parts[0]):
            raise ValueError("invalid_station")
        try:
            weight = float(parts[1]) if len(parts) == 2 else 1.0
        except ValueError as exc:
            raise ValueError("invalid_weight") from exc
        if not 0 < weight <= 100:
            raise ValueError("invalid_weight")
        stations.append({"prefix": parts[0], "weight": weight})
    if not 1 <= len(stations) <= 20 or len({s["prefix"] for s in stations}) != len(stations):
        raise ValueError("invalid_station")
    return stations

class WeatherBlendFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                stations = parse_stations(user_input["stations"])
            except ValueError as exc:
                errors["base"] = str(exc)
            else:
                await self.async_set_unique_id("default")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Weather Blend",
                    data={"stations": stations, "max_age_minutes": user_input["max_age_minutes"]},
                )
        schema = vol.Schema({
            vol.Required("stations", default=(user_input or {}).get("stations", "")):
                selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Required("max_age_minutes", default=(user_input or {}).get("max_age_minutes", 15)):
                vol.All(vol.Coerce(int), vol.Range(min=2, max=120)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
