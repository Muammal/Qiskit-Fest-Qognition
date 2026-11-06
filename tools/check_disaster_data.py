"""Locked checker for the data task. Run from the folder under test. Re-downloads sources to compare."""

import csv
import hashlib
import html
import json
import math
import random
import re
import secrets
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path("disaster_data")
RESULTS = {}
RNG = random.Random(secrets.randbits(64))
ISLANDS = {
    "st_vincent": (13.33, -61.18),
    "montserrat": (16.72, -62.18),
    "miyakejima": (34.094, 139.526),
    "stromboli": (38.789, 15.213),
    "la_palma": (28.57, -17.83),
}
SOURCE_IDS = [
    "gvp_volcanoes",
    "gvp_eruptions",
    "noaa_volcano_events",
    "noaa_tsunamis",
    "noaa_earthquakes",
    "natural_earth_land",
    "natural_earth_minor_islands",
    "ibtracs",
    "upper_wind_st_vincent",
    *[f"weather_{i}" for i in ISLANDS],
]
REQUIRED_RAW = {
    "gvp_volcanoes.json",
    "gvp_eruptions.json",
    "noaa_volcano_events.json",
    "noaa_tsunamis.json",
    "noaa_earthquakes.json",
    "ne_10m_land.zip",
    "ne_10m_minor_islands.zip",
    "ibtracs_since1980.csv",
    "upper_wind_st_vincent.json",
    *[f"weather_{i}.json" for i in ISLANDS],
}
CATALOGS = [
    "volcanoes",
    "eruptions",
    "noaa_volcano_events",
    "volcanic_tsunamis",
    "earthquakes_near_study_islands",
    "cyclones_near_study_islands",
    "precursor_lead_times",
]
KEYS = {
    "first_unrest",
    "evacuation_order",
    "evacuation_complete",
    "eruption_onset",
    "first_pdc",
    "lahar",
    "ashfall",
    "tsunami",
    "deaths",
    "evacuees",
    "precursor",
}
EVENTS = {"tremor", "gas_plume", "eruption", "ash_fall"}


def check(name, passed, detail=""):
    RESULTS[name] = {"pass": bool(passed), "detail": str(detail)[:500]}


def fetch(url, timeout=120, tries=3):
    last = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (stranded-hackathon-data-check)"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:
            last = error
            time.sleep(2 * (attempt + 1))
    raise last


def table(name):
    with (ROOT / "catalog" / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(text):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text).lower()
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), (" ", " ")):
        text = text.replace(a, b)
    text = re.sub(r"\[\s*\d+\s*\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact(text):
    return re.sub(r"[^a-z0-9]+", "", clean(text))


def check_layout():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in manifest["sources"]}
    missing = [s for s in SOURCE_IDS if s not in sources]
    check("manifest_has_sources", not missing, missing)
    fields = ("url", "retrieved_at", "sha256", "file", "licence", "citation")
    check(
        "manifest_fields",
        all(all(s.get(k) for k in fields) for s in sources.values()),
        [i for i, s in sources.items() if not all(s.get(k) for k in fields)][:5],
    )
    raw = {p.name for p in (ROOT / "raw").iterdir()} if (ROOT / "raw").exists() else set()
    check("raw_files_present", REQUIRED_RAW <= raw, sorted(REQUIRED_RAW - raw))
    bad = []
    for source in sources.values():
        path = Path(source.get("file", ""))
        path = path if path.exists() else ROOT / path
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != source.get("sha256"):
            bad.append(source["id"])
    check("hashes_match_raw", not bad, bad)
    missing = [c for c in CATALOGS if not (ROOT / "catalog" / f"{c}.csv").exists()]
    check("catalogs_present", not missing, missing)
    size = sum(p.stat().st_size for p in ROOT.rglob("*") if p.is_file() and "raw" not in p.relative_to(ROOT).parts)
    check("committed_size", size <= 25_000_000, size)
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"], capture_output=True, text=True).stdout.splitlines()
    other = [l for l in status if l[3:].rstrip("/") not in ("disaster_data", "tools", ".gitignore") and not l[3:].startswith(("disaster_data/", "tools/"))]
    check("stayed_in_lane", not other, other[:6])
    ignored = subprocess.run(["git", "check-ignore", "disaster_data/raw/gvp_eruptions.json"], capture_output=True, text=True).returncode == 0
    check("raw_is_gitignored", ignored)
    check("collector_exists", Path("tools/collect_disaster_data.py").exists() and Path("tools/build_calibration.py").exists())


def check_catalogs_against_live():
    url = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_{}&outputFormat=application/json"
    live = json.loads(fetch(url.format("Eruptions"), timeout=240))["features"]
    rows = table("eruptions")
    check("eruptions_complete", abs(len(rows) - len(live)) <= 25, (len(rows), len(live)))
    by_id = {str(f["properties"]["Eruption_Number"]): f["properties"] for f in live}
    bad = []
    for row in RNG.sample(rows, 200):
        p = by_id.get(str(row["eruption_number"]))
        if p is None:
            continue
        vei = p.get("ExplosivityIndexMax")
        if (row["vei"] == "") != (vei is None) or (vei is not None and float(row["vei"]) != float(vei)):
            bad.append((row["eruption_number"], row["vei"], vei))
        if str(row["start_year"]).split(".")[0] != str(p.get("StartDateYear")).split(".")[0]:
            bad.append((row["eruption_number"], row["start_year"], p.get("StartDateYear")))
    check("eruptions_match_live", not bad, bad[:5])
    zeros = sum(r["vei"] in ("0", "0.0") for r in rows)
    live_zero = sum(f["properties"].get("ExplosivityIndexMax") == 0 for f in live)
    check("missing_vei_not_zero", abs(zeros - live_zero) <= 5, (zeros, live_zero))
    live_v = json.loads(fetch(url.format("Volcanoes"), timeout=240))["features"]
    check("volcanoes_complete", abs(len(table("volcanoes")) - len(live_v)) <= 5, (len(table("volcanoes")), len(live_v)))
    total = json.loads(fetch("https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/volcanoes?itemsPerPage=1&page=1"))["totalItems"]
    check("noaa_complete", abs(len(table("noaa_volcano_events")) - total) <= 5, (len(table("noaa_volcano_events")), total))
    page = json.loads(fetch(f"https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/volcanoes?itemsPerPage=50&page={RNG.randint(1, 4)}"))["items"]
    noaa = {r["id"]: r for r in table("noaa_volcano_events")}
    bad = []
    for item in page:
        row = noaa.get(str(item["id"]))
        if row is None:
            bad.append(("missing", item["id"]))
        elif (row["deaths_total"] or None) and item.get("deathsTotal") is not None and float(row["deaths_total"]) != float(item["deathsTotal"]):
            bad.append((item["id"], row["deaths_total"], item.get("deathsTotal")))
    check("noaa_match_live", not bad, bad[:5])


def check_island_classes():
    rows = table("volcanoes")
    named = {r["name"]: r for r in rows}
    expected = {
        "small_island": [
            "Soufriere St. Vincent",
            "Soufriere Hills",
            "Miyakejima",
            "Izu-Oshima",
            "Stromboli",
            "Vestmannaeyjar",
            "La Palma",
            "Pelee",
            "Krakatau",
        ],
        "large_island": ["Merapi", "Hekla"],
        "continental": ["St. Helens", "Rainier", "Popocatepetl", "Vesuvius"],
    }
    wrong = [(n, named.get(n, {}).get("island_class"), want) for want, names in expected.items() for n in names if named.get(n, {}).get("island_class") != want]
    check("island_classes_known_answers", not wrong, wrong)
    counts = Counter(r["island_class"] for r in rows)
    check("island_class_spread", all(counts[k] >= 50 for k in expected), counts)
    area = {n: named.get(n, {}).get("island_area_km2") for n in ("Soufriere St. Vincent", "Soufriere Hills")}
    ok = all(a not in ("", None) for a in area.values()) and 200 <= float(area["Soufriere St. Vincent"]) <= 500 and 50 <= float(area["Soufriere Hills"]) <= 200
    check("island_area_plausible", ok, area)


def check_cases():
    data = json.loads((ROOT / "case_studies.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    check("six_cases", len(cases) >= 6, len(cases))
    numbers = {str(c.get("volcano_number")) for c in cases}
    check("required_cases", {"360150", "372010", "360120"} <= numbers, numbers)
    pages, verified, unverified, schema = {}, {}, [], []
    for case in cases:
        facts = case["facts"]
        keys = {f["key"] for f in facts}
        if len(facts) < 5 or not {"first_unrest", "eruption_onset"} <= keys or not keys & {"evacuation_order", "evacuation_complete"}:
            schema.append((case["id"], "facts", sorted(keys)))
        if "first_pdc" not in keys and not case.get("no_pdc_reason"):
            schema.append((case["id"], "no pdc reason"))
        if keys - KEYS:
            schema.append((case["id"], sorted(keys - KEYS)))
        if not any(f.get("source_type") == "primary" for f in facts):
            schema.append((case["id"], "no primary"))
        if sum("wikipedia.org" in f["source_url"] for f in facts) > len(facts) / 2:
            schema.append((case["id"], "wikipedia heavy"))
        for fact in facts:
            words = len(fact["quote"].split())
            if not 6 <= words <= 60 or not re.search(r"\d", fact["quote"]):
                schema.append((case["id"], fact["key"], "quote shape", words))
            url = fact["source_url"]
            if url not in pages:
                try:
                    pages[url] = compact(fetch(url).decode("utf-8", "replace"))
                except Exception as error:
                    pages[url] = None
                    unverified.append((url, repr(error)[:60]))
            if pages[url] and compact(fact["quote"]) in pages[url]:
                verified.setdefault(case["id"], []).append(fact["key"])
            else:
                unverified.append((case["id"], fact["key"], url[:70]))
    check("case_schema", not schema, schema[:6])
    total = sum(len(c["facts"]) for c in cases)
    done = sum(len(v) for v in verified.values())
    check("quotes_found_live", total and done / total >= 0.9, (done, total, unverified[:5]))
    thin = [c["id"] for c in cases if len(verified.get(c["id"], [])) < 3]
    check("each_case_verified", not thin, thin)
    required = {"360150": ("eruption_onset", "2021-04-09"), "372010": ("eruption_onset", "1973-01-23"), "360120": ("first_pdc", "1902-05-08")}
    wrong = []
    for number, (key, date) in required.items():
        case = next(
            (c for c in cases if str(c.get("volcano_number")) == number and any(str(f.get("iso_date", "")).startswith(date[:4]) for f in c["facts"])), None
        )
        if not case or not any(f["key"] == key and str(f.get("iso_date", "")).startswith(date) for f in case["facts"]):
            wrong.append((number, key, date))
    check("known_dates", not wrong, wrong)
    rows = table("precursor_lead_times")
    hours = [float(r["lead_hours"]) for r in rows if r["lead_hours"]]
    check(
        "iceland_lead_times",
        len(rows) >= 15 and 0.2 <= min(hours) <= 0.3 and 300 <= max(hours) <= 325,
        (len(rows), min(hours, default=None), max(hours, default=None)),
    )
    return data


def _classify(precip, wind):
    if sum(precip) >= 10 or max(wind) >= 50:
        return "storm"
    return "calm" if sum(precip) < 0.5 else "rain"


def _markov(hourly):
    start = next(i for i, t in enumerate(hourly["time"]) if int(t[11:13]) % 2 == 0)
    states = [
        _classify(hourly["precipitation"][i : i + 2], hourly["wind_speed_10m"][i : i + 2])
        for i in range(start, len(hourly["time"]) - 1, 2)
        if None not in hourly["precipitation"][i : i + 2] and None not in hourly["wind_speed_10m"][i : i + 2]
    ]
    pairs = Counter(zip(states, states[1:]))
    return {
        a: {b: pairs[(a, b)] / max(sum(pairs[(a, c)] for c in ("calm", "rain", "storm")), 1) for b in ("calm", "rain", "storm")}
        for a in ("calm", "rain", "storm")
    }


def check_calibration():
    cal = json.loads((ROOT / "calibration.json").read_text(encoding="utf-8"))
    required = [
        "vei_distribution_small_island",
        "hazard_agents_small_island",
        "lead_time_hours_iceland",
        "upper_wind_st_vincent",
        "case_lead_times",
        "volcanic_tsunami_count",
        "small_island_eruption_count",
    ]
    for island in ISLANDS:
        required += [f"weather_markov_{island}", f"temperature_{island}", f"cyclone_rate_per_year_{island}"]
    missing = [k for k in required if k not in cal]
    check("calibration_entries", not missing, missing)
    thin = [
        k
        for k, v in cal.items()
        if not all(f in v for f in ("value", "n", "method", "source_ids", "region", "caveat")) or not v["caveat"] or not v["source_ids"]
    ]
    check("calibration_provenance", not thin, thin[:5])
    volcanoes = {r["volcano_number"]: r for r in table("volcanoes")}
    counts = Counter()
    for row in table("eruptions"):
        if row["activity_type"] == "Confirmed Eruption" and row["vei"] != "" and volcanoes.get(row["volcano_number"], {}).get("island_class") == "small_island":
            counts[str(int(float(row["vei"])))] += 1
    total = sum(counts.values())
    entry = cal["vei_distribution_small_island"]
    diff = max((abs(entry["value"].get(k, entry["value"].get(k + ".0", 0)) - counts[k] / total) for k in counts), default=1)
    check("vei_recomputed", diff < 0.005 and entry["n"] == total and abs(sum(entry["value"].values()) - 1) < 0.01, (round(diff, 4), entry["n"], total))
    bad = []
    for island in ISLANDS:
        hourly = json.loads((ROOT / "raw" / f"weather_{island}.json").read_text(encoding="utf-8"))["hourly"]
        ours = cal[f"weather_markov_{island}"]["value"]
        theirs = _markov(hourly)
        for a in theirs:
            for b in theirs[a]:
                if abs(ours[a][b] - theirs[a][b]) > 0.03:
                    bad.append((island, a, b, ours[a][b], round(theirs[a][b], 3)))
    check("markov_recomputed", not bad, bad[:5])
    temps = cal["temperature_st_vincent"]["value"]
    check(
        "temperature_plausible",
        15 <= min(v for v in temps.values() if isinstance(v, (int, float))) and max(v for v in temps.values() if isinstance(v, (int, float))) <= 40,
        temps,
    )
    rate = cal["cyclone_rate_per_year_st_vincent"]["value"]
    check("cyclone_rate_plausible", isinstance(rate, (int, float)) and 0.1 <= rate <= 3, rate)
    check("lead_times_labelled_iceland", "iceland" in str(cal["lead_time_hours_iceland"]["region"]).lower())
    check("wind_caveat", "surface" in cal["upper_wind_st_vincent"]["caveat"].lower())
    before = (ROOT / "calibration.json").read_bytes()
    done = subprocess.run([sys.executable, "tools/build_calibration.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    check("rebuild_runs", done.returncode == 0, done.stderr[-300:])
    check("rebuild_deterministic", (ROOT / "calibration.json").read_bytes() == before)


def _circular_mean(values):
    x = sum(math.sin(math.radians(v)) for v in values)
    y = sum(math.cos(math.radians(v)) for v in values)
    return math.degrees(math.atan2(x, y)) % 360


def check_live_weather():
    island = RNG.choice(list(ISLANDS))
    hourly = json.loads((ROOT / "raw" / f"weather_{island}.json").read_text(encoding="utf-8"))["hourly"]
    check(
        "weather_covers_ten_years",
        len(hourly["time"]) >= 87000 and hourly["time"][0].startswith("2015-01-01") and hourly["time"][-1].startswith("2024-12-31"),
        len(hourly["time"]),
    )
    year, month, day = RNG.randint(2015, 2024), RNG.randint(1, 12), RNG.randint(1, 28)
    date = f"{year}-{month:02d}-{day:02d}"
    lat, lon = ISLANDS[island]
    live = json.loads(
        fetch(
            f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={date}&end_date={date}&timezone=UTC&hourly=temperature_2m,precipitation"
        )
    )["hourly"]
    index = {t: i for i, t in enumerate(hourly["time"])}
    bad = [t for k, t in enumerate(live["time"]) if abs((hourly["temperature_2m"][index[t]] or 0) - (live["temperature_2m"][k] or 0)) > 1.5]
    check("weather_matches_live", len(bad) <= 2, (island, date, bad[:4]))


def check_scenarios():
    path = ROOT / "scenarios" / "st_vincent_2021.json"
    scenario = json.loads(path.read_text(encoding="utf-8"))
    files = list((ROOT / "scenarios").glob("*.json"))
    check("two_scenarios", len(files) >= 2, [p.name for p in files])
    onset = (12 + 41 / 60 + 24) // 2
    check("st_vincent_start", scenario["start_utc"].startswith("2021-04-08T00:00"), scenario["start_utc"])
    check("st_vincent_onset_step", scenario["onset_step"] == onset, (scenario["onset_step"], onset))
    check("st_vincent_upper_wind", scenario["wind_source"] == "500hPa")
    live = json.loads(
        fetch(
            "https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=13.33&longitude=-61.18&start_date=2021-04-08&end_date=2021-04-10&timezone=UTC&hourly=wind_direction_500hPa,wind_direction_10m"
        )
    )["hourly"]
    mismatch = sum(abs(((scenario["wind_deg"][k] - (live["wind_direction_500hPa"][2 * k] + 180)) + 180) % 360 - 180) > 15 for k in range(36))
    check("st_vincent_wind_matches_live", mismatch <= 3, mismatch)
    after = list(range(int(onset), min(int(onset) + 12, 36)))
    upper = _circular_mean([scenario["wind_deg"][k] for k in after])
    surface = _circular_mean([(live["wind_direction_10m"][2 * k] + 180) % 360 for k in after])
    # Ash from this eruption reached Barbados, to the east. Surface trade winds run the other way.
    check("ash_goes_east_on_upper_wind", 30 <= upper <= 150, round(upper))
    check("surface_wind_is_opposite", 200 <= surface <= 320, round(surface))
    cases = json.loads((ROOT / "case_studies.json").read_text(encoding="utf-8"))["cases"]
    case_urls = {c["id"]: {f["source_url"] for f in c["facts"]} for c in cases}
    case_keys = {c["id"]: {f["key"] for f in c["facts"]} for c in cases}
    problems = []
    for p in files:
        s = json.loads(p.read_text(encoding="utf-8"))
        if any(len(s[k]) != 36 for k in ("weather", "wind_deg", "temperature_c")) or s.get("step_hours") != 2:
            problems.append((p.name, "lengths"))
        if not set(s["weather"]) <= {"calm", "rain", "storm"} or s["wind_source"] not in ("500hPa", "200hPa", "10m"):
            problems.append((p.name, "values"))
        if s["case_id"] not in case_urls:
            problems.append((p.name, "case id"))
            continue
        for sign in s["signs"]:
            if sign["event"] not in EVENTS or sign["source_url"] not in case_urls[s["case_id"]] or sign["fact_key"] not in case_keys[s["case_id"]]:
                problems.append((p.name, sign))
    check("scenarios_valid", not problems, problems[:5])


def check_report():
    path = ROOT / "REPORT.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lowered = text.lower()
    missing = [s for s in ("em-dat", "iceland", "surface", "reanalysis", "bias", "model versus data", "could not", "licence") if s not in lowered]
    check("report_sections", not missing, missing)
    banned = [s for s in ("proves the model", "validates the model", "forecasts", "guarantee") if s in lowered]
    check("report_no_overclaim", not banned, banned)
    check(
        "report_compares_engine",
        all(s in text for s in ("2/3", "PDC_DELAYS")) and "cold" in lowered,
        "needs eruption probability, PDC_DELAYS and cold mechanics",
    )


def main():
    steps = [check_layout, check_catalogs_against_live, check_island_classes, check_cases, check_calibration, check_live_weather, check_scenarios, check_report]
    for step in steps:
        try:
            step()
        except Exception as error:
            check(step.__name__, False, repr(error))
    failed = {k: v["detail"] for k, v in RESULTS.items() if not v["pass"]}
    print(json.dumps({"passed": not failed, "checks": len(RESULTS), "failed": failed}, indent=1))
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
