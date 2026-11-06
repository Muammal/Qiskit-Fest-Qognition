"""Merge the older partial manifests into manifest.json, add cited sources, fill provider terms.

Licence and citation text comes only from pages read in raw/. Anything unread stays
'not confirmed'. Hashes are always recomputed from the file on disk.
"""

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "disaster_data"
RAW = ROOT / "raw"
PARTS = ("additional_manifest.json", "evidence_manifest.json", "supplemental_manifest.json")
NOT_CONFIRMED = "not confirmed"
BOT_CHALLENGE_BYTES = 3100
GVP_URL = (
    "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0"
    "&request=GetFeature&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_{}"
    "&outputFormat=application/json"
)

NOAA_VOLCANO = (
    "NCEI/WDS Global Significant Volcanic Eruptions Database. Citation requested on the "
    'provider page: "Please cite this data/database as doi:10.7289/V5JW8BSH".'
)
NOAA_TSUNAMI = (
    'NCEI/WDS Global Historical Tsunami Database. Citation requested on the provider page: "Please cite this data/database as: doi:10.7289/V5PN93H7".'
)
IBTRACS = (
    "Knapp, K. R., M. C. Kruk, D. H. Levinson, H. J. Diamond, and C. J. Neumann, 2010, BAMS "
    "91, 363-376, doi:10.1175/2009BAMS2755.1; and Gahtan, J., et al., 2024, IBTrACS Project, "
    "Version 4r01, NOAA NCEI, doi:10.25921/82ty-9e16, as requested on the provider page."
)
OPEN_METEO = "Open-Meteo.com API, Historical Weather or Historical Forecast endpoint."
CC_BY_OPEN_METEO = "CC-BY 4.0, stated in the Open-Meteo terms read in raw/open_meteo_terms.html"
CC_BY_ARTICLE = "CC BY, stated on the article page"
NATURAL_EARTH = "Public domain, stated in the Natural Earth terms read in raw/natural_earth_terms.html"

# (source id) -> (url, raw file, licence, citation). Only for sources not in an older manifest.
ADDED = {
    "gvp_volcanoes": (GVP_URL.format("Volcanoes"), "raw/gvp_volcanoes.json", NOT_CONFIRMED, NOT_CONFIRMED),
    "gvp_eruptions": (GVP_URL.format("Eruptions"), "raw/gvp_eruptions.json", NOT_CONFIRMED, NOT_CONFIRMED),
    "einarsson_2018": (
        "https://www.frontiersin.org/articles/10.3389/feart.2018.00045",
        "raw/einarsson_2018.html",
        CC_BY_ARTICLE,
        "Einarsson, P., 2018, Short-Term Seismic Precursors to Icelandic Eruptions 1973-2014, Frontiers in Earth Science 6:45, doi:10.3389/feart.2018.00045",
    ),
    "st_vincent_plumes": (
        "https://acp.copernicus.org/articles/23/15209/2023/acp-23-15209-2023.html",
        "raw/st_vincent_plumes.html",
        "Creative Commons Attribution 4.0, stated on the article page",
        "Taylor, I. A., et al., 2023, A satellite chronology of plumes from the April 2021 eruption of La Soufriere, St Vincent, Atmos. Chem. Phys. 23, 15209, doi:10.5194/acp-23-15209-2023",
    ),
    "st_vincent_wiki": (
        "https://en.wikipedia.org/wiki/2021_eruption_of_La_Soufri%C3%A8re",
        "raw/st_vincent_wiki.html",
        NOT_CONFIRMED,
        "Wikipedia, 2021 eruption of La Soufriere",
    ),
    "st_vincent_cole_uea": (
        "https://ueaeprints.uea.ac.uk/id/eprint/91119",
        "raw/st_vincent_cole_uea.html",
        "Accepted version: Creative Commons Attribution, stated on the repository page",
        "Cole, P. D., et al., 2024, Explosive sequence of La Soufriere St Vincent April 2021, Geological Society Special Publications 539, 81-106, doi:10.1144/SP539-2022-292",
    ),
    "st_vincent_cole_accepted": (
        "https://ueaeprints.uea.ac.uk/id/eprint/91119/1/SP539_2022_292.pdf",
        "raw/st_vincent_cole_accepted.pdf",
        "Accepted version: Creative Commons Attribution, stated on the repository page",
        "Accepted manuscript of Cole et al. 2024. Only pages 2 and 5-12 were read, to confirm the abstract symbol.",
    ),
    "pelee_sdsu": (
        "https://volcanoes.sdsu.edu/Pelee.html",
        "raw/pelee_sdsu.html",
        NOT_CONFIRMED,
        "How Volcanoes Work, San Diego State University, Mt. Pelee eruption (1902)",
    ),
    "pelee_sciam": (
        "https://blogs.scientificamerican.com/history-of-geology/may-8-1902-la-pelee/",
        "raw/pelee_sciam.html",
        NOT_CONFIRMED,
        "Scientific American blog, History of Geology, May 8, 1902: La Pelee",
    ),
    "pelee_ebsco": (
        "https://www.ebsco.com/research-starters/history/mount-pelee-erupts",
        "raw/pelee_ebsco.html",
        NOT_CONFIRMED,
        "EBSCO Research Starters, Mount Pelee Erupts",
    ),
    "miyakejima_eri_73": (
        "https://www.eri.u-tokyo.ac.jp/KOHO/Yoran2001ep/07_3.html",
        "raw/miyakejima_eri_73.html",
        NOT_CONFIRMED,
        "Earthquake Research Institute, University of Tokyo, Yoran 2001, section 7-3",
    ),
    "miyakejima_nied": (
        "https://nied-repo.bosai.go.jp/records/4152",
        "raw/miyakejima_nied.html",
        NOT_CONFIRMED,
        "Nakada, S., et al., 2005, Chronology and products of the 2000 eruption of Miyakejima Volcano, Japan, Bull. Volcanol. 67, 205-218, doi:10.1007/s00445-004-0404-4 (abstract in the NIED repository)",
    ),
    "miyakejima_osu": (
        "https://volcano.oregonstate.edu/miyake-jima",
        "raw/miyakejima_osu.html",
        NOT_CONFIRMED,
        "Volcano World, Oregon State University, Miyake-jima",
    ),
    "la_palma_eos": (
        "https://eos.org/science-updates/volcanic-anatomy-mapped-as-it-erupts",
        "raw/la_palma_eos.html",
        "Text CC BY-NC-ND 3.0, stated on the article page",
        "Zanon, V., and L. D'Auria, 2024, Volcanic anatomy, mapped as it erupts, Eos 105, doi:10.1029/2024EO240431",
    ),
    "brown_fatalities": (
        "https://static-content.springer.com/esm/art%3A10.1186%2Fs13617-017-0067-4/MediaObjects/13617_2017_67_MOESM1_ESM.xlsx",
        "raw/brown_fatalities.xlsx",
        NOT_CONFIRMED,
        "Brown et al. 2017, Volcanic fatalities database, DOI 10.1186/s13617-017-0067-4, supplementary material 1. The article page returned a bot challenge, so its licence text could not be read.",
    ),
    "noaa_hazel_legend": (
        "https://www.ngdc.noaa.gov/hazel/static/js/main.4768c122.js",
        "raw/noaa_hazel_bundle_0.js",
        NOT_CONFIRMED,
        "NCEI HazEL front-end bundle, holding the on-site agent and tsunami-cause legends. Read as text, never executed.",
    ),
}

# Pages cached while searching and not cited: blocked, empty or not used for any fact.
DROP = {"st_vincent_paper", "la_palma_paper", "pelee_paper", "noaa_volcano_fields", "heimaey_usgs_of97"}

TERMS = {
    "natural_earth_land": (NATURAL_EARTH, "Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com. ne_10m_land"),
    "natural_earth_minor_islands": (NATURAL_EARTH, "Made with Natural Earth. ne_10m_minor_islands"),
    "natural_earth_terms": (NATURAL_EARTH, "Natural Earth terms of use page"),
    "ibtracs": (NOT_CONFIRMED, IBTRACS),
    "ibtracs_terms": (NOT_CONFIRMED, IBTRACS),
    "noaa_volcano_events": (NOT_CONFIRMED, NOAA_VOLCANO),
    "noaa_volcano_docs": (NOT_CONFIRMED, NOAA_VOLCANO),
    "noaa_volcano_legend": (NOT_CONFIRMED, NOAA_VOLCANO),
    "noaa_tsunamis": (NOT_CONFIRMED, NOAA_TSUNAMI),
    "noaa_tsunami_docs": (NOT_CONFIRMED, NOAA_TSUNAMI),
    "noaa_earthquakes": (NOT_CONFIRMED, "NCEI/WDS Global Significant Earthquake Database, via the HazEL API. Exact citation text not read."),
    "noaa_terms": (NOT_CONFIRMED, "NCEI Natural Hazards page"),
    "open_meteo_terms": (CC_BY_OPEN_METEO, OPEN_METEO),
    "upper_wind_st_vincent": (CC_BY_OPEN_METEO, OPEN_METEO),
    "la_palma_frontiers": (
        "Creative Commons Attribution License (CC BY), stated on the article page",
        "Bonadonna, C., et al., 2023, Frontiers in Earth Science 11:1166073, doi:10.3389/feart.2023.1166073",
    ),
    "heimaey_usgs": (NOT_CONFIRMED, "Williams, R. S., Jr., and J. G. Moore, Man Against Volcano: The Eruption on Heimaey, USGS General Interest Publication"),
    "pelee_usgs": (NOT_CONFIRMED, "Hawaiian Volcano Observatory, USGS, Volcano Watch: Chronology of a volcanic disaster, March 11, 2004"),
    "miyakejima_usgs": (
        NOT_CONFIRMED,
        "Wright, T., and Sakai, S., 2004, Bulletin of the Earthquake Research Institute, v. 79, p. 1-16 (USGS Publications Warehouse record)",
    ),
    "miyakejima_tokyo": (NOT_CONFIRMED, "Earthquake Research Institute, University of Tokyo, Yoran 2001, section 5-2"),
    "montserrat_chronology": (
        NOT_CONFIRMED,
        "Montserrat Volcano Observatory, Chronology of the Eruption of Soufriere Hills Volcano, on the Michigan Tech mirror",
    ),
    "montserrat_mvo": (NOT_CONFIRMED, "Montserrat Volcano Observatory, Scientific Report 18, 03 April 1996, on the Michigan Tech mirror"),
    "heimaey_museum": (NOT_CONFIRMED, "Safnahus Vestmannaeyja, Heimaey: the eruption 1973"),
    "st_vincent_ipgp": (NOT_CONFIRMED, "Institut de Physique du Globe de Paris, Retour sur l'eruption de la Soufriere de Saint-Vincent, 29/04/2021"),
    "brown_fatalities_article": (NOT_CONFIRMED, "Bot-challenge page only. Article not read. DOI 10.1186/s13617-017-0067-4"),
}


ACCESS_FAILURES = [
    {
        "id": "gvp_html_pages",
        "url": "https://volcano.si.edu/volcano.cfm?vn=360150",
        "error": "HTTP 403 to scripts, so not cited. Same for the home page and the other volcano pages tried; GVP licence text could not be read.",
    },
    {"id": "st_vincent_paper", "url": "https://www.nature.com/articles/s41467-022-31901-4", "error": "Bot challenge page, not cited."},
    {"id": "la_palma_paper", "url": "https://www.nature.com/articles/s41598-022-23998-w", "error": "Bot challenge page, not cited."},
    {
        "id": "brown_article",
        "url": "https://appliedvolc.biomedcentral.com/articles/10.1186/s13617-017-0067-4",
        "error": "Bot challenge page, not cited. The supplementary xlsx itself was reachable on static-content.springer.com.",
    },
    {
        "id": "noaa_volcano_fields",
        "url": "https://www.ngdc.noaa.gov/hazel/view/hazards/volcano/event-data",
        "error": "JavaScript shell with no text. The legends were read from its static bundle instead.",
    },
    {"id": "cole_par", "url": "https://par.nsf.gov/biblio/10555826", "error": "Item not found page, not cited."},
    {
        "id": "pelee_erudit",
        "url": "https://www.erudit.org/fr/revues/bshg/2010-n156-bshg02573/1036841ar/",
        "error": "Landing page without article text, not cited.",
    },
    {
        "id": "pelee_paperspast",
        "url": "https://paperspast.natlib.govt.nz/newspapers/GIST19020524.2.20",
        "error": "Script-only response with no text, not cited.",
    },
    {"id": "emdat", "url": "https://www.emdat.be/", "error": "Needs registration. Not attempted, by instruction."},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_in(path: Path) -> int | None:
    if path.suffix != ".json":
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data.get("features", data.get("items", data.get("hourly", {}).get("time", []))))


def merged_sources() -> dict[str, dict]:
    sources: dict[str, dict] = {}
    for name in ("manifest.json", *PARTS):
        path = ROOT / name
        if path.exists():
            for source in json.loads(path.read_text(encoding="utf-8"))["sources"]:
                sources.setdefault(source["id"], source)
    for sid, (url, file, licence, citation) in ADDED.items():
        stored = sources.get(sid, {})
        sources[sid] = {**stored, "id": sid, "url": url, "file": file, "licence": licence, "citation": citation}
    return sources


def finished(source: dict) -> dict | None:
    path = ROOT / source["file"]
    if source["id"] in DROP or not path.exists():
        return None
    if path.suffix == ".html" and path.stat().st_size <= BOT_CHALLENGE_BYTES and source["id"] != "noaa_volcano_legend":
        return None
    licence, citation = TERMS.get(source["id"], (source.get("licence"), source.get("citation")))
    if source["id"].startswith("weather_"):
        licence, citation = CC_BY_OPEN_METEO, OPEN_METEO
    retrieved = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
    return {
        "id": source["id"],
        "url": source["url"],
        "retrieved_at": source.get("retrieved_at") or retrieved,
        "sha256": sha256(path),
        "file": source["file"],
        "licence": licence or NOT_CONFIRMED,
        "citation": citation or NOT_CONFIRMED,
        "rows": rows_in(path),
    }


def main() -> None:
    sources = [s for s in map(finished, merged_sources().values()) if s]
    sources.sort(key=lambda s: s["id"])
    (ROOT / "manifest.json").write_text(json.dumps({"sources": sources}, indent=2) + "\n", encoding="utf-8")
    (ROOT / "access_failures.json").write_text(json.dumps(ACCESS_FAILURES, indent=2) + "\n", encoding="utf-8")
    for name in PARTS:
        (ROOT / name).unlink(missing_ok=True)
    print(len(sources), "sources;", sum(s["licence"] == NOT_CONFIRMED for s in sources), "licences not confirmed")


if __name__ == "__main__":
    main()
