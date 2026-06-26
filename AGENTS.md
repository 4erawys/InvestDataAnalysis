# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python investment data workspace. The current layout is:

- `scripts/` for one-off data fetchers and plot generators.
- `data/raw/` for downloaded source files. This directory is ignored by Git.
- `data/processed/` for cleaned, analysis-ready CSVs that should be versioned.
- `reports/figures/` for generated charts.
- `AGENTS.md` for contributor guidance and repo conventions.

Keep new reusable code in `scripts/` only if it is small and task-specific. If shared logic grows, move it into a proper module.

## Build, Test, and Development Commands

Run everything inside the `invest` conda environment.

- `conda run -n invest python scripts/fetch_gold_monthly_price_data.py` builds the monthly gold series from the manually-downloaded WGC `.xlsx`.
- `conda run -n invest python scripts/fetch_index_data.py` builds U.S. and China equity index datasets.
- `conda run -n invest python scripts/fetch_china_index_data.py` fetches Shanghai and CSI 300 data.
- `conda run -n invest python scripts/fetch_bond_data.py` fetches U.S. and China bond series.
- `conda run -n invest python scripts/plot_all_asset_curves.py` renders the combined figure.
- `conda run -n invest python scripts/plot_gold_price_trend.py` renders the gold-only figure.

Install missing packages with `mamba install -n invest <package>`.

## Coding Style & Naming Conventions

Use Python 4-space indentation, `snake_case` for files/functions/variables, and `PascalCase` for classes. Prefer explicit column names in CSVs and keep filenames descriptive, for example `sp500_annual_1926_2025.csv`.

Keep scripts direct and reproducible. Avoid new abstractions unless they will be reused by multiple scripts.

## Data Handling

Treat `data/raw/` as source material and `data/processed/` as the committed output. Raw downloads may be large, licensed, or noisy; do not add them to Git unless they are required for reproducibility.

When adding a new series, preserve the existing CSV pattern. Annual series:

```csv
year,<value_column>,frequency,source,source_url,notes
```

Monthly series swap the first column for `year_month` (`YYYY-MM`):

```csv
year_month,<value_column>,frequency,source,source_url,notes
```

The loader aligns mixed-frequency selections to the coarsest common frequency (any annual asset downsamples monthly ones to year-end). Manually-downloaded sources (e.g. the WGC `.xlsx`) go in the gitignored `data/manual_get_resources/`.

## Testing & Verification

There is no formal test suite yet. Verify changes by running the relevant script and checking row counts, year ranges, and representative head/tail rows. For plots, confirm the output PNG exists and is non-empty.

## Commit & Pull Request Guidelines

Use short, imperative commit messages such as `Add gold trend plot` or `Fetch bond index data`. Pull requests should describe the data source, the date range covered, and any caveats about series definitions.

## Security & Configuration Tips

Do not commit API keys, account identifiers, or proprietary datasets. Keep local-only settings in ignored files such as `.env`. Use the existing `invest` environment for all runs; do not switch environments mid-task.
