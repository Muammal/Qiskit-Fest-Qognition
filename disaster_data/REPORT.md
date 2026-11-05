# Real disaster data for Stranded

This folder holds real volcano, island and weather data, for calibrating the engine later and for citing in the final report. Nothing in `engine/` was changed. The data describes past events. It does not establish that the model is right, and it cannot predict anything.

Three results matter most:

- **Lethal cold has weak support in a tropical setting.** St Vincent's coldest 5% of night hours are at or below 19.2 °C.
- **Wind must be taken per event.** Over 2021 to 2024, 500 hPa air at St Vincent moved west on average. In April 2021 it moved east. Surface wind moved west on average in both periods.
- **The engine's storm rate is far above St Vincent's reanalysis.** Calm-to-storm is 0.03 in the engine and 0.00003 in the data. Part of that gap is probably because a coarse grid smooths extremes.

## What we collected

Access dates are 2026-11-03 and 2026-11-04. `manifest.json` has the exact URL, time, SHA-256 and citation for all 49 sources. It replaces the three older partial manifests.

| Category | Source | Licence | Citation | Rows |
|---|---|---|---|---|
| Volcanoes | Smithsonian GVP WFS (`gvp_volcanoes`) | not confirmed: GVP web pages return 403 | not confirmed | 1,214 |
| Eruptions | Smithsonian GVP WFS (`gvp_eruptions`) | not confirmed | not confirmed | 11,089 |
| Volcanic events | NOAA NCEI HazEL (`noaa_volcano_events`) | not confirmed | doi:10.7289/V5JW8BSH | 903 |
| Tsunamis | NOAA NCEI HazEL (`noaa_tsunamis`) | not confirmed | doi:10.7289/V5PN93H7 | 3,140, of which 138 volcanic |
| Earthquakes | NOAA NCEI HazEL (`noaa_earthquakes`) | not confirmed | citation text not read | 6,698, of which 194 near the islands |
| Fatalities | Brown et al. 2017 supplement (`brown_fatalities`) | not confirmed: article page blocked | DOI 10.1186/s13617-017-0067-4 | 635 incidents, 133 on small islands |
| Coastlines | Natural Earth 10 m land and minor islands | public domain, per its terms page | Natural Earth | shapefiles |
| Cyclones | IBTrACS v04r01 (`ibtracs`) | not confirmed | Knapp et al. 2010 and Gahtan et al. 2024, doi:10.25921/82ty-9e16 | 217 storm and island pairs |
| Weather | Open-Meteo archive, five islands | CC-BY 4.0, per its terms | Open-Meteo | 87,672 hours each |
| Upper wind | Open-Meteo historical-forecast, St Vincent | CC-BY 4.0 | Open-Meteo | 32,904 hours, from April 2021 |
| Lead times | Einarsson 2018 Table 1, **Iceland only** | CC BY, per the article | doi:10.3389/feart.2018.00045 | 24 rows, 22 with a value |
| Case studies | 24 cited web pages, see `case_studies.json` | mostly not confirmed; see manifest | per manifest | 6 cases, 76 facts |

Licence text is filled in only where we read the provider's own words. 33 of the 49 manifest entries say "not confirmed". Check those before republishing any raw data.

### Case studies

Each quote is copied from its page and was checked against the cached copy. `tools/verify_quotes.py` repeats that check. French quotes stay in French.

| Case | Facts | Unrest to onset | Onset to first flow | Comparison with the GVP catalogue start |
|---|---|---|---|---|
| `st_vincent_2021` | 13 | null: November to December 2020 is month precision | 24 h at day precision; the paper says more than 24 h | GVP has 2020-12-27, the effusive onset, also stored as a fact |
| `heimaey_1973` | 11 | 29.8 h | none reported | matches 1973-01-23 |
| `pelee_1902` | 18 | null: month precision | 360 h, day precision | matches 1902-04-23 |
| `miyakejima_2000` | 12 | 24 h, day precision | 1,512 h, day precision | matches 2000-06-27 |
| `montserrat_1995` | 11 | null: month precision | 6,240 h, day precision | matches 1995-07-18 |
| `la_palma_2021` | 11 | 192 h, day precision | none reported | matches 2021-09-19 |

Within a key, the first fact listed is the one used for lead times and scenarios: the most precise date, then a primary source.

Two judgement calls on labels:

- We marked the IPGP page `secondary`. IPGP runs observatories, but this page is an explainer that credits the UWI Seismic Research Centre.
- We marked the Michigan Tech copies of Montserrat Volcano Observatory reports `primary`, because they are the observatory's own text on a mirror.

### Codes

**NOAA agent codes.** HazEL's normal page is a JavaScript shell, so we read the legend as text from its static bundle (`noaa_hazel_legend`). Case carries meaning, so `M` and `m` stay separate:

- `A` avalanche, `E` electrical, `F` floods, `G` gas
- `I` indirect deaths, `L` lava flows, `M` mudflows or lahars
- `m` secondary, post-eruption mudflows
- `P` pyroclastic flows, surges and direct blasts
- `S` seismic, `T` tephra, `W` waves or tsunami

Compound strings such as `T, m` are kept as NOAA wrote them.

**NOAA tsunami cause.** `volcanic_tsunamis.csv` uses code 6, which the same legend defines as "Volcano". Three mixed codes also involve a volcano and are left out: code 4 (22 events), code 5 (2 events) and code 7 (20 events).

### Scenarios

| Scenario | Wind | Onset step | First flow step | Signs | Weather in 36 bins | Temperature |
|---|---|---|---|---|---|---|
| `st_vincent_2021` | 500 hPa | 18 (12:41 UTC, 9 April) | null | tremor and gas at 0, eruption at 18, ash at 24 | 34 calm, 2 rain, 0 storm | 19.7 to 23.1 °C |
| `la_palma_2021` | 10 m fallback | 19 (14:13 UTC, 19 September) | null | eruption at 19 | 36 calm | 8.9 to 17.4 °C, from a 1,672 m cell |

St Vincent's `first_pdc_step` is null because the sourced first-flow fact has a date and no time. Signs with only a date sit at 00:00 UTC of that day, so they can be up to a day early.

## What we could not get, and why

- **EM-DAT** needs registration, so we did not attempt it. A teammate can register at emdat.be.
- **GVP web pages and terms** return 403 to scripts. The catalogue data came through the WFS, but its licence text could not be read, and no quote cites those pages.
- **Brown et al. 2017 article page** returned a bot challenge. Its supplementary spreadsheet was reachable, so the database is included, but we could not read its licence. An earlier attempt on a different download host failed.
- **Two Nature papers**, one on St Vincent and one on La Palma, returned bot challenges and are not cited.
- **A time of day for St Vincent's first flow.** The HTML abstract gives 10 April only. We read pages 2 and 5 to 12 of the accepted manuscript, and later pages may hold more. A PDF cannot be a required source here, so `first_pdc_step` stays null.
- **2021 isopachs and PDC deposit maps as data.** Cole et al. show them as figures. We found no GIS files.
- **A lahar chronology for St Vincent.** We found no usable source, and the USGS data release named in `docs/VOLCANO_MODEL.md` was not opened.
- **A settled date for the Miyakejima whole-island order.** See the disagreements below.

The UWI Seismic Research Centre is the most likely holder of the St Vincent isopachs, deposit maps and lahar records. The St Vincent National Emergency Management Organisation (NEMO) and the Montserrat Volcano Observatory may also help. `access_failures.json` lists the blocked or empty pages.

## Model versus data

Engine values come from `engine/volcano.py`, `engine/events.py`, `engine/agent.py`, `engine/simulation.py` and `docs/VOLCANO_MODEL.md` at commit `2c4599e`. "Pending" describes changes that have since landed in commit `269dcd2`, the demo build.

| Constant | Engine at `2c4599e` | What the data says | Recommendation |
|---|---|---|---|
| Eruption probability | 2/3 (`ERUPTION_PROBABILITY`), from a search summary | **Our data cannot test this.** All six cases erupted because we chose eruptions, and the catalogues have no count of unrest that faded. | Keep it labelled as an unverified prior. Read the Phillipson and Gottsmann paper before citing it. |
| Onset range | `ONSET_RANGE` 4 to 19 steps, or 8 to 38 h | St Vincent is step 18 in its scenario. Heimaey had 29.8 h and Miyakejima about 24 h from first unrest. La Palma had about 8 days. St Vincent and Montserrat had months to years of earlier unrest. | Keep it as "final escalation only", and say so. It does not describe unrest as a whole. |
| First-flow delay | `PDC_DELAYS` = (0, 0, 0, 1, 3, 8, 15) steps, or 0 to 30 h. Pending: (0, 0, 1, 2, 3, 5, 8, 15) | St Vincent: more than 24 h, over 12 steps. Pelée 15 days, Miyakejima 63 days, Montserrat 260 days, each from an earlier onset. None of the four shows a flow within 24 h. | Fewer zero delays looks like the right direction, so the pending change fits better, but only the value 15 fits St Vincent. With four selected cases, short delays are unsupported here, not ruled out. |
| Weather transitions | calm .78/.19/.03; rain .22/.65/.13; storm .12/.38/.50 | See the weather table. St Vincent: calm .876/.124/.00003; rain .377/.622/.0008; storm .063/.563/.375, from 16 samples. | Do not adopt the storm row from St Vincent alone. Choose an analog island deliberately, and keep the thresholds labelled as assumptions. |
| Night temperature and cold | Cold-night chance .12 + .22 wet + .20 ash; warmth loss .03 to .10 per event; death at warmth 0, cause "hypothermia". Pending: lethal cold removed | St Vincent night p5 is 19.2 °C and the coldest hour in ten years is 16.7 °C. Montserrat night p5 is 20.4 °C. | Supports the pending removal for a tropical island. Reconsider it if the fictional island is meant to be temperate. |
| Wind | None: ash transport is listed as out of scope. Pending: seeded wind with slow drift | Direction changes by event and by height. See the wind section. | If wind is added, use per-event data and never a fixed bearing. |
| Hazard mix | PDC, lava and lahar are lethal. Ash reduces warmth and safety and is not directly lethal. No tsunami or gas toxicity | In NOAA, 92 fatal small-island events have an agent. Events naming tephra: 35, pyroclastic flows: 28, waves: 16, mudflows: 12 (plus 4 secondary), lava: 10, indirect: 8, gas: 7. In Brown, reported deaths are led by tsunami (40,634) and PDCs (36,693), but Krakatau 1883 and Pelée 1902 alone are 71% of the 90,624 total. | PDC and lahar priority is reasonable. Tephra and tsunami are real killers the engine does not model. Say so in the report as a scope limit. |

Springs and food have also moved in the demo build. We have no data bearing on either, so they are not compared.

### Weather by island

Bins are 2 hours long, using the brief's assumed thresholds. The engine's long-run mix, worked out from its own matrix, is 47.0% calm, 39.8% rain and 13.2% storm.

| Island | Cell elevation | Calm | Rain | Storm | Storm bins | Calm to storm | Storm to storm | Wind-only storm bins | Night p5 | Coldest hour | Cyclones per year |
|---|---|---|---|---|---|---|---|---|---|---|---|
| St Vincent | 716 m | 75.2% | 24.7% | 0.04% | 16 | .00003 | .375 | 5 | 19.2 °C | 16.7 °C | 1.11 |
| Montserrat | 556 m | 90.3% | 9.6% | 0.17% | 75 | .00018 | .547 | 33 | 20.4 °C | 17.7 °C | 1.13 |
| Miyakejima | 740 m | 73.1% | 13.6% | 13.2% | 5,799 | .0174 | .818 | 5,427 | 5.4 °C | −1.0 °C | 2.30 |
| Stromboli | 847 m | 92.5% | 6.5% | 1.07% | 469 | .00252 | .633 | 457 | 6.6 °C | −1.4 °C | 0.00 |
| La Palma | 1,672 m | 94.1% | 5.1% | 0.84% | 369 | .00146 | .799 | 346 | 2.5 °C | −2.8 °C | 0.02 |

Cyclone rates count storm centres within 200 km, 1980 to 2025. That is not the same as impact on the island.

## Findings that contradict the current model

**Storms at St Vincent.** Reanalysis shows almost no `storm` bins: 16 out of 43,836. The storm row of the Markov matrix therefore rests on just 16 samples, and calm-to-storm rests on one transition. The engine's calm-to-storm is about 1,000 times higher. This does not mean St Vincent has no severe weather: it has about 1.1 cyclones a year within 200 km, and a coarse grid smooths extremes. Both statements are true, and the data cannot say how much each contributes.

**Grid elevation.** Each Open-Meteo cell is a broad average with its own elevation, and St Vincent's is 716 m. So these temperatures are probably cooler than at the coast, and the night figures below are, if anything, too cold for someone near sea level. La Palma's 1,672 m cell makes its 2.5 °C unrepresentative of the coast. High cells also change wind: most "storm" bins at Miyakejima, Stromboli and La Palma are wind-only. The engine's long-run storm share matches Miyakejima's only on the surface, because that is mostly wind in a 740 m cell.

**Cold.** St Vincent's night 5th percentile is 19.2 °C, using local hours 20 to 6, so lethal cold within 72 h has weak support in a tropical setting. Air temperature is not the whole story: rain, wind and wet clothing matter, and we collected no physiology data. Stromboli (6.6 °C) and Miyakejima (5.4 °C) are much colder in winter, so this depends on which island you choose as the analog. Pick that analog first, and then decide about cold.

**Wind.** All values are the bearing air moves toward.

| Level | 2021 to 2024 mean | April 2021 mean | 9 to 22 April 2021 mean | 2021-04-09 12:00 UTC | Speed then |
|---|---|---|---|---|---|
| 10 m | 268° (west) | 268° | 269° | 269° | not in this file |
| 500 hPa | 259° (west) | 90° (east) | 116° | 114° | 14.5 km/h |
| 200 hPa | 88° (east) | 87° | 103° | 70° | 84.3 km/h |

- A fixed wind direction would be wrong. The 500 hPa mean over 2021 to 2024 points almost opposite to April 2021.
- The upper-air record starts in April 2021, so that mean covers under four years and is not a long climatology.
- Surface wind blew the opposite way to the eruption's ash, which reached Barbados to the east from 10 April.
- 500 hPa alone is not enough. Around the first explosion, 200 hPa air moved almost six times faster on a bearing 44° different. The plumes reached about 8 km at first and later up to about 20 km, per IPGP. As general meteorology, not from our data, 500 hPa is only about 5 to 6 km up, so much of the plume sat above that level.
- `wind_source` is "500hPa" because the brief requires it. A later ash model should consider several levels.

**The "15 minutes to 13 days" range is Iceland only.** It comes from Einarsson 2018 Table 1, and it does not transfer to tropical island volcanoes. The table has 24 rows, 22 of them with a single value, while its text speaks of 21 eruptions. We could not reconcile the difference, so all rows are kept. The median is 1.875 h, and 11 of the 22 values fall under 2 h, so half are shorter than one engine step. Separately, the paper says warnings were issued in about two thirds of cases. That is unrelated to the engine's 2/3 eruption probability, so do not cite one for the other.

**The ~30 h anchor.** The engine doc calls Cole's first-flow delay about 30 h, from a supplied summary. The paper's abstract says more than 24 h on 10 April, and we could not confirm 30 h from what we read.

## Where sources disagree

Both values are kept in `case_studies.json`, never averaged.

- **St Vincent evacuees:** about 13,000 (IPGP) and about 16,000 (Wikipedia).
- **St Vincent onset:** effusive on 27 December 2020 and explosive on 9 April 2021. These are two phases, not a true conflict.
- **Heimaey onset:** 01:45 (museum), 01:50 to 01:55 (Einarsson), about 01:55 (Wikipedia).
- **Heimaey evacuees:** 5,200 (museum) and 5,300 (Wikipedia).
- **Pelée first unrest:** January 1902 (SDSU), early April (Wikipedia), late April (USGS).
- **Pelée first flow:** about 07:50 (SDSU) and about 08:00 (USGS).
- **Pelée deaths:** about 26,000 (USGS), about 28,000 (Wikipedia, SDSU), about 29,000 (Wikipedia infobox).
- **Pelée 5 May mudflow deaths:** 23 (USGS) and 150 (Scientific American blog).
- **Miyakejima onset:** 27 June submarine (ERI), 8 July summit (Nakada et al.), 14 July (Wikipedia).
- **Miyakejima whole-island evacuation:** ordered 31 August (Volcano World), and evacuated in early September (ERI). The Geological Survey of Japan page says it was decided on 1 September. That sentence is stored only here, because Japanese has no spaces and cannot meet the quote word-count rule.
- **Montserrat first flow:** 29 March 1996 block and ash flows, and 3 April 1996 "first pyroclastic flow".
- **La Palma onset:** 14:13 and 14:12 UTC, both in one Wikipedia article. Its prose also calls 14:13 "local time", which conflicts with its own infobox.
- **La Palma first unrest:** since 2017 (Eos), a few years (Bonadonna et al.), 11 September 2021 (Wikipedia).

**Pelée evacuation.** The stored fact is the evacuation of Le Prêcheur on 10 and 11 May, after the disaster. Saint-Pierre was not evacuated beforehand. The SDSU page says troops turned people back, but that sentence has no digit, so it is noted in the fact's value and not stored as a quote.

## Limits

- **Iceland-only lead times.** They should not be applied to other regions.
- **Catalogue reporting bias.** GVP, NOAA and Brown record what was noticed and written down. Old, remote and small events are undercounted. NOAA lists only significant events.
- **Volcano matching.** NOAA events are matched to the nearest GVP volcano within 30 km, which is an assumption. 21 of the 113 matched fatal events have no agent code.
- **Brown totals.** They are reported deaths. Some are uncertain, and they include indirect and non-eruptive causes.
- **Reanalysis resolution.** Each weather record is one coarse grid cell, not a station. It smooths extremes, and its elevation affects temperature and wind.
- **Weather thresholds.** The calm, rain and storm cut-offs are assumptions from the brief.
- **Surface versus upper wind.** Surface wind can run opposite to ash transport, and one level does not describe a tall plume.
- **Selected case studies.** These six are well-documented eruptions, not a random sample, and they contain no false alarms. They cannot give rates.
- **Onset definitions differ.** Phreatic, effusive, submarine and explosive onsets are all called "onset", so delays are not strictly comparable.
- **Absence of a PDC.** The `no_pdc_reason` for Heimaey and La Palma means none appears in the sources read. It is not a statement by those sources that none occurred.
- **Wikipedia.** It is always `secondary` and is at most half of any case's facts. At St Vincent, the 16,000 evacuee figure comes only from Wikipedia.

## Rebuilding

`tools/build_calibration.py` rebuilds `catalog/`, `calibration.json` and `scenarios/` from the cached `raw/` files with no network.

`raw/` is gitignored, so it must be collected again on a new machine:

- `tools/collect_disaster_data.py` fetches the main datasets.
- `tools/fetch_*.py` fetch the case-study pages.
- `tools/extract_einarsson.py` writes `precursor_rows.json`.
- `tools/merge_manifest.py` writes `manifest.json`.
- `tools/verify_quotes.py` rechecks every quote.
