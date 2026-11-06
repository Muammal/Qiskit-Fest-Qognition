"""Deterministically derive catalogs and calibration from cached source data only."""

import csv
import datetime as dt
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "disaster_data"
RAW = ROOT / "raw"
CAT = ROOT / "catalog"
ISLANDS = {
    "st_vincent": (13.33, -61.18),
    "montserrat": (16.72, -62.18),
    "miyakejima": (34.094, 139.526),
    "stromboli": (38.789, 15.213),
    "la_palma": (28.57, -17.83),
}
CAL = {}
AGENT_LEGEND = (
    "NOAA HazEL on-site legend, read from its front-end bundle: A Avalanche (Debris and landslides); E Electrical (lightning); F Floods (& Jokulhlaups); "
    "G Gas (emission from eruptive craters as well as fumarolic/solfataric activity); I Indirect deaths (disease, starvation, exposure, desolation); L Lava flows; M Mudflows/Lahars; "
    "m Secondary (post-eruption) mudflows; P Pyroclastic flows, surges, & direct blasts; S Seismic, or volcanic earthquake (tectonic earthquake deaths excluded); "
    "T Tephra (ash, bombs, lapilli, steam blasts). Killing either by ballistic impact, or with finer-grained ash, by suffocation, collapse of ash-covered roofs, etc.; W Waves or tsunami."
)
# Which facts become scenario signs: (fact key, iso_date, event). Explicit so each sign traces to one fact.
SCENARIO_SIGNS = {
    "st_vincent_2021": [
        ("precursor", "2021-04-08", "tremor"),
        ("precursor", "2021-04-08", "gas_plume"),
        ("eruption_onset", "2021-04-09T12:41Z", "eruption"),
        ("ashfall", "2021-04-10", "ash_fall"),
    ],
    "la_palma_2021": [("eruption_onset", "2021-09-19T14:13Z", "eruption")],
}


def load(name, default=None):
    p = RAW / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def write(name, fields, rows):
    with (CAT / (name + ".csv")).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def entry(key, value, n, method, sources, region="Global", caveat="Catalogue reporting and selection bias; this is descriptive, not predictive."):
    CAL[key] = dict(value=value, n=int(n), method=method, source_ids=sources, region=region, caveat=caveat)


def distance(lat, lon, a, b):
    lat, lon, a, b = map(np.radians, (lat, lon, a, b))
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(np.sin((a - lat) / 2) ** 2 + np.cos(lat) * np.cos(a) * np.sin((b - lon) / 2) ** 2, 0, 1)))


def contains(points, x, y):
    x1, y1 = points[:, 0], points[:, 1]
    x2, y2 = np.roll(x1, 1), np.roll(y1, 1)
    cross = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-300) + x1)
    return bool(np.count_nonzero(cross) % 2)


def polygons(name, minor=False):
    p = RAW / name
    if not p.exists():
        return []
    with zipfile.ZipFile(p) as z:
        b = z.read(next(n for n in z.namelist() if n.endswith(".shp")))
    rings = []
    offset = 100
    while offset < len(b):
        size = struct.unpack_from(">i", b, offset + 4)[0] * 2
        body = offset + 8
        typ = struct.unpack_from("<i", b, body)[0]
        if typ in (5, 15, 25):
            parts, n = struct.unpack_from("<2i", b, body + 36)
            starts = list(struct.unpack_from("<" + str(parts) + "i", b, body + 44)) + [n]
            points = np.frombuffer(b, dtype="<f8", count=n * 2, offset=body + 44 + parts * 4).reshape(-1, 2)
            for i in range(parts):
                xy = points[starts[i] : starts[i + 1]].copy()
                if len(xy) < 3:
                    continue
                signed = np.sum(xy[:-1, 0] * xy[1:, 1] - xy[1:, 0] * xy[:-1, 1]) / 2
                if signed > 0:
                    continue  # Shapefile holes are counterclockwise.
                lon = np.unwrap(np.radians(xy[:, 0]))
                lat = np.radians(xy[:, 1])
                area = abs(np.sum(np.diff(lon) * (np.sin(lat[1:]) + np.sin(lat[:-1]))) * 6371.0088**2 / 2)
                rings.append(dict(xy=xy, area=area, minor=minor, box=(xy[:, 0].min(), xy[:, 1].min(), xy[:, 0].max(), xy[:, 1].max())))
        offset = body + size
    return rings


def classify(rings, lat, lon, australia):
    hits = [r for r in rings if r["box"][0] <= lon <= r["box"][2] and r["box"][1] <= lat <= r["box"][3] and contains(r["xy"], lon, lat)]
    chosen = min(hits, key=lambda r: r["area"]) if hits else None
    if chosen is None:
        nearby = []
        for r in rings:
            x0, y0, x1, y1 = r["box"]
            if y0 - 0.3 <= lat <= y1 + 0.3 and x0 - 0.6 <= lon <= x1 + 0.6:
                xy = r["xy"]
                scale = np.array([111.195 * math.cos(math.radians(lat)), 111.195])
                v = (xy - np.array([lon, lat])) * scale
                a = v[:-1]
                d = v[1:] - a
                t = np.clip(-np.sum(a * d, axis=1) / (np.sum(d * d, axis=1) + 1e-300), 0, 1)
                near = float(np.sqrt(np.sum((a + t[:, None] * d) ** 2, axis=1)).min())
                if near <= 5 or (near < 30 and (r["area"] < 2000 or r["minor"])):
                    nearby.append((near, r))
        if nearby:
            chosen = min(nearby, key=lambda pair: pair[0])[1]
    if chosen is None:
        return "small_island", None
    area = chosen["area"]
    if lat < -60:
        return "continental", area
    if area < 2000 or chosen["minor"]:
        return "small_island", area
    return ("large_island" if area < australia else "continental"), area


def catalogs():
    rings = polygons("ne_10m_land.zip") + polygons("ne_10m_minor_islands.zip", True)
    aus = [r["area"] for r in rings if contains(r["xy"], 133, -25)]
    australia = min(aus) if aus else math.inf
    volcanoes = []
    mappings = {
        "volcano_number": "Volcano_Number",
        "name": "Volcano_Name",
        "country": "Country",
        "subregion": "Subregion",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "elevation_m": "Elevation",
        "primary_type": "Primary_Volcano_Type",
        "last_eruption_year": "Last_Eruption_Year",
    }
    for f in load("gvp_volcanoes.json", {"features": []})["features"]:
        p = f["properties"]
        r = {k: p.get(v) for k, v in mappings.items()}
        r["island_class"], r["island_area_km2"] = classify(rings, float(r["latitude"]), float(r["longitude"]), australia) if rings else (None, None)
        volcanoes.append(r)
    write("volcanoes", list(mappings) + ["island_class", "island_area_km2"], volcanoes)
    em = {
        "volcano_number": "Volcano_Number",
        "volcano_name": "Volcano_Name",
        "eruption_number": "Eruption_Number",
        "activity_type": "Activity_Type",
        "vei": "ExplosivityIndexMax",
        "start_year": "StartDateYear",
        "start_month": "StartDateMonth",
        "start_day": "StartDateDay",
        "end_year": "EndDateYear",
        "end_month": "EndDateMonth",
        "end_day": "EndDateDay",
    }
    eruptions = [{k: f["properties"].get(v) for k, v in em.items()} for f in load("gvp_eruptions.json", {"features": []})["features"]]
    write("eruptions", list(em), eruptions)
    nm = {
        "id": "id",
        "year": "year",
        "month": "month",
        "day": "day",
        "name": "name",
        "country": "country",
        "latitude": "latitude",
        "longitude": "longitude",
        "agent": "agent",
        "deaths_total": "deathsTotal",
        "tsunami_event_id": "tsunamiEventId",
        "earthquake_event_id": "earthquakeEventId",
    }
    noaa = [{k: p.get(v) for k, v in nm.items()} for p in load("noaa_volcano_events.json", {"items": []})["items"]]
    write("noaa_volcano_events", list(nm), noaa)
    ts = [p for p in load("noaa_tsunamis.json", {"items": []})["items"] if p.get("causeCode") in (6, "6")]
    fields = sorted(set().union(*(p.keys() for p in ts))) if ts else ["id", "year", "month", "day", "causeCode"]
    write("volcanic_tsunamis", fields, ts)
    eq = []
    for p in load("noaa_earthquakes.json", {"items": []})["items"]:
        if p.get("latitude") is None or p.get("longitude") is None:
            continue
        for island, (lat, lon) in ISLANDS.items():
            km = float(distance(lat, lon, p["latitude"], p["longitude"]))
            if km <= 200:
                eq.append(dict(p, island=island, distance_km=km))
    fields = sorted(set().union(*(p.keys() for p in eq))) if eq else ["id", "island", "distance_km"]
    write("earthquakes_near_study_islands", fields, eq)
    small = {str(r["volcano_number"]) for r in volcanoes if r["island_class"] == "small_island"}
    counts = Counter(
        str(int(r["vei"])) for r in eruptions if str(r["volcano_number"]) in small and r["activity_type"] == "Confirmed Eruption" and r["vei"] is not None
    )
    n = sum(counts.values())
    entry(
        "vei_distribution_small_island",
        {k: v / n for k, v in sorted(counts.items())},
        n,
        "Confirmed Eruption rows with non-null VEI; Natural Earth spherical landmass classification.",
        ["gvp_volcanoes", "gvp_eruptions", "natural_earth_land", "natural_earth_minor_islands"],
    )
    agents = Counter()
    matched = 0
    for p in noaa:
        if not p["deaths_total"] or p["deaths_total"] <= 0 or p["latitude"] is None or p["longitude"] is None:
            continue
        near = [(float(distance(p["latitude"], p["longitude"], v["latitude"], v["longitude"])), v) for v in volcanoes]
        if not near:
            continue
        km, v = min(near, key=lambda pair: pair[0])
        if km <= 30 and str(v["volcano_number"]) in small:
            matched += 1
            if p["agent"] is not None:
                agents[str(p["agent"])] += 1
    entry(
        "hazard_agents_small_island",
        dict(sorted(agents.items())),
        matched,
        "Fatal NOAA events; nearest GVP volcano within 30 km, classified small island; literal agent strings counted without splitting compound codes. Case is meaningful: M is mudflows/lahars and m is secondary (post-eruption) mudflows, so keys are not merged. "
        + AGENT_LEGEND,
        ["noaa_volcano_events", "gvp_volcanoes", "noaa_hazel_legend"],
        caveat='Spatial match is an assumption; unmatched events and events with no agent are excluded. NOAA lists significant events only, so this is a reporting-biased count of fatal events, not of deaths and not a probability per eruption. Compound strings such as "T,m" name several agents without splitting deaths between them.',
    )
    entry(
        "volcanic_tsunami_count",
        len(ts),
        len(ts),
        "NOAA causeCode 6, which the HazEL legend defines as Volcano; catalogue event rows, not runups. Codes 4 (Volcano and Earthquake), 5 (Volcano, Earthquake, and Landslide) and 7 (Volcano and Landslide) are mixed causes and are excluded.",
        ["noaa_tsunamis", "noaa_hazel_legend"],
    )
    nsmall = sum(str(r["volcano_number"]) in small and r["activity_type"] == "Confirmed Eruption" for r in eruptions)
    entry(
        "small_island_eruption_count",
        nsmall,
        nsmall,
        "Confirmed Eruption rows on classified small-island volcanoes, including missing VEI.",
        ["gvp_eruptions", "gvp_volcanoes"],
    )
    return volcanoes


def xlsx_rows(path):
    """First sheet of a workbook as a list of {column letter: text}. Reads XML only."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = ["".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns)]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).find("m:sheetData", ns)
    rows = []
    for row in sheet.findall("m:row", ns):
        cells = {}
        for c in row.findall("m:c", ns):
            v = c.find("m:v", ns)
            if v is not None:
                cells[re.match("[A-Z]+", c.get("r")).group(0)] = shared[int(v.text)] if c.get("t") == "s" else v.text
        rows.append(cells)
    return rows


def brown_hazards(volcanoes):
    """Brown et al. 2017 incidents at small-island volcanoes, by the database's own fatal cause."""
    path = RAW / "brown_fatalities.xlsx"
    if not path.exists():
        return
    small = {str(r["volcano_number"]) for r in volcanoes if r["island_class"] == "small_island"}
    incidents = Counter()
    fatalities = Counter()
    matched = 0
    for row in xlsx_rows(path)[1:]:
        if row.get("A") not in small:
            continue
        matched += 1
        cause = row["Z"].strip()
        incidents[cause] += 1
        fatalities[cause] += int(round(float(row["Y"])))
    value = {c: {"incidents": incidents[c], "fatalities": fatalities[c]} for c in sorted(incidents)}
    entry(
        "hazard_fatalities_brown_small_island",
        value,
        matched,
        "Brown et al. 2017 supplementary database. Rows joined on GVP volcano number to our small_island class; the fatal cause strings are the database's own and are not merged; fatalities sum its Number of fatalities column.",
        ["brown_fatalities", "gvp_volcanoes", "natural_earth_land", "natural_earth_minor_islands"],
        "Small islands, global",
        "Our island class is not the database's own island flag (radius of about 5 km or less). Causes include non-eruptive and indirect deaths. Numbers are as listed in the database, some from uncertain historic reports; a few very large events dominate the fatality totals. This describes reported deaths, not the chance of dying.",
    )


def cyclones():
    path = RAW / "ibtracs_since1980.csv"
    results = []
    last = None
    if path.exists():
        use = ["SID", "SEASON", "NAME", "LAT", "LON", "USA_WIND", "WMO_WIND", "ISO_TIME"]
        df = pd.read_csv(path, skiprows=[1], usecols=use, low_memory=False)
        for c in ["SEASON", "LAT", "LON", "USA_WIND", "WMO_WIND"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        maxdate = pd.to_datetime(df.ISO_TIME.str.strip(), errors="coerce").max()
        # The final year in the track archive may be incomplete.
        last = int(maxdate.year) - 1
        for island, (lat, lon) in ISLANDS.items():
            km = distance(lat, lon, df.LAT.to_numpy(), df.LON.to_numpy())
            near = df.loc[km <= 200].copy()
            near["closest_km"] = km[km <= 200]
            for sid, g in near.groupby("SID", sort=True):
                whole = df.loc[df.SID == sid]
                winds = whole.USA_WIND.combine_first(whole.WMO_WIND)
                results.append(
                    dict(
                        island=island,
                        sid=sid,
                        season=int(g.SEASON.iloc[0]),
                        name=str(g.NAME.iloc[0]).strip(),
                        max_wind_kt=None if winds.isna().all() else float(winds.max()),
                        closest_km=float(g.closest_km.min()),
                    )
                )
    write("cyclones_near_study_islands", ["island", "sid", "season", "name", "max_wind_kt", "closest_km"], results)
    for island in ISLANDS:
        n = sum(r["island"] == island and 1980 <= r["season"] <= last for r in results) if last else 0
        entry(
            "cyclone_rate_per_year_" + island,
            n / (last - 1980 + 1) if last else None,
            n,
            f"Unique SID within 200 km; seasons 1980 through {last}; denominator includes zero-storm years. Max wind is lifetime USA_WIND with per-point WMO_WIND fallback, in knots.",
            ["ibtracs"],
            island,
            "The final archive year is excluded as potentially incomplete; storm-centre distance is not an impact footprint. Reporting and wind-agency biases remain.",
        )


def bins(h):
    states = []
    indices = []
    for i, t in enumerate(h["time"][:-1]):
        if int(t[11:13]) % 2:
            continue
        if dt.datetime.fromisoformat(h["time"][i + 1]) - dt.datetime.fromisoformat(t) != dt.timedelta(hours=1):
            continue
        p = h["precipitation"][i : i + 2]
        w = h["wind_speed_10m"][i : i + 2]
        if any(v is None for v in p + w):
            states.append(None)
            indices.append(i)
            continue
        states.append("storm" if sum(p) >= 10 or max(w) >= 50 else "calm" if sum(p) < 0.5 else "rain")
        indices.append(i)
    return states, indices


def weather():
    for island, (lat, lon) in ISLANDS.items():
        j = load("weather_" + island + ".json")
        if not j:
            continue
        h = j["hourly"]
        states, indices = bins(h)
        counts = {a: Counter() for a in ("calm", "rain", "storm")}
        for k, (a, b) in enumerate(zip(states, states[1:])):
            if a and b and indices[k + 1] - indices[k] == 2:
                counts[a][b] += 1
        probs = {a: {b: counts[a][b] / sum(counts[a].values()) if sum(counts[a].values()) else None for b in counts} for a in counts}
        entry(
            "weather_markov_" + island,
            probs,
            sum(sum(c.values()) for c in counts.values()),
            "Consecutive non-overlapping 2-hour bins at even UTC hours: storm if precipitation sum >=10 mm or peak wind >=50 km/h; else calm if sum <0.5 mm; else rain; missing bins excluded.",
            ["weather_" + island],
            island,
            f"Thresholds are assumptions. Coarse reanalysis grid cell, not a station, with cell elevation {j['elevation']} m; it smooths extremes, so storm bins may be undercounted, while high cells may overstate wind. Transitions are descriptive and seasonally pooled.",
        )
        t = np.array([np.nan if v is None else v for v in h["temperature_2m"]])
        local = [(dt.datetime.fromisoformat(s) + dt.timedelta(hours=lon / 15)).hour for s in h["time"]]
        night = t[np.array([hr >= 20 or hr <= 6 for hr in local])]
        q = np.nanpercentile(t, [5, 50, 95])
        value = dict(p5=float(q[0]), p50=float(q[1]), p95=float(q[2]), night_p5=float(np.nanpercentile(night, 5)))
        entry(
            "temperature_" + island,
            value,
            np.isfinite(t).sum(),
            "Hourly Celsius percentiles using numpy linear interpolation; night local mean solar time UTC + longitude/15 hours, local hours 20..6 inclusive.",
            ["weather_" + island],
            island,
            f"Coarse reanalysis grid cell, not a station, with cell elevation {j['elevation']} m, so it can read colder than the coast. Local mean solar time is an explicit convention; exposure and individual physiology are unresolved.",
        )
    j = load("upper_wind_st_vincent.json")
    value = {}
    n = 0
    if j:
        h = j["hourly"]
        n = len(h["time"])
        for level in ["10m", "500hPa", "200hPa"]:
            a = np.array([np.nan if v is None else (v + 180) % 360 for v in h["wind_direction_" + level]])
            rad = np.radians(a)
            mean = float(np.degrees(np.arctan2(np.nanmean(np.sin(rad)), np.nanmean(np.cos(rad)))) % 360)
            b = a[::2]
            change = np.abs((np.diff(b) + 180) % 360 - 180)
            value[level] = dict(toward_circular_mean_deg=mean, median_abs_change_per_2h_deg=float(np.nanmedian(change)))
    entry(
        "upper_wind_st_vincent",
        value,
        n,
        "Meteorological direction +180 modulo 360; circular mean of all hourly bearings; median shortest angular difference between even-UTC 2-hour samples.",
        ["upper_wind_st_vincent"],
        "St Vincent",
        "Surface wind can blow the opposite way from ash transport, and 500 hPa and 200 hPa can differ in speed and bearing. Upper winds here start in April 2021, so this is under four years, not a long climatology. No imputation.",
    )


def headline(case, key):
    """First listed fact for a key: case_studies.json lists the most precise, then primary, first."""
    return next((f for f in case["facts"] if f["key"] == key), None)


def parse_date(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def gap_hours(a, b):
    """Hours between two facts and the precision, or (None, reason). Month-only dates give no number."""
    if a is None or b is None:
        return None, "missing fact"
    fa, fb = a.get("iso_date"), b.get("iso_date")
    if not fa or not fb:
        return None, "no calendar date in source"
    if len(fa) < 10 or len(fb) < 10:
        return None, "month or year precision only"
    if "T" in fa and "T" in fb and fa.endswith("Z") == fb.endswith("Z"):
        return (parse_date(fb) - parse_date(fa)).total_seconds() / 3600, "minute"
    return (dt.date.fromisoformat(fb[:10]) - dt.date.fromisoformat(fa[:10])).days * 24.0, "day"


def leads():
    p = ROOT / "case_studies.json"
    cases = json.loads(p.read_text(encoding="utf-8"))["cases"] if p.exists() else []
    lp = ROOT / "precursor_rows.json"
    rows = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else []
    write("precursor_lead_times", ["eruption", "year", "lead_hours", "source_url", "quote_or_row"], rows)
    hours = [r["lead_hours"] for r in rows if r["lead_hours"] is not None]
    entry(
        "lead_time_hours_iceland",
        hours,
        len(hours),
        f"Parsed from Einarsson 2018 Table 1 by tools/extract_einarsson.py, Iceland only. {len(rows)} table rows, {len(hours)} with a single stated time. Values the table marks as imprecise (~) or with an assumed eruption start ( ) are kept; the row text shows the mark. One range and one empty cell have no value.",
        ["einarsson_2018"],
        "Iceland",
        "Iceland only. Not a transferable distribution for tropical island eruptions. It measures seismic precursor time to the start of the eruption, and many Icelandic eruptions are basaltic rift events unlike a dome-forming arc volcano.",
    )
    values = {}
    for c in cases:
        unrest, onset, pdc = headline(c, "first_unrest"), headline(c, "eruption_onset"), headline(c, "first_pdc")
        h1, p1 = gap_hours(unrest, onset)
        h2, p2 = gap_hours(onset, pdc)
        values[c["id"]] = {"unrest_to_onset_hours": h1, "unrest_to_onset_precision": p1, "onset_to_first_pdc_hours": h2, "onset_to_first_pdc_precision": p2}
    entry(
        "case_lead_times",
        values,
        len(cases),
        "Subtract the headline (first listed) facts in case_studies.json. Both with a time and the same time basis: minute precision. Otherwise whole-day differences of the calendar dates: day precision, value is days x 24. Month-only, year-only or undated facts give null.",
        ["case_studies"],
        "Selected island events",
        "Day-precision values can be wrong by up to about a day, and a value of 0 is possible. Nulls mean the source lacks precision, not that the gap is unknown in the literature. Selected cases, not a random sample. Onset may mean effusive, phreatic or explosive onset, as stated in each fact; St Vincent uses the explosive onset.",
    )
    return cases


def scenarios(cases):
    specs = [("st_vincent_2021", "st_vincent", "2021-04-08T00:00Z", "500hPa"), ("la_palma_2021", "la_palma", "2021-09-18T00:00Z", "10m")]
    for cid, island, start, level in specs:
        case = next((c for c in cases if c["id"] == cid), None)
        if case is None:
            continue
        j = load("weather_" + island + ".json")
        u = load("upper_wind_st_vincent.json") if level == "500hPa" else j
        if not j or not u:
            continue
        h = j["hourly"]
        wh = u["hourly"]
        index = {t: i for i, t in enumerate(h["time"])}
        wi = {t: i for i, t in enumerate(wh["time"])}
        begin = parse_date(start)
        states, bi = bins(h)
        state_by = {h["time"][i]: s for s, i in zip(states, bi)}
        notes = (
            "Historical-forecast 500 hPa wind and ERA5-based surface weather from a coarse grid cell, not a station. Explosive onset used; the earlier effusive onset is a separate fact. Signs with a date only sit at 00:00 UTC of that day, so tremor and gas can be up to a day early against the source, and ash_fall is the Barbados date. first_pdc_step is null because the sourced first-flow fact gives a date, 10 April, with no time; the same source says it came after more than 24 h of explosive activity."
            if level == "500hPa"
            else "Reanalysis weather and 10 m wind from a coarse grid cell, not a station. Surface wind is a fallback and does not represent upper-air ash transport. No pyroclastic density current is reported in the sources read, so first_pdc_step is null. The earthquake swarm of 11 September starts before this window, and the ash fact has a date only, so neither is a sign."
        )
        out = dict(
            id=cid,
            case_id=cid,
            start_utc=start,
            step_hours=2,
            weather=[],
            wind_deg=[],
            wind_source=level,
            temperature_c=[],
            onset_step=None,
            first_pdc_step=None,
            signs=[],
            notes=notes,
        )
        for k in range(36):
            t = (begin + dt.timedelta(hours=2 * k)).strftime("%Y-%m-%dT%H:%M")
            v = wh["wind_direction_" + level][wi[t]]
            if v is None or state_by.get(t) is None:
                raise ValueError(f"{cid}: missing weather or wind at {t}")
            out["weather"].append(state_by[t])
            out["wind_deg"].append((v + 180) % 360)
            out["temperature_c"].append(h["temperature_2m"][index[t]])

        def step_of(date):
            return math.floor((parse_date(date).replace(tzinfo=dt.timezone.utc) - begin).total_seconds() / 7200)

        out["onset_step"] = step_of(headline(case, "eruption_onset")["iso_date"])
        pdc = headline(case, "first_pdc")
        if pdc and "T" in (pdc.get("iso_date") or ""):
            out["first_pdc_step"] = step_of(pdc["iso_date"])
        for key, date, event in SCENARIO_SIGNS[cid]:
            fact = next(f for f in case["facts"] if f["key"] == key and f["iso_date"] == date)
            out["signs"].append(dict(step=step_of(date), event=event, fact_key=key, source_url=fact["source_url"]))
        dump(ROOT / "scenarios" / (cid + ".json"), out)


def main():
    CAT.mkdir(parents=True, exist_ok=True)
    (ROOT / "scenarios").mkdir(exist_ok=True)
    brown_hazards(catalogs())
    cyclones()
    weather()
    cases = leads()
    scenarios(cases)
    dump(ROOT / "calibration.json", CAL)
    print("Built", len(CAL), "calibration entries from cached inputs only.")


if __name__ == "__main__":
    main()
