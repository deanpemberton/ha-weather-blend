"""Weather Blend sensors. Source data stays inside Home Assistant."""
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util
from .blend import Observation, blend, weighted_vapor_pressure, relative_humidity, dewpoint_from_vapor_pressure, feels_like
from .const import METRICS
from .reliability import ReliabilityTracker

async def async_setup_entry(hass, entry, async_add_entities):
    sensors = [WeatherBlendSensor(hass, entry, metric) for metric in METRICS]
    async_add_entities(sensors)

class WeatherBlendSensor(SensorEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry, metric):
        self.hass = hass
        self.entry = entry
        self.metric = metric
        self.settings = {**entry.data, **entry.options}
        self.stations = self.settings["stations"]
        self._attr_name = "Weather Blend " + metric.replace("_", " ").title()
        self._attr_unique_id = f"{entry.entry_id}_{metric}"
        self._attr_native_unit_of_measurement = METRICS[metric][0]
        self._attr_native_value = None
        self._attr_available = False
        self._attr_extra_state_attributes = {}
        self._tracker = ReliabilityTracker()
        self._last_observation_signature = None

    async def async_added_to_hass(self):
        suffixes = set(METRICS) | {"humidity", "local_observation_time"}
        ids = [f'{s["prefix"]}_{suffix}' for s in self.stations for suffix in suffixes]
        self.async_on_remove(async_track_state_change_event(self.hass, ids, self._on_change))
        self.async_on_remove(async_track_time_interval(self.hass, self._on_tick, timedelta(minutes=1)))
        self._update()
        self.async_write_ha_state()

    async def _on_change(self, event):
        self._update()
        self.async_write_ha_state()

    async def _on_tick(self, now):
        self._update()
        self.async_write_ha_state()

    def _age(self, prefix):
        state = self.hass.states.get(f"{prefix}_local_observation_time")
        if state is None:
            return None
        observed = dt_util.parse_datetime(state.state)
        if observed is None:
            return None
        return (dt_util.utcnow() - dt_util.as_utc(observed)).total_seconds()

    def _value(self, prefix, suffix):
        state = self.hass.states.get(f"{prefix}_{suffix}")
        if state is None:
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _observations(self, metric):
        suffix = "relative_humidity" if metric == "relative_humidity" else metric
        output = []
        max_age = self.settings["max_age_minutes"] * 60
        for station in self.stations:
            prefix = station["prefix"]
            age = self._age(prefix)
            value = self._value(prefix, suffix)
            if age is not None and value is not None and -120 <= age <= max_age:
                output.append(Observation(value, station["weight"], age, prefix))
        # Reliability scores are local, metric-specific and bounded.
        # Do not learn repeatedly from the same station reading on refresh ticks.
        sample_signature = tuple((o.source, self.hass.states.get(f"{o.source}_local_observation_time").state) for o in output)
        if metric in ("temperature", "pressure") and sample_signature != self._last_observation_signature:
            self._tracker.update(metric, output)
            self._last_observation_signature = sample_signature
        return [Observation(o.value, o.weight * self._tracker.reliability(metric, o.source), o.age_seconds, o.source) for o in output]

    def _update(self):
        metric = self.metric
        if metric in ("dewpoint", "feels_like", "relative_humidity"):
            paired = []
            ages = {}
            for station in self.stations:
                prefix = station["prefix"]
                age = self._age(prefix)
                temp = self._value(prefix, "temperature")
                rh = self._value(prefix, "relative_humidity")
                if age is not None and -120 <= age <= self.settings["max_age_minutes"] * 60 and temp is not None and rh is not None:
                    paired.append((temp, rh, station["weight"]))
                    ages[prefix] = age
            t = blend("temperature", self._observations("temperature"))
            vapor = weighted_vapor_pressure(paired)
            if t.value is None or vapor is None:
                value, count, confidence = None, 0, "unavailable"
            else:
                humidity = relative_humidity(t.value, vapor)
                if metric == "relative_humidity":
                    value = humidity
                elif metric == "dewpoint":
                    value = dewpoint_from_vapor_pressure(vapor)
                else:
                    wind = blend("wind_speed", self._observations("wind_speed"))
                    value = feels_like(t.value, humidity, wind.value) if wind.value is not None else None
                count = min(t.count, len(paired))
                confidence = t.confidence if count >= 2 else "reduced"
        else:
            result = blend(metric, self._observations(metric), self.settings["max_age_minutes"] * 60)
            value, count, confidence = result.value, result.count, result.confidence
        self._attr_native_value = round(value, 2) if value is not None else None
        self._attr_available = value is not None
        self._attr_extra_state_attributes = {
            "contributing_stations": count,
            "configured_stations": len(self.stations),
            "confidence": confidence,
            "reliability_model": "rolling_peer_agreement",
            "station_health": {s["prefix"]: {
                "reliability": round(self._tracker.health(metric, s["prefix"]).reliability, 3),
                "accepted": self._tracker.health(metric, s["prefix"]).accepted,
                "rejected": self._tracker.health(metric, s["prefix"]).rejected,
                "observation_age_seconds": round(self._age(s["prefix"]), 0) if self._age(s["prefix"]) is not None else None,
            } for s in self.stations},
        }
