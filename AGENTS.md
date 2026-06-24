# Repository Guidelines

## Project Structure & Module Organization

This repository is intended for Python-based investment product data analysis. The repository is currently minimal, so use the following structure as it grows:

- `src/` for reusable analysis code, data loading utilities, and modeling modules.
- `notebooks/` for exploratory Jupyter notebooks.
- `tests/` for automated tests that mirror `src/` modules.
- `data/raw/` for immutable source files and `data/processed/` for generated datasets. Do not commit large or sensitive data files unless explicitly approved.
- `reports/` or `outputs/` for generated charts, tables, and analysis summaries.

## Build, Test, and Development Commands

Run all project commands inside the provided conda environment named `invest`.

- `conda run -n invest python --version` checks the active Python runtime.
- `conda run -n invest python path/to/script.py` runs an analysis script.
- `conda run -n invest pytest` runs the test suite once tests exist.
- `mamba install -n invest <package>` installs project dependencies into the correct environment.

If a dependency file is added later, prefer updating it together with the environment change, for example `environment.yml` or `requirements.txt`.

## Coding Style & Naming Conventions

Use Python with 4-space indentation and clear, typed function signatures where practical. Prefer small, reusable functions in `src/` over long notebook-only workflows. Use `snake_case` for functions, variables, modules, and file names; use `PascalCase` for classes.

Keep notebooks focused on exploration and presentation. Move stable data cleaning, feature engineering, and calculation logic into importable modules so it can be tested.

## Testing Guidelines

Use `pytest` for automated tests. Name test files `test_<module>.py` and test functions `test_<behavior>()`. Place tests under `tests/`, following the structure of `src/` where possible.

For financial calculations, include tests for boundary cases such as missing prices, zero returns, non-trading days, currency mismatches, and empty input datasets.

## Commit & Pull Request Guidelines

This repository has no existing commit history yet, so use concise, imperative commit messages such as `Add portfolio return calculation` or `Document data directory layout`.

Pull requests should include a short summary, the reason for the change, commands run for verification, and notes about any data assumptions. Include screenshots or exported charts when a change affects visual reports.

## Security & Configuration Tips

Do not commit API keys, account identifiers, brokerage exports, or proprietary datasets. Store local secrets in ignored environment files such as `.env`, and document required variable names without exposing values.
