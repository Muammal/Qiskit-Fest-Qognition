# Sources and derivation report: Titanic, Pompeii and Waterloo scenarios

For use in writing up the research. It records where each number came from, how it was derived and how far it can be trusted. More detail is in [TITANIC_MODEL.md](TITANIC_MODEL.md), [POMPEII_SOURCES.md](POMPEII_SOURCES.md) and [WATERLOO_SOURCES.md](WATERLOO_SOURCES.md).

**Scope:** every scenario built so far. Later scenarios should be added here.

## Summary

- Both scenarios run everyone on the same, unedited quantum mind: 2,208 people on Titanic and 11,500 in Pompeii. Role and status never reach it.
- Waterloo runs 100 people by default on the same mind. It is a hypothetical at a real site, because almost nothing about the real 2012 leak could be confirmed.
- **These are demonstrations, not reconstructions.** Agreement with history is weak evidence, and neither scenario was fitted to history.
- **Results depend heavily on modelling choices with no source.** In Pompeii, `quantum` deaths range from 0 to about 11,400 depending on those choices.
- **The results do not show that quantum cognition explains real evacuations.** A coherence effect appears under one Pompeii mapping and in none of the other three. On Titanic, `quantum` and its no-coherence control are close. At Waterloo it appears under two of three mappings, and nearly vanishes under the third.

## Status labels

| Label | Meaning | Citable? |
|---|---|---|
| **read** | Read on the page, or in text an automated fetch returned | Yes, after checking the original |
| **abstract** | Only the abstract was read | Read the full paper first |
| **excerpt** | Seen only as a search-result excerpt | Read the source first |
| **news** | A news report of research | Cite the research instead |
| **school / blog** | School page, flashcards, blog or forum | No |
| **memory** | From the author's memory, unconfirmed | No |
| **assumption** | A modelling choice with no source | State it as an assumption |

**All pages were read through an automated fetch tool,** which sometimes returned part of a page or a machine summary. Check every quote and figure against the original before citing it.

## Sources to obtain before citing

| Source | Why |
|---|---|
| British Wreck Commissioner's Inquiry, [crew and passengers](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepCrewpax.php), [numbers saved](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepSaved.php), [boats](https://www.titanicinquiry.org/BOTInq/BOTReport/BOTRepBoats.php) | Primary Titanic record. Blocked automated access |
| Scarpati group (2025), *J. Geological Society*: [flows](https://www.lyellcollection.org/doi/abs/10.1144/jgs2024-072), [falls](https://pubs.geoscienceworld.org/gsl/jgs/article-abstract/182/1/jgs2024-071/648461/The-ad-79-Vesuvius-eruption-revisited-Plinian-and?redirectedFrom=fulltext) | Basis for the 32-hour chronology. Blocked; authors unconfirmed |
| [Luongo et al. (2003)](https://www.iris.unina.it/handle/11588/163033), doi:10.1016/S0377-0273(03)00147-1 | Victim counts. Abstract only |
| [Sigurdsson et al. (1985)](https://digitalcommons.uri.edu/gsofacpubs/1114) and [Carey & Sigurdsson (1987)](https://digitalcommons.uri.edu/gsofacpubs/1107) | Classic chronology. Abstracts only |
| Seth Bernard's article in *Past & Present*, reported by [Hyperallergic](https://hyperallergic.com/new-research-shows-slaverys-outsized-role-in-pompeiis-economy) | Enslaved share. News report only |
| [CTV Kitchener, 31 July 2012](https://www.ctvnews.ca/kitchener/article/chlorine-leak-forces-evacuation-at-waterloo-community-centre/) and the *Waterloo Region Record* archive | Waterloo incident. Article body did not load; only the caption was read |
| Forssberg et al. (2019), Larusdottir and Dederichs (*Fire Technology*), Hashempour et al. (doi:10.1002/fam.3209), SFPE Handbook | Evacuation behaviour. Excerpts only, or not obtained |

## Method common to both

**The mind.** `quantum_decide` in `mind/quantum_mind.py`, unedited. Each person's state follows the frozen contract in `contracts.py`. Tests check that no role or status is passed to it. Equal inputs share a cached answer, because the mind ignores position and day under its default rule; tests compare cached answers with direct calls.

**Controls.** `classical_mixture` is the same pipeline with coherence removed. `classical` picks the action with the highest prior.

**Event translation.** The mind only accepts its existing event names and raises an error on others, so every historical event is translated into one. **This is a modelling choice, and it strongly affects results.**

**Known inputs that push decisions.** Editing no mind code does not make inputs neutral:

| Choice | Titanic | Pompeii |
|---|---|---|
| Using volcano event names, which add a `hide` prior | Yes, for all warnings | Yes |
| Some events force belief to certain danger | Rockets, "told it will sink", water at feet | Depends on mapping |
| Who hears what | **Crew told earlier and more strongly, by role** | No role rule; servants carry news to households |
| Safety capped by location | Yes, by deck | No |
| Nudge after choosing `hide` | Yes: safety up, stress down | No |
| `hide` only moves people once warned | **No** | Yes, as in `engine/agent.py` |
| Boarding or leaving rules outside the mind | Women and children first; only `hide` can board | Optional hold on enslaved people, off by default |
| Starting variation in safety and stress | Yes | Yes |

**These differences mean the two scenarios are not directly comparable.** Titanic was built before the bias review, and has not been changed to match Pompeii.

---

## Titanic

### Numbers and where they came from

| Number | Value | Source | Status |
|---|---|---|---|
| Aboard and saved, by class and group | 2,208 and 712 | [Wikipedia casualty table](https://en.wikipedia.org/wiki/Sinking_of_the_Titanic), citing Encyclopedia Titanica | read. The inquiry gives 2,201 and 711 |
| First, second, third class, crew | 324, 284, 709, 891 | Same table | read |
| Saved, by group | 201, 118, 181, 212 | Same table, summed by the author | read |
| Deck, engine, victualling crew | 66, 325, 494 | [Inquiry](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepCrewpax.php) | excerpt |
| Servers | 500 | Remaining crew, so the total reaches 891 | assumption |
| Captain and officers | 1 and 7 | Author's knowledge of the named officers | memory |
| Collision, sinking | 23:40, 02:20 | [Wikipedia](https://en.wikipedia.org/wiki/Sinking_of_the_Titanic) | read |
| Boats uncovered | 00:05 | Wikipedia | Machine summary |
| Loading order | 00:25 | Widely repeated | assumption |
| Rockets | From 00:47; eight by 01:20 | [Wormstedt](https://wormstedt.com/Titanic/revised.html); Wikipedia | read; machine summary |
| Boat launch times | Per boat, in `engine/lifeboats.py` | [Wormstedt revised table](https://wormstedt.com/Titanic/revised.html) | read. Called approximate. Sides inferred from layout |
| Compartments breached | 6 of 16 | Wikipedia | read |
| Water temperature, survival | -2 C, 15-30 minutes | Wikipedia | Machine summary |
| Rescued from the water | About 40 | Wikipedia | read |
| Standard, collapsible seats | 65, 47 | [Museums Worcestershire](https://www.museumsworcestershire.org.uk/wp-content/uploads/2021/05/14.-Launching-the-Lifeboats.pdf) | excerpt |
| Cutter seats | 40 | Gives the widely quoted 1,178 total | memory |
| Ship length | 269 m | Wikipedia article on the ship, as cited in the code | memory, not opened |

**Assumptions:** walking speeds, warning probabilities, loading rates, flood fill rates, waterline shape, chill rates and berths.

### Results

Ten seeds (1-10). Survivors as mean and range.

| Mind | Survivors | First | Second | Third | Crew |
|---|---|---:|---:|---:|---:|
| `quantum` | 608 (570-675) | 218 | 106 | 222 | 63 |
| `classical_mixture` | 600 (554-664) | 238 | 101 | 202 | 59 |
| `classical` | 840 (768-888) | 262 | 134 | 317 | 127 |
| History | 712 | 201 | 118 | 181 | 212 |

- `quantum` and `classical_mixture` differ by 8, inside the seed range. This is no evidence of a coherence effect.
- `classical` chooses `hide` more often (53% of steps, against 22%). That and the boarding rule favour it.
- Crew survival is well below history, because the model seats only three rowers per boat.
- Titanic has **not** had the assumption tests that Pompeii has.

---

## Pompeii

### Numbers and where they came from

| Number | Value | Source | Status |
|---|---|---|---|
| Population, default | 11,500 | [Wikipedia](https://en.wikipedia.org/wiki/Pompeii), from household counts | read |
| Population, setting | 20,000 | [Pompeii park, 2025](https://pompeiisites.org/en/?p=64435) | read |
| Enslaved share | 30% | [Hyperallergic](https://hyperallergic.com/new-research-shows-slaverys-outsized-role-in-pompeiis-economy), reporting Bernard | news |
| Magistrates | 4 | [School page](https://sites.google.com/narrabeenhs.com/pompeiiandherculaneum/2-3-local-political-life) | school |
| Council | 100 | [Attested for three other towns](https://journal.fi/arctos/article/download/85058/44034/127474) | assumption (excerpt) |
| Merchants | 1,000 | [One blog](https://blog.eixos.cat/?p=744), one person per establishment | assumption (blog) |
| Visitors, guards | 100, 20 | No evidence found; the user's labelled counts | assumption |
| City area | 66 hectares | [Park guide](https://pompeiisites.org/wp-content/uploads/A-Guide-to-the-Pompeii-Excavations-2.pdf) p. 9 | read |
| Walls | Over 3,200 m; drawn 2,916 m | Guide p. 81 | read |
| Porta Marina, Porta Nocera | West, southeast | Guide pp. 81, 38 | read |
| Porta Ercolano, Porta Sarno | Northwest, east | [Madain Project](https://madainproject.com/porta_ercolano), [Via dell'Abbondanza](https://madainproject.com/via_dell_abbondanza) | excerpt |
| Porta Vesuvio, Nola, Stabia | North, northeast, south | | memory |
| Vesuvius distance | 8 km | [Roman Ports](https://www.romanports.org/en/articles/ports-in-focus/625-the-port-of-pompeii.html). Bearing from memory | read |
| Main phase, grey pumice, end of fall | 13:00, 20:00, 07:00 | [Sparice et al. 2024](https://www.frontiersin.org/articles/10.3389/feart.2024.1386960/full) | read |
| Pumice depth | 2.8 m | Sparice et al. 2024 | read |
| Flows at 07:30, 08:00, and a break | Times as given | [Scarpati et al. 2020](https://www.cambridge.org/core/journals/geological-magazine/article/pompeian-hiatuses-new-stratigraphic-data-highlight-pauses-in-the-course-of-the-ad-79-eruption-at-pompeii/0D717E1C9BBDFD4C10AE34A0F2B86ADF) | read |
| First flow to reach town | 06:30; 200 m in | [Michigan Tech summary](https://geo.mtu.edu/volcanoes/boris/mirror/mirrored_html/VESUVIO_79.html); Scarpati 2020 | read |
| Quake | About 07:00 | Order from Sparice 2024 | Time is an assumption |
| Number of flows, length of last phase | 17; about 12 h | [2025 flows paper](https://www.lyellcollection.org/doi/abs/10.1144/jgs2024-072) | excerpt |
| Interval between late flows | About 80 minutes | [Jerusalem Post](https://www.jpost.com/archaeology/archaeology-around-the-world/article-839410), which says it used an automated system | news, weak |
| Bodies found on site | 1,150 | [Luongo et al. 2003](https://www.iris.unina.it/handle/11588/163033) | abstract. The park says about 1,300 |
| Victims in pumice layer, flow deposits | 394 (38%), 650 | Luongo et al. 2003 | abstract |
| Later victims on roads | 49% | Luongo et al. 2003 | abstract |

Pompeii had no king. It was a Roman colony under elected magistrates. The eruption date is disputed; this model defaults to the park's 24 August, with autumn as a setting.

**Assumptions:** walking speed on pumice, noticing and news chances, roof failure, collapse deaths, crowd limits, household sizes and noon locations.

### Results

Ten seeds (1-10), 11,500 people. Deaths as mean and range.

| Mapping: column / pumice | `quantum` | `classical_mixture` | `classical` |
|---|---|---|---|
| A: `eruption` / `ash_fall` | 0 (0-1) | 0 (0-0) | 0 (0-1) |
| **B (default): `gas_plume` / `ash_fall`** | 0 (0-1) | 0 (0-0) | 0 (0-1) |
| C: `gas_plume` / `gas_plume` | 1,063 (1,020-1,117) | 1 (0-2) | 0 (0-1) |
| D: `tremor` / `tremor` | 0 (0-2) | 0 (0-1) | 0 (0-1) |

Mapping B was chosen for meaning, as the most literal. It was chosen after these outcomes were visible, though it was not chosen for its result.

### Assumption tests

Scripts: [pompeii_sensitivity.py](../tools/pompeii_sensitivity.py) and [pompeii_sweep.py](../tools/pompeii_sweep.py). Raw results: [pompeii_results/](../tools/pompeii_results/).

Five seeds (1-5), one change at a time. Mean deaths. Full table in [POMPEII_SOURCES.md](POMPEII_SOURCES.md#assumption-tests).

| Changed | B, `quantum` | C, `quantum` | C, `classical_mixture` |
|---|---:|---:|---:|
| Baseline | 0 | 1,050 | 1 |
| Pumice slowdown x2 | 96 | 8,921 | 70 |
| Pumice slowdown x4 | 2,171 | 11,381 | 1,136 |
| Noticing chance x0.5 | 32 | 1,596 | 87 |
| Noticing chance x1.5 | 0 | 399 | 0 |
| Collapse kills 100% | 0 | 1,055 | 1 |
| Quake off | 0 | 1,043 | 1 |
| Autumn | 0 | 1,075 | 1 |
| Enslaved held with household | 0 | 1,289 | 0 |

### Reading these results

- **The default overstates escape.** Under B nearly everyone leaves within hours. The user decided to leave this as it is and report it. At least 1,150 bodies were found, so this should not be read as a claim that the eruption was survivable.
- **The total under C is not a match with history.** Almost all its deaths are from flows, with almost none from roofs, against 38% of known victims in the pumice phase. And 1,150 is excavated finds from part of the site, not a death toll.
- **The coherence effect is real in the model and fragile.** C and D are both "ambiguous" readings, yet deaths are about 1,063 and 0. That shows sensitivity to which rotation is used for an event.
- **Walking speed on pumice is the most powerful assumption and has no source.** This is the most useful single thing to find evidence for.

---

## Waterloo

A hypothetical evacuation at Moses Springer Community Centre, not a reconstruction. All numbers, links, status labels and assumption tests are in [WATERLOO_SOURCES.md](WATERLOO_SOURCES.md).

**Sourced:** the facility and its outlines (City of Waterloo, OpenStreetMap), chlorine limits (EPA, NIOSH, CDC), walking speeds (Rinne et al. 2010), and modelled weather (Open-Meteo).

**Assumed:** the head-count and roles, leak place, size and length, doors and interior, how gas spreads, the chances of noticing, and the alarm.

**Main results,** 100 people, 10 seeds, time until half have left: mapping A `quantum` 564 s against 241 s for `classical_mixture`; mapping B `quantum` 253 s. With the alarm off under A, about 25 of 100 `quantum` people leave against about 91. Mapping A was chosen after seeing results. The alarm is the strongest assumption, and whether the centre had one in 2012 is unknown.

**Comparability:** the mind's three-event memory spans 3 minutes here, 45 minutes in Pompeii and 6 hours on the island. Harm is counted differently too: exposure levels here, deaths in Titanic and Pompeii.

---

## A risk in how the mind is loaded

`contracts.py` and `mind/quantum_mind.py` import each other. If `mind` is imported first, `contracts.quantum_decide` silently uses a heuristic stub instead of the quantum mind, with no error. Checked on 5 November 2026: the window and command-line launchers, the Titanic, Pompeii and Waterloo simulations and the three sweep scripts all load the real mind. A test-only `conftest.py` keeps plain `pytest` on the real mind. The fallback itself remains, so any new script should import `contracts` first and confirm that decisions include a `quantum` field.

---

## What can and cannot be claimed

**Supported, as statements about the model:**
- The same mind reaches different decisions when people hear the same events in a different order.
- Results are highly sensitive to how events are translated, and to the unsourced assumptions listed above.
- In Pompeii, under mapping C only, removing coherence greatly reduces deaths.
- At Waterloo, removing coherence shortens evacuation time under mappings A and C, and barely changes it under B.

**Not supported:**
- That quantum cognition explains behaviour on the Titanic, at Pompeii or at Waterloo.
- That Waterloo shows what happened on 30 July 2012, or anything about the centre's staff or safety systems.
- That either scenario reproduces what happened. Totals that fall near history are not validation.
- That the simulations show how any real person, or any group such as enslaved people, thought or acted. The written thoughts on screen are templates, not model output.

**Gaps to state in any write-up:**
- Primary sources not read in full (listed above).
- Titanic has not had assumption tests, and has more input nudges than Pompeii.
- Assumptions were tested one at a time, so combined effects are unknown.
- The author set the assumptions and saw early results, so this was not a pre-registered test.
