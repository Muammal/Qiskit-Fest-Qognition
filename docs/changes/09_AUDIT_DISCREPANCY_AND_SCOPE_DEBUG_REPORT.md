# Agentic Engineering Log 09: Audit, Discrepancy & Scope Debug Report

## 1. Audit Context & Directive
Following the user request:
> *"readme mentions references yet references is gitignored, debug codebase entirely for similar issues, report anything out of the current scope of the project"*

An end-to-end audit was conducted across the git index, directory trees, path calculations, package imports, and file scopes.

---

## 2. Issues Discovered & Programmatic Resolutions

### Issue 1: `README.md` and `references/` Discrepancy
- **Discovery**: `README.md` listed `references/` in its directory tree and claimed:
  *"All historical research notebooks and exhaustive mathematical documentation are preserved in references/."*
  However:
  1. `references/` was explicitly gitignored in `.gitignore`. Anyone cloning the repository would receive a broken or missing directory.
  2. The notebooks stored in `references/notebooks/` were **not** research notebooks for this Quantum RL exploit hunter; they were legacy molecular chemistry tutorial labs from an external competition.
  3. The core technical document `QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md` (which details the 320x speedup mechanics, Grover oracle math, and fast statevector Gram matrix derivations) had been moved into `references/docs/` and was therefore also gitignored and invisible on GitHub!
- **Resolution**:
  - Restored `QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md` to a tracked, official documentation folder: `docs/QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md`.
  - Updated `README.md` to link directly to `docs/QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md` and `changes/` using portable relative links.
  - Removed `references/` from the tracked tree in `README.md`.
  - Added `references/README.md` clarifying that `references/` is an excluded local archive for legacy tutorial materials.

### Issue 2: Committed Python Bytecode (`__pycache__/*.pyc`) in Git Tracking
- **Discovery**: Running `git ls-files` revealed 9 compiled Python bytecode files (`.pyc`) committed into git:
  - `run/__pycache__/*.cpython-313.pyc` (8 files)
  - `ui/__pycache__/server.cpython-313.pyc` (1 file)
- **Root Cause**: These files were staged into git tracking before `.gitignore` was configured.
- **Resolution**: Executed `git rm -r --cached run/__pycache__ ui/__pycache__` to purge bytecode from git tracking without affecting local execution.

### Issue 3: Packaging & Relative Import Failure in `run/`
- **Discovery**: Running `python -c "import run"` failed with:
  `ModuleNotFoundError: No module named 'common' in run/run_mario.py`.
- **Root Cause**: When `run/` was imported as a package from outside its folder, `run/run_mario.py` attempted `from common import ...` instead of package-relative imports (`from .common import ...`).
- **Resolution**: Implemented dual-mode import fallbacks across all runner modules (`run_mario.py`, `run_doom.py`, `run_chess.py`, `run_sudoku.py`, `run_blackjack.py`, `run_game.py`):
  ```python
  try:
      from .common import IterationLog, QuantumTerminalHUD
  except ImportError:
      from common import IterationLog, QuantumTerminalHUD
  ```
  And added `RUN_DIR` to `sys.path`. All 19 modules across the codebase now import with zero errors.

### Issue 4: `PROJECT_ROOT` Path Miscalculation in `config.py`
- **Discovery**: In `config.py`, line 13 calculated:
  `PROJECT_ROOT = os.path.abspath(os.path.join(PACKAGE_DIR, ".."))`.
  Since `config.py` was elevated to the repository root (`QWC/`), `PACKAGE_DIR` was `QWC/`, causing `PROJECT_ROOT` to point to the parent `OneDrive\Desktop` directory!
- **Resolution**: Fixed in `config.py`:
  ```python
  PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
  PACKAGE_DIR = PROJECT_ROOT
  DATA_DIR = os.path.join(PROJECT_ROOT, "data")
  ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")
  RUNS_DIR = os.path.join(PROJECT_ROOT, "runs")
  ```

### Issue 5: Stale Ghost Paths (`qiskit_exploit_hunter`)
- **Discovery**: 12 files contained dead references appending the non-existent folder `qiskit_exploit_hunter` to `sys.path`.
- **Resolution**: Removed all stale references across `main.py`, `ui/server.py`, `run/common.py`, and runner modules.

### Issue 6: Tracked Runtime Artifact `_vizdoom.ini`
- **Discovery**: `_vizdoom.ini` was tracked by git, causing `git status` to flag it as modified after every ViZDoom run.
- **Resolution**: Removed from git index via `git rm --cached _vizdoom.ini` and ensured `.gitignore` ignores it.

### Issue 7: Hardcoded Machine-Specific Windows Paths in Markdown
- **Discovery**: `README.md` contained local Windows paths (`file:///c:/Users/lenovo/...`).
- **Resolution**: Converted all links to portable relative markdown links (e.g. `docs/...`, `changes/...`, `artifacts/...`).

---

## 3. Inventory of Out-of-Scope Files in the Workspace

The workspace contains 6 Jupyter notebooks that are **completely out of scope** of the Quantum RL & Game Exploit Detection Framework:

| File Path | Original Title / Source | Actual Content & Focus | Status / Verdict |
| :--- | :--- | :--- | :--- |
| `references/notebooks/01_sample_then_diagonalize(1) (1).ipynb` | *Sample, Then Diagonalize* (IBM Quantum Fall Fest) | Quantum chemistry Hamiltonian diagonalization via Sample-then-Diagonalize (SQD). | **Out of Scope**: Chemistry challenge lab, unrelated to game RL or exploit detection. |
| `references/notebooks/02_molecules_as_bitstrings.ipynb` | *Molecules as Bitstrings* (IBM Quantum Fall Fest) | Electronic orbitals, Hartree-Fock determinants, and bitstring mappings. | **Out of Scope**: Chemistry challenge lab. |
| `references/notebooks/03_the_full_sqd_pipeline.ipynb` | *The Full SQD Pipeline* (IBM Quantum Fall Fest) | Full molecular active space SQD pipeline for chemistry. | **Out of Scope**: Chemistry challenge lab. |
| `references/notebooks/challenge_1_tutorial.ipynb` | *Ground-State Energy of a Molecule with VQE* (BasQ Fall Fest 2026) | VQE calculation of $H_2$ hydrogen molecule ground-state energy. | **Out of Scope**: Chemistry challenge tutorial. |
| `references/notebooks/challenge_2_tutorial.ipynb` | *BasQ Fall Fest 2026 Challenge 2* | Quantum challenge tutorial lab. | **Out of Scope**: Competition tutorial. |
| `references/notebooks/challenge_3_tutorial.ipynb` | *BasQ Fall Fest 2026 Challenge 3* | Quantum challenge tutorial lab. | **Out of Scope**: Competition tutorial. |

### Disposition:
These 6 notebooks are kept locally in `references/notebooks/` and strictly ignored in `.gitignore`. They are excluded from the project's source tree and `README.md`.

