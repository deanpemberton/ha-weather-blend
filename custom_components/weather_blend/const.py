DOMAIN = "weather_blend"
# Generic suffixes; real station IDs are supplied privately in Home Assistant.
METRICS = {
    "temperature": ("°C", "temperature"),
    "relative_humidity": ("%", "humidity"),
    "pressure": ("hPa", "atmospheric_pressure"),
    "wind_speed": ("km/h", "wind_speed"),
    "wind_gust": ("km/h", "wind_speed"),
    "wind_direction_degrees": ("°", None),
    "solar_radiation": ("W/m²", "irradiance"),
    "uv_index": (None, None),
    "precipitation_rate": ("mm/h", "precipitation_intensity"),
    "precipitation_today": ("mm", "precipitation"),
    "dewpoint": ("°C", "temperature"),
    "feels_like": ("°C", "temperature"),
}
SOURCE_METRIC = {"relative_humidity": "humidity", "wind_direction_degrees": "wind_direction_degrees"}
