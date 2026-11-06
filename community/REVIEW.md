# How sims are reviewed

A sim goes public when a maintainer merges it to `main`. Review checks that a sim is safe and fair to publish. It doesn't check that a sim is accurate, and it never means a sim has been validated.

## What the automatic check does

`python tools/publish_sim.py check` runs on every pull request. It refuses a file that:

- isn't a valid sim file, or breaks the limits in [docs/SIM_FILES.md](../docs/SIM_FILES.md)
- has no description
- isn't licensed CC BY 4.0
- has a file name that doesn't match its id
- leaves the gallery list out of date

It also lists sims set in a real place, which need the closer look below.

## What the reviewer checks

Everything in this list needs a yes:

- [ ] The title and description match what the sim does, and don't claim to predict or recreate anything.
- [ ] The text has nothing hateful, harassing, sexual, or that targets a real person.
- [ ] It isn't advertising, and has no links or contact details.
- [ ] The author has the right to share it.
- [ ] It opens, plays to the end, and gives a sensible report.
- [ ] The pull request changes only `community/`, so no code arrives with a sim.

## Sims set in a real place

These need extra care, because people may have lost family in the event:

- [ ] The description says it is a model and not a record of what happened.
- [ ] It doesn't name or depict real victims.
- [ ] It doesn't mock, or trade on, a recent disaster. Be slow to accept anything about an event from the last five years.
- [ ] It doesn't look like official guidance for a real place.

## Decisions

Approve only if every box is ticked. Otherwise ask for changes, or close the pull request and give the reason in plain words. Anyone can ask for a published sim to be removed by opening an issue. Remove it first if it may cause harm, and decide afterwards.

To remove a sim, delete its file, run `python tools/publish_sim.py rebuild`, and merge that to `main`.
