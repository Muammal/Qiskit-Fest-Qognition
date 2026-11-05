"""Where and when the St Vincent 2021 scenario happens. Shared by the scenario builder and validation."""
from __future__ import annotations

from datetime import datetime, timezone

from rasterio.warp import transform

from stranded_physics.core.api import TimeAxis, XY

UTM = "EPSG:32620"
TIME = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200., 36)  # 72 hours, spanning the first explosive day.
VENT_LONLAT = (-61.18, 13.33)  # Smithsonian GVP volcano 360150, in disaster_data/catalog/volcanoes.csv. Lies inside the summit crater.
BARBADOS_LONLAT = (-59.55, 13.17)  # Near the island's centre. assumption: from memory, and precise enough for a 170 km ash path.


def to_utm(lonlat: tuple[float, float]) -> XY:
    x, y = transform("EPSG:4326", UTM, [lonlat[0]], [lonlat[1]])
    return float(x[0]), float(y[0])


def to_lonlat(xy: XY) -> tuple[float, float]:
    lon, lat = transform(UTM, "EPSG:4326", [xy[0]], [xy[1]])
    return float(lon[0]), float(lat[0])


VENT_XY = to_utm(VENT_LONLAT)
BARBADOS_XY = to_utm(BARBADOS_LONLAT)
