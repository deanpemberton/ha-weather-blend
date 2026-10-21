"""Local-only station configuration and editable integration options."""
import math
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN

PREFIX = re.compile(r"^sensor\.[a-z0-9_]+$")


def parse_stations(text):
    """Line syntax: sensor.prefix[,weight[,pressure_offset_hpa]].

    Pressure corrections are optional, manual and zero by default. Never infer
    absolute barometer calibration from disagreement among nearby stations.
    """
    stations = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = [part.strip() for part in raw.split(",")]
        prefix = parts[0].rstrip("_")
        if len(parts) not in (1, 2, 3) or not PREFIX.fullmatch(prefix):
            raise ValueError("invalid_station")
        try:
            weight = float(parts[1]) if len(parts) > 1 else 1.0
        except ValueError as exc:
            raise ValueError("invalid_weight") from exc
        if not math.isfinite(weight) or not 0 < weight <= 100:
            raise ValueError("invalid_weight")
        try:
            offset = float(parts[2]) if len(parts) == 3 else 0.0
        except ValueError as exc:
            raise ValueError("invalid_pressure_offset") from exc
        if not math.isfinite(offset) or abs(offset) > 30:
            raise ValueError("invalid_pressure_offset")
        stations.append({
            "prefix": prefix,
            "weight": weight,
            "pressure_offset_hpa": offset,
        })
    if not 1 <= len(stations) <= 20 or len({s["prefix"] for s in stations}) != len(stations):
        raise ValueError("invalid_station")
    return stations


def format_stations(stations):
    """Round-trip persisted station settings without exposing them outside HA."""
    return "\n".join(
        f'{station["prefix"]},{station["weight"]:g},'
        f'{station.get("pressure_offset_hpa", 0):g}'
        for station in stations
    )


def settings_schema(stations="", max_age_minutes=15):
    return vol.Schema({
        vol.Required("stations", default=stations):
            selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
        vol.Required("max_age_minutes", default=max_age_minutes):
            vol.All(vol.Coerce(int), vol.Range(min=2, max=120)),
    })


def validated_settings(user_input):
    return {
        "stations": parse_stations(user_input["stations"]),
        "max_age_minutes": user_input["max_age_minutes"],
    }


class WeatherBlendFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WeatherBlendOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = validated_settings(user_input)
            except ValueError as exc:
                errors["base"] = str(exc)
            else:
                await self.async_set_unique_id("default")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Weather Blend", data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=settings_schema(
                (user_input or {}).get("stations", ""),
                (user_input or {}).get("max_age_minutes", 15),
            ),
            errors=errors,
        )


class WeatherBlendOptionsFlow(config_entries.OptionsFlow):
    """Options changes reload this entry, never all of Home Assistant."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = validated_settings(user_input)
            except ValueError as exc:
                errors["base"] = str(exc)
            else:
                return self.async_create_entry(title="", data=data)
        current = self._entry.options or self._entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=settings_schema(
                (user_input or {}).get("stations", format_stations(current["stations"])),
                (user_input or {}).get("max_age_minutes", current["max_age_minutes"]),
            ),
            errors=errors,
        )
