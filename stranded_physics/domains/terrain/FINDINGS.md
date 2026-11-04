# terrain T1 findings

First run on real data, 2026-11-04. Gate targets were committed before the download, in `5e7760a`.

| Gate | Target | Measured | Verdict |
|---|---|---|---|
| Summit height | 1220 m, within 100 m | 1202 m on the 90 m grid | PASS |
| Island area | 330.75 km², within 25 km² | 346.9 km² | PASS |
| Summit location | 0 m from catalogue point, within 1500 m | 2007 m | **FAIL** |
| Canopy bias | None, reported only | See below | NO_TARGET |

These targets are anchors. They show the surface was read and placed sensibly. They validate no hazard model.

## The failed gate

The failure stays on record, and the tolerance has not been changed. The evidence suggests the target was wrong, not the map:

- On the 30 m source, the highest point is 1221.7 m at 13.3482 N, 61.1782 W. That is close to the catalogue height, about 2 km north of its position (13.33 N, 61.18 W).
- The catalogue position stands at 736 m on the 90 m grid, with higher ground in every direction: 893 to 1100 m within 1.5 km. Going north, the ground stays near 750 m for 720 m, then climbs past 1000 m by 1440 m.
- That fits a point inside the summit crater, reported as about 1.6 km wide and 300 to 600 m deep ([Nature Communications, 2022](https://www.nature.com/articles/s41467-022-31901-4.pdf)). The catalogue point appears to mark the crater, not the highest ground.

This reading was made after seeing the result, so it is a diagnosis, not a pass. A replacement gate would need its own target, labelled as written after this run, and someone else's review. Until then T-201 stays blocked.

## Canopy bias

GLO-30 minus FABDEM, on land cells of the 90 m grid:

| Cells | Count | Mean | Median | 90th percentile |
|---|---|---|---|---|
| Forest valley floors | 12,586 | 6.7 m | 6.0 m | 13.5 m |
| Open valley floors | 1,416 | 1.6 m | 1.0 m | 4.9 m |
| All forest | 38,614 | 6.2 m | 5.5 m | 12.3 m |
| All open ground | 4,210 | 1.8 m | 1.2 m | 4.9 m |

FABDEM is a machine-learned correction of this same surface, not a survey, so this only sizes the bias roughly. Valley floors here are cells at least 15 m below their 1 km neighbourhood mean, an assumed definition. The model does not correct the bias. T-202 must check whether it blocks or diverts flow paths.

## Known limits

- The surface is GLO-30 as distributed. Check its acquisition dates before treating it as the April 2021 pre-eruption surface, and don't assume it shows the crater as it is today.
- WorldCover is mapped from 2021 imagery, so it may include eruption damage on the northern slopes.
- Licences and citations are unconfirmed until T-104.
- T-001 has not been frozen. If the interfaces change, this category may need to change with them.
