"""Pure-Python, offline, deterministic weather fusion engine.

No Home Assistant imports, networking, location discovery or telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, exp, hypot, isfinite, log, radians, sin
from statistics import median

RANGES = {
    "temperature": (-60, 65), "humidity": (0, 100),
    "pressure": (850, 1100), "dewpoint": (-80, 65),
    "wind_speed": (0, 250), "wind_gust": (0, 350),
    "wind_direction_degrees": (0, 360),
    "solar_radiation": (0, 1500), "uv_index": (0, 16),
    "precipitation_rate": (0, 300), "precipitation_today": (0, 1500),
}
# Minimum tolerances prevent falsely rejecting genuine local weather differences.
TOLERANCE = {
    "temperature": 3.0, "humidity": 12.0, "pressure": 5.0,
    "dewpoint": 3.0, "wind_speed": 30.0, "wind_gust": 45.0,
    "solar_radiation": 200.0, "uv_index": 3.0,
    "precipitation_rate": 20.0, "precipitation_today": 25.0,
}
DEFAULT_WEIGHTS = (0.40, 0.30, 0.18, 0.12)


@dataclass(frozen=True)
class Observation:
    value: float
    weight: float = 1.0
    age_seconds: float = 0.0
    source: str = ""


@dataclass(frozen=True)
class Result:
    value: float | None
    count: int
    rejected: int
    confidence: str
    dispersion: float | None = None


def _median_abs_deviation(values: list[float]) -> float:
    center = median(values)
    return median([abs(v - center) for v in values])


def blend(metric: str, observations: list[Observation], max_age: float = 900) -> Result:
    """Validate, reject isolated spikes and aggregate remaining measurements.

    Only reject statistical outliers with at least three independent stations.
    Two disagreeing stations are retained with reduced confidence.
    Localised rain, wind and solar variations receive wider tolerances.
    """
    if metric not in RANGES:
        raise ValueError("Unknown weather metric")
    low, high = RANGES[metric]
    valid = [
        o for o in observations
        if isfinite(o.value) and isfinite(o.weight) and o.weight > 0
        and isfinite(o.age_seconds) and -120 <= o.age_seconds <= max_age
        and low <= o.value <= high
    ]
    rejected = len(observations) - len(valid)
    if not valid:
        return Result(None, 0, rejected, "unavailable")
    if metric == "wind_direction_degrees":
        x = sum(o.weight * cos(radians(o.value)) for o in valid)
        y = sum(o.weight * sin(radians(o.value)) for o in valid)
        strength = hypot(x, y) / sum(o.weight for o in valid)
        if strength < 0.15:
            return Result(None, len(valid), rejected, "unavailable")
        angle = (degrees(atan2(y, x)) + 360) % 360
        return Result(angle, len(valid), rejected, "high" if len(valid) >= 3 and strength > .7 else "reduced", 1-strength)

    # Rain events are spatially patchy. Do not reject an isolated wet station.
    if len(valid) >= 3 and metric not in ("precipitation_rate", "precipitation_today", "wind_speed", "wind_gust", "solar_radiation"):
        values = [o.value for o in valid]
        mid = median(values)
        mad = _median_abs_deviation(values)
        tolerance = max(TOLERANCE.get(metric, 1), 3.5 * 1.4826 * mad)
        kept = [o for o in valid if abs(o.value - mid) <= tolerance]
        # Require a strict majority. A 2-2 split has no authoritative winner.
        if len(kept) > len(valid) / 2:
            rejected += len(valid) - len(kept)
            valid = kept

    total = sum(o.weight for o in valid)
    value = sum(o.value * o.weight for o in valid) / total
    spread = max(o.value for o in valid) - min(o.value for o in valid)
    tolerance = TOLERANCE.get(metric, 1)
    confidence = ("high" if len(valid) >= 3 and spread <= tolerance * 2
                  else "reduced")
    if metric in ("precipitation_rate", "precipitation_today") and any(o.value > 0 for o in valid) and any(o.value == 0 for o in valid):
        confidence = "reduced"
    return Result(value, len(valid), rejected, confidence, spread)


def saturation_vapor_pressure(temp_c: float) -> float:
    """Magnus approximation in hPa."""
    return 6.112 * exp(17.62 * temp_c / (243.12 + temp_c))


def dewpoint_from_vapor_pressure(vapor_hpa: float) -> float | None:
    if vapor_hpa <= 0 or not isfinite(vapor_hpa):
        return None
    ratio = log(vapor_hpa / 6.112)
    return 243.12 * ratio / (17.62 - ratio)


def relative_humidity(temp_c: float, vapor_hpa: float) -> float:
    return min(100.0, max(0.0, 100.0 * vapor_hpa / saturation_vapor_pressure(temp_c)))


def weighted_vapor_pressure(readings: list[tuple[float, float, float]]) -> float | None:
    """Blend (temperature C, RH %, weight) as vapor pressure."""
    clean = [(saturation_vapor_pressure(t) * h / 100, w) for t, h, w in readings
             if -60 <= t <= 65 and 0 <= h <= 100 and w > 0]
    if not clean:
        return None
    return sum(v*w for v, w in clean) / sum(w for _, w in clean)


def feels_like(temp_c: float, rh: float, wind_kmh: float) -> float:
    """Steadman-style apparent temperature; wind speed is converted to m/s."""
    e = rh / 100 * saturation_vapor_pressure(temp_c)
    return temp_c + 0.33 * e - 0.70 * (wind_kmh / 3.6) - 4.0


def robust_blend(readings, circular=False):
    """Compatibility helper for early tests."""
    metric = "wind_direction_degrees" if circular else "temperature"
    result = blend(metric, [Observation(v, w) for v, w in readings])
    return result.value, result.count
