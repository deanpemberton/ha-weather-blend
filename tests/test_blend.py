from custom_components.weather_blend.blend import robust_blend

def test_outlier():
    result, count = robust_blend([(10,1),(11,1),(100,1)])
    assert 10 <= result <= 11
    assert count == 2

def test_empty():
    assert robust_blend([]) == (None,0)

def test_circular():
    result, count = robust_blend([(350,1),(10,1)], circular=True)
    assert result < 1 or result > 359
    assert count == 2
