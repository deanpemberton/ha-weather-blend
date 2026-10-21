"""Catch Home Assistant API incompatibilities before HACS deployment."""
import importlib

def test_integration_modules_import():
    for name in (
        "custom_components.weather_blend.const",
        "custom_components.weather_blend.config_flow",
        "custom_components.weather_blend.sensor",
        "custom_components.weather_blend.reliability",
        "custom_components.weather_blend.blend",
    ):
        assert importlib.import_module(name)

def test_manifest_is_valid_json():
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "custom_components/weather_blend/manifest.json"
    manifest = json.loads(path.read_text())
    assert manifest["domain"] == "weather_blend"
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == []
