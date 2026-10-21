"""Blended weather entities based on existing Home Assistant station sensors."""
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util
from .const import METRICS
from .blend import robust_blend

async def async_setup_entry(hass, entry, async_add_entities):
    prefixes = [s.strip().lower().rstrip('_') for s in entry.data['stations'].splitlines() if s.strip()]
    if not prefixes or len(set(prefixes)) != len(prefixes) or any(not s.startswith('sensor.') or ' ' in s for s in prefixes):
        raise ValueError('Stations must be unique sensor entity prefixes, one per line')
    entities = [BlendedSensor(hass, entry, prefixes, metric) for metric in METRICS]
    async_add_entities(entities)

class BlendedSensor(SensorEntity):
    _attr_has_entity_name = False
    _attr_should_poll = False
    def __init__(self, hass, entry, prefixes, metric):
        self.hass = hass
        self.entry = entry
        self.prefixes = prefixes
        self.metric = metric
        self._attr_name = f'Weather Blend {metric.replace("_", " ").title()}'
        self._attr_unique_id = f'{entry.entry_id}_{metric}'
        self._attr_native_unit_of_measurement = METRICS[metric][0]
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_extra_state_attributes = {'contributing_stations': 0}
        self._attr_native_value = None

    async def async_added_to_hass(self):
        ids = [f'{p}_{self.metric}' for p in self.prefixes]
        ids += [f'{p}_local_observation_time' for p in self.prefixes]
        self.async_on_remove(async_track_state_change_event(self.hass, ids, self._changed))
        self.async_on_remove(async_track_time_interval(self.hass, self._tick, timedelta(minutes=1)))
        self._update()

    async def _changed(self, event):
        self._update()
        self.async_write_ha_state()

    async def _tick(self, now):
        self._update()
        self.async_write_ha_state()

    def _update(self):
        lo, hi = METRICS[self.metric][1:]
        now = dt_util.utcnow()
        max_age = self.entry.data.get('max_age_minutes', 15)
        values = []
        for prefix in self.prefixes:
            s = self.hass.states.get(f'{prefix}_{self.metric}')
            t = self.hass.states.get(f'{prefix}_local_observation_time')
            if not s or s.state in ('unknown', 'unavailable', 'none') or not t:
                continue
            try:
                value = float(s.state)
                observed = dt_util.parse_datetime(t.state)
                if observed is None:
                    continue
                age = (now - dt_util.as_utc(observed)).total_seconds()
                if not (-120 <= age <= max_age * 60) or not lo <= value <= hi:
                    continue
                values.append((value, 1.0))
            except (ValueError, TypeError, OverflowError):
                continue
        result, count = robust_blend(values, self.metric == 'wind_direction')
        self._attr_native_value = round(result, 2) if result is not None else None
        self._attr_available = result is not None
        self._attr_extra_state_attributes = {'contributing_stations': count, 'configured_stations': len(self.prefixes), 'confidence': 'high' if count >= 3 else 'reduced' if count else 'unavailable'}
