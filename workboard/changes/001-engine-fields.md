# 001: Add fields for the first real engine path

**Type:** additive, so existing categories keep working.
**Why:** 500 hPa alone is not enough for ash, so wind needs more than one height. Drainage needs to reach flow models, and ash needs column height.

Added to `core/fields.py`:

- `terrain.flow_accumulation`, `terrain.height_above_drainage`
- `atmos.wind_speed_500hpa`, `atmos.wind_bearing_500hpa`, `atmos.wind_speed_200hpa`, `atmos.wind_bearing_200hpa`
- `eruption.column_height`

`atmos.wind_speed` and `atmos.wind_bearing` are now documented as the 10 m wind.

**Status:** made before the T-001 review, so it needs the owner's sign-off with the rest of the interfaces.
