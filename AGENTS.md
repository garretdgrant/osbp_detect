# Repository Guidelines

## Project Structure & Module Organization

Core entry points live at the repository root: `run.py` exposes the CLI detector and `gui.py` provides the desktop client. Shared logic is split under `src/`: `fast5_utils.py` wraps HDF5/ONT helpers, while `signal_utils.py` hosts the event parsing heuristics. Visual aids are under `img/`, dependency pins sit in `requirements.txt`, and platform docs are grouped under `docs/` (see `docs/instructions.md` for macOS setup).

## Build, Test, and Development Commands

Use the system Python 3 that matches `pip3`. Install deps once per clone with `python3 -m pip install -r requirements.txt`. Run the GUI during development via `python3 gui.py`. The CLI accepts FAST5 inputs and channel filters: `python3 run.py -i path/to/file.fast5 -r 1-32 -b 4,8 > detections.tsv`.

## Coding Style & Naming Conventions

Follow standard PEP 8 with 4-space indentation, snake_case functions, PascalCase classes (if introduced), and uppercase module-scoped constants (e.g., threshold defaults). Keep signal-processing helpers pure where possible and move any file I/O to `fast5_utils`. Annotate new public functions with docstrings describing expected sampling rates and channel formats. Prefer descriptive variable names (`open_current`, `residual_current`) to align with the existing terminology in `README.md`.

## Testing Guidelines

Automated tests are not yet committed, so add a `tests/` package that uses `pytest` (already compatible with the current structure). Focus on deterministic units: mock HDF5 handles when exercising `fast5_utils`, and feed synthetic numpy traces into `signal_utils` to verify baseline detection, filtering, and event windowing. When validating end-to-end changes, run `python3 run.py` against a short public FAST5 and compare TSV counts.

## Commit & Pull Request Guidelines

Recent history favors short, imperative commits such as `update baseline detection method`; continue this tense and keep subjects under ~60 characters. Each PR should explain the motivation, list key file-level changes, and note any CLI or GUI behavior updates. Reference issue IDs or external tickets when applicable, attach before/after screenshots for GUI tweaks, and include sample command lines or TSV snippets that reviewers can reproduce.

## Data & Configuration Notes

FAST5 files may contain sensitive metadata. Store credentials or proprietary datasets outside the repo and load paths via environment variables or `.env` files excluded by `.gitignore`. Parameter defaults (channel ranges, thresholds) belong near the top of `run.py` so downstream agents can override them without editing shared modules.
