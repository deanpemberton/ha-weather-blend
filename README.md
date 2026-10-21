# Weather Blend for Home Assistant

Privacy-first, local weather blending from existing Home Assistant sensor entities. No telemetry, network calls, analytics, location discovery or credential collection.

## Development status
**Pre-release.** This integration must run in parallel before any control automation or dashboard is migrated. The fusion engine provides freshness filtering, metric-specific physical bounds, robust outlier filtering, circular wind direction, vapor-pressure humidity/dewpoint, apparent temperature, and source-count confidence.

## Installation
Install via HACS as a custom integration or copy `custom_components/weather_blend` to Home Assistant. A **user-approved** restart is required to load a newly installed custom integration. Add **Weather Blend** under Settings → Devices & Services.

Enter existing sensor prefixes, one per line, optionally with a weight after a comma:

```text
sensor.example_alpha,0.40
sensor.example_bravo,0.30
sensor.example_charlie,0.18
sensor.example_delta,0.12
```

Each station should provide `<prefix>_temperature`, `<prefix>_relative_humidity`, `<prefix>_pressure`, `<prefix>_wind_speed`, `<prefix>_wind_gust`, `<prefix>_wind_direction_degrees`, `<prefix>_solar_radiation`, `<prefix>_uv_index`, `<prefix>_precipitation_rate`, `<prefix>_precipitation_today`, and `<prefix>_local_observation_time`. Missing metrics are tolerated.

The station prefix list, identifiers and observations stay in the private Home Assistant configuration and must not be included in public issues or diagnostics.

## Limitations
Pressure observations must be in comparable units and reference level; the integration does **not** apply elevation correction automatically. Rainfall is spatially variable; blended precipitation is a regional estimate, not proof of rain at a particular address. Daily precipitation totals may reset at different times across stations. Confidence currently reflects contributing-station count and spread, not learned historical reliability. Station weights are configurable but not yet automatically learned.

## Privacy
Never commit real Home Assistant configuration, station identifiers, coordinates, API tokens, logs or weather-history exports. All test data is synthetic.
