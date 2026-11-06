# Pompeii scenario: sources and how each number was derived

Working record for the research paper. It lists every source, what was actually read from it, how far it can be trusted, and which code uses it. It will be updated as the scenario is built, and folded into a combined Pompeii and Titanic report at the end.

**This is a demonstration model, not a reconstruction.** See [What the results can and cannot support](#what-the-results-can-and-cannot-support) before citing any output.

## How to read this document

Every figure carries one of these labels. The same labels are in the `PROVENANCE` tables in `engine/city.py`, `engine/eruption.py` and `engine/citizens.py`.

| Label | Meaning |
|---|---|
| **read** | Read on the page, or in the text an automated fetch returned |
| **excerpt** | Seen only as a search-result excerpt. The page itself was not opened |
| **news** | From a news report of research, not the research itself |
| **school** | From a school or student study page. Not citable in a paper |
| **blog** | From a blog or forum post. Not citable in a paper |
| **inferred** | Reasoned from a source; no source states it directly |
| **memory** | From the author's memory. Not confirmed by any source read |
| **assumption** | A modelling choice with no source |

**Check before citing.** Pages were read through an automated fetch tool, which sometimes returned only part of a page or a machine summary. Quotes and figures must be checked against the originals. Read the primary papers before citing them.

## Sources

### Papers

| Source | What was read | Used for |
|---|---|---|
| Sparice D., Amoretti V., Galadini F., Di Vito M.A., Terracciano A., Scarpati G., Zuchtriegel G. (2024). A novel view of the destruction of Pompeii during the 79 CE eruption of Vesuvius (Italy). *Frontiers in Earth Science* 12. [doi:10.3389/feart.2024.1386960](https://www.frontiersin.org/articles/10.3389/feart.2024.1386960/full) | About a third of the page text returned verbatim, the rest as machine summary | Fall timing, pumice depth, quake |
| Scarpati C., Perrotta A., Martellone A., Osanna M. (2020). Pompeian hiatuses. *Geological Magazine* 157(4), 695-700. [doi:10.1017/S0016756819001560](https://www.cambridge.org/core/journals/geological-magazine/article/pompeian-hiatuses-new-stratigraphic-data-highlight-pauses-in-the-course-of-the-ad-79-eruption-at-pompeii/0D717E1C9BBDFD4C10AE34A0F2B86ADF) | Article text | Breaks, 07:30 and 08:00 layers, first flow reaching 200 m into town |
| Luongo G., Perrotta A., Scarpati C., De Carolis E., Patricelli G., Ciarallo A. (2003). Impact of the AD 79 explosive eruption on Pompeii, II. *J. Volcanology and Geothermal Research* 126, 169-200. [doi:10.1016/S0377-0273(03)00147-1](https://www.iris.unina.it/handle/11588/163033) | **Abstract only** | Victim counts and where they were found |
| Sigurdsson H., Carey S., Cornell W., Pescatore T. (1985). The eruption of Vesuvius in AD 79. *National Geographic Research* 1(3). [Record](https://digitalcommons.uri.edu/gsofacpubs/1114) | **Abstract only** | Start, 7 h of white pumice, 6 surges |
| Carey S., Sigurdsson H. (1987). Temporal variations in column height and magma discharge rate. *GSA Bulletin* 99(2). [Record](https://digitalcommons.uri.edu/gsofacpubs/1107) | **Abstract only** | About 19 hours |
| Scarpati group (2025). The AD 79 Vesuvius eruption revisited: [the pyroclastic density currents](https://www.lyellcollection.org/doi/abs/10.1144/jgs2024-072) and [Plinian and post-Plinian falls](https://pubs.geoscienceworld.org/gsl/jgs/article-abstract/182/1/jgs2024-071/648461/The-ad-79-Vesuvius-eruption-revisited-Plinian-and?redirectedFrom=fulltext). *J. Geological Society* 182 | **Excerpt only. Publisher blocked access.** Authors and details unconfirmed | 17 flows, post-Plinian phase of about 12 h |
| Sigurdsson H. et al. (1982). The eruption of Vesuvius in AD 79. [Record](https://www.journals.uchicago.edu/doi/10.2307/504292) | **Not read. Blocked.** | Not used directly |

**Get these before citing:** the two *Journal of the Geological Society* papers, Luongo 2003, Sigurdsson 1985 and Carey & Sigurdsson 1987, in full.

### Official and reference pages

| Source | What was read | Used for |
|---|---|---|
| Pompeii Archaeological Park, [A Guide to the Pompeii Excavations](https://pompeiisites.org/wp-content/uploads/A-Guide-to-the-Pompeii-Excavations-2.pdf) | Text extracted from the PDF, filtered to places and streets | Gates, walls, city size, street names, amphitheatre region, 3.5 m pumice |
| Pompeii Archaeological Park, [news item, 2025](https://pompeiisites.org/en/?p=64435) | Page | At least 20,000 people, about 1,300 victims, survivors |
| [INGV press release, 2024](https://www.ingv.it/en/urp-press/Press-office/Press-releases/Pompeii-reconstructed-the-effects-of-seismicity-during-the-eruption-of-Vesuvius-in-79-AD-2) | Page | Decline in activity, quakes before phase two |
| [Michigan Tech summary](https://geo.mtu.edu/volcanoes/boris/mirror/mirrored_html/VESUVIO_79.html) of Sigurdsson 1985 (mirror, modified 1996, no author named) | Page | Surge clock times, 12-15 cm per hour |
| [Roman Ports: the port of Pompeii](https://www.romanports.org/en/articles/ports-in-focus/625-the-port-of-pompeii.html) | Page | 8 km to Vesuvius, 40 m terrace, uncertain port |
| Wikipedia, [Pompeii](https://en.wikipedia.org/wiki/Pompeii) and [Eruption of Vesuvius](https://en.wikipedia.org/wiki/Eruption_of_Mount_Vesuvius_in_79_AD) | Most of each page | 11,000-11,500 population, 1,150 bodies, date dispute. Use for orientation, not citation |

### News

| Source | Note |
|---|---|
| [Hyperallergic, 2025](https://hyperallergic.com/new-research-shows-slaverys-outsized-role-in-pompeiis-economy), on Seth Bernard's study in *Past & Present* | The enslaved share. **Cite Bernard's article directly once obtained** |
| [Jerusalem Post, 2025](https://www.jpost.com/archaeology/archaeology-around-the-world/article-839410) | States it was written with an automated system. Source of the 80-minute interval and 20:05 end time. Weak |
| [Eos, 2024](https://eos.org/?p=225596), [History.com, 2024](https://www.history.com/articles/pompeii-eruption-volcano-earthquakes), [Artnet](https://news.artnet.com/art-world/pompeii-pliny-vesuvius-eruption-date-2587228), [History.com, date](https://www.history.com/articles/pompeii-vesuvius-destruction-date) | Context for the quake and the date dispute. History.com's 5.8 quake magnitude conflicts with Sparice 2024 |

### Not citable

| Source | Used for |
|---|---|
| [Narrabeen HS: plans](https://sites.google.com/narrabeenhs.com/pompeiiandherculaneum/1-2-plans-and-streetscapes), [local politics](https://sites.google.com/narrabeenhs.com/pompeiiandherculaneum/2-3-local-political-life) (school pages) | Magistrates, block sizes, terrain slope, palaestra |
| [Pompeionline](https://www.pompeionline.net/pompeii/map.htm) (website) | Forum position, Via di Nola |
| [Brainscape flashcards](https://brainscape.com/flashcards/core-16391306/packs/22193690) (student) | Early role information only; superseded |
| [Eixos blog](https://blog.eixos.cat/?p=744) | About 1,000 establishments |
| Madain Project pages: [Porta Ercolano](https://madainproject.com/porta_ercolano), [Via dell'Abbondanza](https://madainproject.com/via_dell_abbondanza) | **Excerpts only**; the site blocked the fetch |

## Population and roles

Default 11,500, with 20,000 as a setting. In code: `engine/citizens.py`.

| Role | At 11,500 | At 20,000 | Basis | Label |
|---|---:|---:|---|---|
| Residents | 6,826 | Remainder | Remainder | Calculated |
| Enslaved | 3,450 | 6,000 | 30%, reported from Bernard | news |
| Merchants | 1,000 | Scaled | One person per establishment, from a blog count | assumption, blog |
| Visitors | 100 | Scaled | The user's labelled count | assumption |
| Council | 100 | 100 | [Attested for three other towns](https://journal.fi/arctos/article/download/85058/44034/127474), seen as an excerpt; sizes vary from 30 | assumption |
| Guards | 20 | Scaled | The user's labelled count. No evidence found | assumption |
| Magistrates | 4 | 4 | Two duumviri, two aediles | school |

Population sources disagree: 10,000-20,000 and 11,000-11,500 (Wikipedia), at least 20,000 (the park), 15,000-30,000 (Hyperallergic). Pompeii had no king; it was a Roman colony under elected magistrates.

Household sizes, servants per household and noon locations are all assumptions, and they set how fast news travels.

## Maps

In code: `engine/city.py`. The maps are labelled schematics.

| Fact | Value | Label |
|---|---|---|
| City area | 66 hectares ([guide](https://pompeiisites.org/wp-content/uploads/A-Guide-to-the-Pompeii-Excavations-2.pdf) p. 9) | read |
| Walls | Over 3,200 m (guide p. 81). **The drawn oval is about 2,916 m, 9% short** | read |
| Porta Marina, west | Guide p. 81 | read |
| Porta Nocera, southeast | Guide p. 38 | read |
| Porta Ercolano, northwest; road to Naples | Excerpt; road from guide p. 75 | excerpt, read |
| Porta Sarno, east end of Via dell'Abbondanza | Excerpt | excerpt |
| **Porta Vesuvio north, Porta Nola northeast, Porta Stabia south** | **Positions from memory** | memory |
| Amphitheatre, southeast | From its region in the guide. One school page says southwest | inferred |
| Vesuvius 8 km away | Roman Ports. **Northwest bearing from memory** | read, memory |
| Vesuvius height | 1,200 m | assumption |
| Coast and Sarno course | Uncertain in the sources | assumption |
| Streets and blocks | Drawn blocks of 18,000 sq m against a sourced 850-5,500. 40% of the town is open | assumption |

## Eruption timeline

In code: `engine/eruption.py`. About 32 hours in 15-minute steps, using the user's combined chronology. Default date 24 August, with autumn as a setting.

| Clock | Event | Basis | Label |
|---|---|---|---|
| About noon, day 1 | Run starts | Sources say late morning to noon | read |
| 13:00 | Main phase, white pumice | Sparice 2024 | read |
| 20:00 | Grey pumice | Sparice 2024 | read |
| 01:00 onward | First flows, not reaching town | Michigan Tech | read |
| 06:30 | First flow reaches 200 m past the north wall | Time from Michigan Tech; distance from Scarpati 2020 | read |
| 07:00 | Pumice ends at 2.8 m | Sparice 2024 | read |
| 07:00 | Quake, with a switch | Order from Sparice 2024; **time assumed** | assumption |
| 07:30 | Flow over the north half of town | Time from Scarpati 2020; **area assumed** | read, assumption |
| 07:45 | Break. The source has two in half an hour; this grid shows one | Scarpati 2020 | read |
| 08:00 | Flow over the whole town | Scarpati 2020 | read |
| To about 19:15 | Nine more flows, 17 in total | Count from excerpt; interval from one news article | excerpt, news |

**Known mismatches:**
- Even pumice gives 1.87 m at 01:00, against about 1.5 m in the Michigan Tech summary.
- Rounded to the grid, the 80-minute interval becomes 75 minutes, so the last flow is at 19:15, not 20:00.
- The news report's 19:06 first-flow time was deliberately left out.

**Assumptions with large effects:** half of roofs fail by 2.8 m of pumice, the quake brings down 30% of those standing, and temperature is 27 C or 17 C.

The date is disputed. The park keeps 24 August, while a charcoal inscription and autumn finds support a later date. The inscription's value is itself contested.

## How people are modelled

In code: `engine/citizens.py` and `engine/pompeii.py`.

- **Mind:** everyone calls the same unedited function. It receives no role, household or status. A test checks this.
- **Noticing:** depends on distance, being indoors, visibility and chance. The role plays no part. The chances are assumptions.
- **News:** servants who know carry it home, so a household with more servants tends to hear sooner.
- **Moving:** `hide` only moves someone once they've been warned, the same rule as `engine/agent.py`.
- **Enslaved people:** decide for themselves by default. A switch holds them with the household. No direct evidence was found either way.
- **Collapse:** 50% of those inside die and the rest are injured (the user's choice; no source).
- **Flows:** lethal to anyone covered, indoors or out (the user's choice). About 300 C for the first flow to reach town is from Wikipedia.
- **Crowding:** 60 people per tile halves walking speed, and each gate takes 1,000 per step. Both are assumptions, with a switch.
- **Starting state:** everyone in town at noon. Earlier tremors are not carried over.
- **Reaching safety:** the Nola, Sarno, Nocera and Stabia road ends count as escape. No boats are modelled.

## On screen

In code: `engine/gui_city.py`, `engine/scenes_pompeii.py`, and hooks in `engine/gui.py`. Display only; none of this changes a result (a test checks this).

- **Maps:** city and region, switched with `M`.
- **Split-screen panels:** up to three people, seeded random across roles, or whoever is clicked. They show what the person heard and in what order, their belief, their probabilities and their action.
- **Written thoughts:** template sentences built only from those values, labelled as illustration. They add no motives or feelings, and the close-up's face stays neutral.
- **Cutscenes,** replayed from the end screen rather than during the run: street level (column), aerial (crowds), from the bay, a house cutaway (roof), a close-up on the followed person, and eye level (flow arrival). Under mapping B, flows reach an almost empty town, or the run ends first.

## Event mapping

The mind only accepts its existing event names, so events have to be translated. **This is a modelling choice, and it dominates the results.** The user chose mapping B on meaning, as the most literal, and asked for all four to be reported.

| Town event | A | B (default) | C | D |
|---|---|---|---|---|
| Column seen | `eruption` | `gas_plume` | `gas_plume` | `tremor` |
| Pumice falling | `ash_fall` | `ash_fall` | `gas_plume` | `tremor` |

`eruption` and `ash_fall` collapse belief to certain danger. `gas_plume` and `tremor` are rotations, meaning ambiguous signs.

Common to all: flow seen is `eruption`, quake and nearby collapse are `tremor`, news and crowds are `gas_plume`, and being hurt is `injury`.

## Results

Ten seeds (1-10), 11,500 people, 24 August, quake on, crowding on. Deaths as mean and range.

| Mapping | `quantum` | `classical_mixture` | `classical` |
|---|---|---|---|
| A | 0 (0-1) | 0 (0-0) | 0 (0-1) |
| **B (default)** | 0 (0-1) | 0 (0-0) | 0 (0-1) |
| C | **1,063 (1,020-1,117)** | 1 (0-2) | 0 (0-1) |
| D | 0 (0-2) | 0 (0-1) | 0 (0-1) |

Across all 120 runs there were only 8 roof deaths. In C with `quantum`, nearly all deaths are from flows. Some runs ended early because nobody was left in danger, and those count as 0 in town at later times.

| Share of people-steps | `hide` | `rest` | In town at 17:00 | In town at 01:00 |
|---|---:|---:|---:|---:|
| B, `quantum` | 53% | 0% | 22 | 0 |
| C, `quantum` | 23% | 29% | 7,244 | 1 |
| B, `classical` | 59% | 0% | 10 | 0 |

## Assumption tests

One assumption changed at a time. Five seeds (1-5), deaths as mean and range, from 11,500 people unless stated. Baseline settings are listed under Results.

Scripts: [pompeii_sensitivity.py](../tools/pompeii_sensitivity.py) and [pompeii_sweep.py](../tools/pompeii_sweep.py). Raw results: [pompeii_results/](../tools/pompeii_results/).

| Changed | B, `quantum` | C, `quantum` | C, `classical_mixture` |
|---|---:|---:|---:|
| Baseline | 0 (0-0) | 1,050 (1,024-1,092) | 1 (0-1) |
| **Pumice slows walking twice as much** | 96 (84-103) | **8,921 (8,818-8,963)** | 70 (67-74) |
| **Pumice slows walking four times as much** | 2,171 (2,128-2,233) | **11,381 (11,376-11,386)** | 1,136 (1,073-1,174) |
| **Chance of noticing halved** | 32 (25-45) | 1,596 (1,545-1,634) | 87 (83-97) |
| Chance of noticing x1.5 | 0 (0-0) | 399 (367-432) | 0 (0-0) |
| Indoors notices a quarter as often, not half | 4 (3-4) | 1,748 (1,696-1,808) | 13 (10-15) |
| Tighter crowding, 30 per tile | 0 (0-0) | 1,552 (1,520-1,591) | 1 (1-2) |
| Tighter gates, 200 per step | 0 (0-0) | 1,275 (1,231-1,344) | 8 (4-11) |
| Crowding off | 0 (0-0) | 913 (867-957) | 0 (0-1) |
| Enslaved held with household | 0 (0-0) | 1,289 (1,236-1,333) | 0 (0-2) |
| Servant news half as likely | 0 (0-1) | 1,050 (1,003-1,095) | 0 (0-1) |
| Autumn | 0 (0-0) | 1,075 (1,045-1,102) | 1 (0-1) |
| Quake off | 0 (0-0) | 1,043 (1,015-1,075) | 1 (0-1) |
| Collapse kills 25% | 0 (0-0) | 1,050 (1,024-1,092) | 1 (0-1) |
| Collapse kills 100% | 0 (0-0) | 1,055 (1,024-1,092) | 1 (0-1) |
| Roofs fail sooner | 0 (0-0) | 1,051 (1,005-1,095) | 1 (0-1) |
| Roofs fail later | 0 (0-0) | 1,054 (1,024-1,092) | 1 (0-1) |
| 20,000 people | 0 (0-0) | 2,430 (2,367-2,500) | 1 (0-2) |

**What this shows:**

- **Walking on pumice dominates.** Doubling the slowdown takes `quantum` under C from 1,050 to 8,921 deaths. The value has no source. This is the first thing to find evidence for.
- **It can also produce deaths under B.** At four times the slowdown, B gives about 2,171 deaths, so the zero under B depends on this assumption, not only on the mapping.
- **Roof settings barely matter.** The town has emptied before many roofs fail, so collapse odds and timing make almost no difference. The earlier expectation that the collapse rate would strongly affect deaths was wrong under these settings. Roof deaths stay near 0 in most rows, reaching 56 at most, while Luongo 2003 puts 38% of known victims in the pumice phase.
- **The quake and date make little difference** here, for the same reason.
- **The enslaved-held rule has a visible cost under C:** survival for enslaved people falls from about 91% to 84%, while residents stay near 91%. It's a modelling rule with no direct evidence, so this measures the rule, not history.
- **`classical_mixture` stays far below `quantum` under C in every row,** so the coherence gap under C survives these changes. It still does not appear under B without a large slowdown, and the caution in item 3 below still applies.

These runs change one thing at a time, so they do not show how assumptions combine. Five seeds is enough to see large effects, not small ones.

## What the results can and cannot support

**1. The default model overstates escape, and that is left as it is by the user's decision.** Under mapping B almost everyone is out of town within hours, with about 0 deaths. History records at least 1,150 bodies on site. The model has no household delay, and the mind tends to move once warned. It should not be read as a claim that the eruption was survivable.

**2. Mapping C's total is not a match with history.** 1,063 sits near 1,150, but nearly all of those deaths are from flows, with almost none from roofs. Luongo 2003 puts 38% of known victims in the pumice phase, and about half of later victims indoors. The 1,150 figure is excavated finds from part of the site, not a death toll.

**3. The quantum difference is real in the model but fragile.** Under C, `quantum` loses about 1,063 people against 1 for `classical_mixture`, which is the same pipeline without coherence. So coherence has a large effect under C. But it vanishes under A, B and D, and C and D are both "ambiguous" readings. It shows sensitivity to the rotation used for an event, not evidence for quantum cognition in real evacuations. Mapping C was also tested after seeing outcomes, so it can't be presented as a prediction.

**4. Results depend most on two unsourced assumptions.** See [Assumption tests](#assumption-tests): the speed of walking on pumice and the chance of noticing danger. Neither has a source. No conclusion should rest on either until it does.

**5. Sensitive subject matter.** The role of enslaved people is modelled with little evidence, and the people represented were real. The planned written "thoughts" in split-screen panels will be template text labelled as illustration, not model output.

## Open items

- Obtain the blocked primary papers.
- Confirm Porta Vesuvio, Nola and Stabia positions from the guide's maps.
- Find evidence for walking speed on pumice and for how quickly people noticed danger.
- Run combinations of assumptions, and more seeds for small effects.
- Decide whether Titanic should also use the warned-only `hide` rule.
