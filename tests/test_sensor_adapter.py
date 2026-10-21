"""Sensor adapter tests with entirely synthetic weather inputs."""
from datetime import timedelta
from types import SimpleNamespace
from homeassistant.util import dt as dt_util
from custom_components.weather_blend.sensor import WeatherBlendSensor

class Reading:
    def __init__(self, value):
        self.state = str(value)

def make_sensor(values, expired=()):
    stamp = dt_util.as_local(dt_util.utcnow()).replace(tzinfo=None)
    states = {}
    stations = []
    for i, value in enumerate(values):
        prefix = f"sensor.synthetic_{i}"
        stations.append({"prefix": prefix, "weight": 1.0})
        age = timedelta(hours=1) if i in expired else timedelta(seconds=30)
        states[f"{prefix}_local_observation_time"] = Reading((stamp - age).isoformat(sep=" "))
        states[f"{prefix}_temperature"] = Reading(value)
    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    entry = SimpleNamespace(entry_id="example", data={"stations": stations, "max_age_minutes": 15}, options={})
    return WeatherBlendSensor(hass, entry, "temperature")

def test_adapter_majority():
    entity = make_sensor([20, 20.2, 20.3, 35])
    entity._update()
    assert entity._attr_native_value == 20.17
    assert entity._attr_extra_state_attributes["contributing_stations"] == 3

def test_adapter_split_confidence():
    entity = make_sensor([20, 20.2, 30, 30.2])
    entity._update()
    assert entity._attr_extra_state_attributes["confidence"] == "low"

def test_adapter_no_fresh_data():
    entity = make_sensor([15, 16], expired=(0, 1))
    entity._update()
    assert not entity._attr_available

def test_adapter_single_station_fallback():
    entity = make_sensor([10, 12], expired=(1,))
    entity._update()
    assert entity._attr_native_value == 10
    assert entity._attr_extra_state_attributes["confidence"] == "reduced"
