from custom_components.weather_blend.blend import Observation
from custom_components.weather_blend.reliability import ReliabilityTracker

def test_reliability_degrades_and_recovers():
    tracker = ReliabilityTracker()
    bad = [Observation(20, 1, 0, "alpha"), Observation(20.2, 1, 0, "bravo"), Observation(40, 1, 0, "charlie")]
    for _ in range(5):
        tracker.update("temperature", bad)
    assert tracker.reliability("temperature", "charlie") < 1
    assert tracker.reliability("temperature", "alpha") == 1
    assert tracker.reliability("temperature", "charlie") >= .25
    good = [Observation(20, 1, 0, "alpha"), Observation(20.2, 1, 0, "bravo"), Observation(20.1, 1, 0, "charlie")]
    tracker.update("temperature", good)
    assert tracker.reliability("temperature", "charlie") > .6

def test_microclimate_not_penalized():
    tracker = ReliabilityTracker()
    values = [Observation(0, 1, 0, "alpha"), Observation(0, 1, 0, "bravo"), Observation(60, 1, 0, "charlie")]
    tracker.update("solar_radiation", values)
    tracker.update("precipitation_rate", values)
    assert tracker.reliability("solar_radiation", "charlie") == 1
    assert tracker.reliability("precipitation_rate", "charlie") == 1

def test_two_station_disagreement_not_penalized():
    tracker = ReliabilityTracker()
    tracker.update("temperature", [Observation(0, 1, 0, "a"), Observation(30, 1, 0, "b")])
    assert tracker.reliability("temperature", "a") == 1
