from custom_components.weather_blend.blend import Observation, blend
from custom_components.weather_blend.reliability import ReliabilityTracker

def test_two_two_split_preserved():
    obs = [Observation(v, 1, 0, str(i)) for i, v in enumerate((20, 20.2, 30, 30.2))]
    result = blend("temperature", obs)
    assert result.count == 4
    assert result.rejected == 0
    assert result.confidence == "low"
    assert 24 < result.value < 26

def test_three_to_one_consensus():
    obs = [Observation(v, 1, 0, str(i)) for i, v in enumerate((20, 20.2, 20.3, 35))]
    result = blend("temperature", obs)
    assert result.count == 3 and result.rejected == 1

def test_split_does_not_damage_reliability():
    tracker = ReliabilityTracker()
    obs = [Observation(v, 1, 0, str(i)) for i, v in enumerate((20, 20.2, 30, 30.2))]
    tracker.update("temperature", obs)
    assert all(tracker.reliability("temperature", str(i)) == 1 for i in range(4))

def test_single_station_reduced_confidence():
    result = blend("temperature", [Observation(20, 1)])
    assert result.confidence == "reduced"
