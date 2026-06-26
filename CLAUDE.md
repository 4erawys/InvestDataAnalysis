# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

All Python commands must run inside the conda environment `invest`. Never create a new environment or switch environments mid-task.

```bash
conda run -n invest python scripts/<script>.py   # run a script
conda run -n invest pytest                        # run tests (suite not yet created)
conda run -n invest streamlit run app.py          # run the V1 app (app.py not yet created)
mamba install -n invest <package>                 # install missing packages
```

## Architecture

This is an investment-asset data workspace evolving from one-off data scripts into a Streamlit portfolio-backtesting tool (V1). Two distinct layers exist:

### Data pipeline (built)
- `scripts/fetch_*.py` — standalone fetchers that download from external sources (DataHub, FRED, Damodaran/NYU Stern, Eastmoney, Wikipedia) into `data/raw/`, then clean into committed CSVs in `data/processed/`. Most use only the Python stdlib (`urllib`, `csv`) plus `xlrd` for Damodaran's `.xls`; `fetch_gold_monthly_price_data.py` reads a manually-downloaded WGC `.xlsx` from `data/manual_get_resources/` via pandas + `openpyxl`.
- `scripts/plot_*.py` — render static matplotlib charts into `reports/figures/`.
- Each script is self-contained with its own source-URL constants and `main()`; there is no shared fetch library. Keep them direct and reproducible.

### Analysis package (in progress)
- `src/invest_analysis/` holds **pure computation only — it must never import `streamlit`**. This algo/UI separation is a hard constraint.
- `assets.py` is the single source of truth mapping the 7 supported assets to their processed-CSV path, display name, and `value_column`. `get_asset_catalog()` returns it; `validate_asset_catalog()` checks every file exists and contains its value column.
- Planned modules (per `documents/0625_V1核心功能实施计划.md`): `data_loader.py` (load/align/normalize to start=1), `portfolio.py` (weight validation + backtest), `metrics.py` (cumulative/annualized return, volatility, max drawdown, Sharpe). `app.py` at repo root is the Streamlit UI entry that imports this package.

The V1 implementation plan and the detailed task breakdown, acceptance criteria, and module signatures live in `documents/0625_V1核心功能实施计划.md` (sourced from `documents/0625需求文档.md`). Consult it before implementing analysis modules. Note: `documents/` is gitignored.

### Design principles to preserve when extending
- **Unified strategy interface**: model buy-and-hold, periodic rebalance, dollar-cost-averaging (later), grid (later) under one signature — `price series + strategy params → one nav/holdings time series`. New strategies implement this interface so the UI layer needs no changes. This is the main extension point for the planned F8–F13 features.
- **Time-axis → recalculation**: Plotly's `rangeslider` drag is client-side only — the backend never sees the zoom event, so return/risk numbers will NOT recompute from it. The chosen approach is a date-range control (`st.slider` for start/end) that drives backend recomputation; the rangeslider is visual zoom only. Do not wire metrics to the rangeslider.
- **Visualization is Plotly** (not matplotlib — that is for the static `scripts/plot_*.py` reports only). Use `@st.cache_data` on CSV loading and nav computation as features grow; split into Streamlit `pages/` when more than one analysis view exists.

## Data conventions

- `data/raw/` is gitignored source material — **never read or commit it** for analysis tasks; treat `data/processed/` as the only input. `data/manual_get_resources/` is also gitignored: it holds source files that must be downloaded by hand (e.g. the World Gold Council `.xlsx`, which has no stable direct-download URL); a `fetch_*` script reads from it and writes the committed processed CSV.
- Processed CSVs follow a fixed schema. Annual series use `year,<value_column>,frequency,source,source_url,notes`; monthly series swap the first column for `year_month` (`YYYY-MM`): `year_month,<value_column>,frequency,source,source_url,notes`. The value column is `index_level` for all index/bond series and `price_usd_per_troy_oz` for gold.
- **Mixed frequencies**: gold is now **monthly** (WGC/LBMA, 1978→), the other six assets are still **annual**. `data_loader` aligns a selection to the *coarsest* common frequency — any annual asset forces the whole set to annual (monthly series downsampled to each year's last month), `periods_per_year=1`; only an all-monthly selection stays monthly, `periods_per_year=12` (which `metrics` uses for annualization). Never upsample/interpolate annual into monthly. Monthly vs quarterly rebalancing is still an interface-level approximation until a second monthly asset exists — keep this caveat surfaced in the UI.
- Filenames encode the range and frequency, e.g. `sp500_annual_1926_2025.csv`, `gold_price_monthly_1978_2026.csv`. Preserve this pattern when adding series.
- Bonds use the U.S. 10Y Treasury **total return index** (Damodaran) as the performance curve, not raw yields.

## Verification

No formal test suite exists yet. Verify data/plot changes by running the relevant script and checking row counts, year ranges, and head/tail rows; confirm output PNGs exist and are non-empty. Before editing, check `git status --short` so you don't clobber uncommitted work.
