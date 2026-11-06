"""Cache public source bytes and their provenance; never execute source content."""

import datetime as dt
import hashlib
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "disaster_data"
RAW = ROOT / "raw"
ISLANDS = {
    "st_vincent": (13.33, -61.18),
    "montserrat": (16.72, -62.18),
    "miyakejima": (34.094, 139.526),
    "stromboli": (38.789, 15.213),
    "la_palma": (28.57, -17.83),
}
SOURCES = []
FAILURES = []


def fetch(url, name):
    path = RAW / name
    if not path.exists():
        time.sleep(1.2)
        req = urllib.request.Request(url, headers={"User-Agent": "StrandedResearch/1.0 (public academic data collection)"})
        with urllib.request.urlopen(req, timeout=180) as response:
            content = response.read()
        path.write_bytes(content)
    return path.read_bytes()


def record(sid, url, name, rows=None):
    p = RAW / name
    SOURCES.append(
        dict(
            id=sid,
            url=url,
            retrieved_at=dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(),
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            file="raw/" + name,
            licence="not confirmed",
            citation="not confirmed",
            rows=rows,
        )
    )


def single(sid, url, name):
    try:
        b = fetch(url, name)
        rows = None
        if name.endswith(".json"):
            j = json.loads(b)
            rows = len(j.get("features", j.get("hourly", {}).get("time", [])))
        record(sid, url, name, rows)
        print(sid, "OK", len(b), flush=True)
    except Exception as e:
        FAILURES.append(dict(id=sid, url=url, error=str(e)))
        print(sid, repr(e), flush=True)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for kind in ("Volcanoes", "Eruptions"):
        url = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?" + urllib.parse.urlencode(
            dict(service="WFS", version="2.0.0", request="GetFeature", typeName="GVP-VOTW:Smithsonian_VOTW_Holocene_" + kind, outputFormat="application/json"),
            safe=":/",
        )
        sid = "gvp_" + kind.lower()
        try:
            name = sid + ".json"
            if not (RAW / name).exists():
                first = json.loads(fetch(url, sid + "_page_0.json"))
                features = first["features"]
                total = int(first["numberMatched"])
                while len(features) < total:
                    start = len(features)
                    page = json.loads(fetch(url + "&count=2000&startIndex=" + str(start), sid + "_page_" + str(start) + ".json"))
                    if not page["features"]:
                        raise ValueError("pagination ended early")
                    features.extend(page["features"])
                first["features"] = features
                first["numberReturned"] = len(features)
                (RAW / name).write_text(json.dumps(first), encoding="utf-8")
            j = json.loads((RAW / name).read_text(encoding="utf-8"))
            record(sid, url, name, len(j["features"]))
            print(sid, len(j["features"]), flush=True)
        except Exception as e:
            FAILURES.append(dict(id=sid, url=url, error=str(e)))
            print(sid, repr(e), flush=True)
    for sid, endpoint in [("noaa_volcano_events", "volcanoes"), ("noaa_tsunamis", "tsunamis/events"), ("noaa_earthquakes", "earthquakes")]:
        url = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/" + endpoint + "?itemsPerPage=200&page="
        try:
            name = sid + ".json"
            if not (RAW / name).exists():
                items = []
                page = 1
                while True:
                    j = json.loads(fetch(url + str(page), sid + "_page_" + str(page) + ".json"))
                    items.extend(j["items"])
                    if len(items) >= int(j["totalItems"]):
                        break
                    if not j["items"]:
                        raise ValueError("pagination ended early")
                    page += 1
                (RAW / name).write_text(json.dumps({"items": items, "totalItems": j["totalItems"]}), encoding="utf-8")
            record(sid, url + "1", name, len(json.loads((RAW / name).read_text())["items"]))
            print(sid, "OK", flush=True)
        except Exception as e:
            FAILURES.append(dict(id=sid, url=url + "1", error=str(e)))
            print(sid, repr(e), flush=True)
    for sid, name in [("natural_earth_land", "ne_10m_land"), ("natural_earth_minor_islands", "ne_10m_minor_islands")]:
        single(sid, "https://naturalearth.s3.amazonaws.com/10m_physical/" + name + ".zip", name + ".zip")
    single(
        "ibtracs",
        "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.since1980.list.v04r01.csv",
        "ibtracs_since1980.csv",
    )
    for island, (lat, lon) in ISLANDS.items():
        q = dict(
            latitude=lat,
            longitude=lon,
            timezone="UTC",
            start_date="2015-01-01",
            end_date="2024-12-31",
            hourly="temperature_2m,precipitation,wind_speed_10m,wind_direction_10m",
        )
        single("weather_" + island, "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(q), "weather_" + island + ".json")
    q = dict(
        latitude=13.33,
        longitude=-61.18,
        timezone="UTC",
        start_date="2021-04-01",
        end_date="2024-12-31",
        hourly="wind_direction_10m,wind_direction_500hPa,wind_speed_500hPa,wind_direction_200hPa,wind_speed_200hPa",
    )
    single("upper_wind_st_vincent", "https://historical-forecast-api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q), "upper_wind_st_vincent.json")
    extras = [
        ("einarsson_2018", "https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2018.00045/full", "einarsson_2018.html"),
        ("brown_fatalities_article", "https://appliedvolc.biomedcentral.com/articles/10.1186/s13617-017-0067-4", "brown_article.html"),
        ("natural_earth_terms", "https://www.naturalearthdata.com/about/terms-of-use/", "natural_earth_terms.html"),
        ("open_meteo_terms", "https://open-meteo.com/en/terms", "open_meteo_terms.html"),
        ("noaa_terms", "https://www.ngdc.noaa.gov/hazard/", "noaa_terms.html"),
        ("gvp_terms", "https://volcano.si.edu/", "gvp_terms.html"),
        ("ibtracs_terms", "https://www.ncei.noaa.gov/products/international-best-track-archive", "ibtracs_terms.html"),
        ("noaa_volcano_legend", "https://www.ngdc.noaa.gov/hazel/view/hazards/volcano/event-data", "noaa_volcano_legend.html"),
    ]
    for vn in (360150, 372010, 360120, 282040, 282060, 383010, 360050, 243040):
        extras.append(("gvp_case_" + str(vn), "https://volcano.si.edu/volcano.cfm?vn=" + str(vn), "gvp_case_" + str(vn) + ".html"))
    for sid, url, name in extras:
        single(sid, url, name)
    (ROOT / "manifest.json").write_text(json.dumps({"sources": SOURCES}, indent=2), encoding="utf-8")
    (ROOT / "access_failures.json").write_text(json.dumps(FAILURES, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
