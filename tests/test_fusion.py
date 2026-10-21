"""Synthetic data only. No real station identifiers or private locations."""
from custom_components.weather_blend.blend import (
    Observation, blend, dewpoint_from_vapor_pressure, feels_like,
    relative_humidity, saturation_vapor_pressure, weighted_vapor_pressure,
)

def o(*values):
    return [Observation(v, 1.0, 30, "synthetic") for v in values]

def test_stale_station_removed():
    result = blend("temperature", [Observation(20, 1, 30), Observation(60, 1, 2000)])
    assert result.value == 20 and result.count == 1

def test_outlier_rejected():
    result = blend("temperature", o(20, 20.5, 60))
    assert 20 <= result.value <= 20.5 and result.rejected == 1

def test_two_station_disagreement_reduced():
    assert blend("temperature", o(10, 30)).confidence == "reduced"

def test_missing():
    assert blend("temperature", []).value is None

def test_invalid_zero_wind_allowed():
    assert blend("wind_speed", o(0, 0)).value == 0

def test_direction_wraparound():
    result = blend("wind_direction_degrees", o(350, 10))
    assert result.value < 1 or result.value > 359

def test_opposing_wind_unavailable():
    assert blend("wind_direction_degrees", o(90, 270)).value is None

def test_localised_rain_retained():
    result = blend("precipitation_rate", o(0, 0, 12))
    assert result.count == 3 and result.value > 0 and result.confidence == "reduced"

def test_vapor_pressure_consistency():
    vapor = weighted_vapor_pressure([(20, 50, 1), (20, 50, 1)])
    assert abs(relative_humidity(20, vapor) - 50) < 0.1
    assert dewpoint_from_vapor_pressure(vapor) < 20

def test_feels_like_finite():
    assert -50 < feels_like(20, 50, 10) < 50

def test_weighted():
    r = blend("temperature", [Observation(10, 3), Observation(20, 1)])
    assert abs(r.value - 12.5) < 1e-9
