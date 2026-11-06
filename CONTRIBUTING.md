# Contributing

Thanks for helping. Code contributions are licensed under [Apache-2.0](LICENSE). Published sims are licensed under [CC BY 4.0](community/LICENSE.txt). Opening a pull request means you agree to this.

To publish a sim, you don't need any of this page. See [docs/SIM_FILES.md](docs/SIM_FILES.md).

## Setup

You need Python 3.11 or newer.

```bash
python -m pip install -r requirements.txt -r requirements-physics.txt -r requirements-dev.txt
```

`python tools/fetch_artifacts.py` downloads the 230 MB raw data. You only need it for scenarios built on real records, and the tests that need it skip without it.

## Before you open a pull request

```bash
python -m ruff check .
python -m ruff format .
SDL_VIDEODRIVER=dummy python -m pytest -q -m "not slow"
```

Windows PowerShell users set `$env:SDL_VIDEODRIVER="dummy"` first. CI runs the same checks.

## Rules for the science

- **The paper's numbers don't move.** `mind/tests/test_paper_baseline.py` guards them. If it fails, your change is wrong, not the test. New models and options are opt-in, with defaults that give identical results.
- **Never change `ETA` in `mind/config.py`, or the required keys in `contracts.py`.**
- **Pre-register.** Commit a protocol to `docs/protocols/` before running a new experiment. Report every result, whichever way it goes, and don't tune after seeing it.
- **Say "model", not "prediction".** Don't imply a hardware run: only `FakeTorino` simulation has been run.
- **Evidence stays with its scenario.** A result on one scenario id says nothing about another.

## Pull requests

- Keep each one to a single change, with tests.
- Say what changed and how you checked it. If you changed the GUI, add a screenshot.
- Every change needs one approving review.
- Add your name to `AUTHORS` in your first pull request.
