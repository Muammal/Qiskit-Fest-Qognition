# 003: the warning-time gate compared the wrong thing

**Changed after a failure, so it is written down here.** `eruption-lead-time-sampling` first asked whether the median of sampled warning times was within 15% of the catalogue's median. It recorded FAIL at 1.2.

The catalogue has 22 values, so its median falls between its two middle values, 5,400 s and 8,100 s, giving 6,750 s. A sampled median almost always lands on one of those two values, so the ratio comes out as 0.8 or 1.2, and both fail. The target could pass only if exactly half of 100,000 draws fell on each side, which has a probability of about 0.25%. No correct sampler could pass it.

**What replaced it:** the largest gap between the sampled and catalogue distributions, with a tolerance of 0.01. This is a check of the sampling, not of the real world. It says nothing about whether real warnings look like these selected cases. The old measure stays available as `lead_time_ratio`.

**What did not change:** `eruption-size-holdout`, the real-world check on eruption sizes, still records its FAIL.

The sampling code was not changed in response to this. A second reviewer should confirm the reasoning above.
