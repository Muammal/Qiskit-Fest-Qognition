# Workboard

Where the physics engine is planned and tracked. Anyone, person or Claude session, can pick up a task from here cold.

**[See current progress](PROGRESS.md)**: what's done, what's in progress, and who we're waiting on.

## Start here

1. Read [DESIGN.md](DESIGN.md). It takes five minutes.
2. Read [`stranded_physics/core/api.py`](../stranded_physics/core/api.py). These are the frozen interfaces.
3. Pick a task from [tasks.csv](tasks.csv) with status `todo` whose `depends` tasks are `done`.

## Claim a task

1. Put your name in `owner`, set `status` to `claimed`, and add your branch name. Commit that first, so nobody doubles up.
2. Branch from `physics/main`, named `physics/T-xxx-short-name`.
3. Follow `specs/T-xxx.md`. It lists the goal, the files you may change, and the command that proves it's done.
4. Write your gate targets and tolerances in `gates.toml` and commit them **before** you run anything against real data.
5. Set `status` to `review`. Someone else re-runs your verification command.
6. It's `done` only when `python -m stranded_physics.gates check <your gate ids>` succeeds for them.

Status values: `todo`, `claimed`, `blocked`, `review`, `done`.

## Setup

```bash
python -m pip install -r requirements.txt -r requirements-physics.txt
python -m pytest stranded_physics/core -q
python -m stranded_physics.run --seed 1 --mind quantum
```

## Everyday commands

| Command | What it does |
|---|---|
| `python -m stranded_physics.catalog` | Rebuilds [CATALOG.md](CATALOG.md) from every category |
| `python -m stranded_physics.gates run <category>` | Runs a category's gates and records verdicts |
| `python -m stranded_physics.gates check <ids>` | Exits nonzero unless those gates hold, with fresh hashes |
| `python -m stranded_physics.gates claims` | Rebuilds `CLAIMS.md` from verdicts |
| `python -m stranded_physics.pack build --scenario fake --seed 1` | Builds a pack offline |

## Add new data

1. Pick the category. Eruption sizes go in `eruption`, storm tracks in `storm`. See [CATALOG.md](CATALOG.md).
2. Add a `[[dataset]]` record to that category's `datasets.toml`, with its source, access date, hash and split.
3. Keep raw files in `artifacts/physics/raw/`, which is gitignored. Git holds the record, so anyone can re-fetch it.
4. Rerun `python -m stranded_physics.catalog`.

Decide the split before you look closely. Data marked `holdout` is refused during calibration.

## Rules that protect the claims

- Every value is a `Parameter` with its own source, or marked `assumption`.
- PASS needs a target committed before the run. No target gives `NO_TARGET`, which never counts as a pass.
- Compare with measurements, not with a paper's formula. Configured inputs never count as agreement.
- Say "verified and validated within a stated domain", never "correct".
- Only one person edits `stranded_physics/core/`. Others write a note in `changes/`.
- Before Nov 7, don't change `engine/`, `main.py`, `contracts.py` or `requirements.txt`: they carry the Nov 6 demo.
- Avoid `plan`, `risk`, `role` or `skill` in Markdown filenames, and `lib/` folders. The team's `.gitignore` hides them.
