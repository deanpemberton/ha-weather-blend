"""Import the pure blending engine without loading Home Assistant modules."""
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
for name in ("custom_components", "custom_components.weather_blend"):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(ROOT / name.replace(".", "/"))]
        sys.modules[name] = module
path = ROOT / "custom_components/weather_blend/blend.py"
spec = importlib.util.spec_from_file_location("custom_components.weather_blend.blend", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
