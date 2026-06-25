"""Load processed asset CSVs, align by date, and normalize to a start value of 1.

Pure computation layer for the V1 portfolio analysis tool. Must not import
streamlit. Indices are years for now; the same interface extends to dates later.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .assets import ASSETS


# Repo root inferred from this file: src/invest_analysis/data_loader.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]


def load_asset_series(asset_id: str, repo_root: Path | str = _REPO_ROOT) -> pd.Series:
    """Load a single asset as a year-indexed Series named by its asset id."""
    if asset_id not in ASSETS:
        raise KeyError(f"unknown asset id: {asset_id!r}")

    metadata = ASSETS[asset_id]
    csv_path = Path(repo_root) / metadata["path"]
    if not csv_path.exists():
        raise FileNotFoundError(f"{asset_id}: missing CSV file {csv_path}")

    frame = pd.read_csv(csv_path)
    value_column = metadata["value_column"]
    if value_column not in frame.columns:
        raise ValueError(
            f"{asset_id}: value column {value_column!r} not found in {csv_path}"
        )

    series = frame.set_index("year")[value_column].sort_index()
    series.name = asset_id
    return series


def load_assets(
    asset_ids: list[str], repo_root: Path | str = _REPO_ROOT
) -> pd.DataFrame:
    """Load multiple assets aligned on their common years (inner join).

    Missing values are never silently filled; if the assets share no common
    years the resulting frame is empty and a ValueError is raised.
    """
    if not asset_ids:
        raise ValueError("asset_ids must not be empty")

    series = [load_asset_series(asset_id, repo_root) for asset_id in asset_ids]
    data = pd.concat(series, axis=1, join="inner")

    if data.empty:
        raise ValueError(
            f"no common dates across assets: {asset_ids}; cannot build a comparable series"
        )
    return data


def filter_date_range(
    data: pd.DataFrame, start: int | None = None, end: int | None = None
) -> pd.DataFrame:
    """Slice the (sorted, year-indexed) frame to the inclusive [start, end] range."""
    sliced = data.loc[start:end]
    if sliced.empty:
        raise ValueError(f"no data in range [{start}, {end}]")
    return sliced


def normalize_prices(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize each column to a net-value series starting at 1.

    Uses each column's first valid value as the base. Requires no missing
    values in the first row (guaranteed by the inner-join alignment).
    """
    if data.empty:
        raise ValueError("cannot normalize an empty frame")

    base = data.iloc[0]
    if base.isna().any() or (base == 0).any():
        raise ValueError("first row contains missing or zero base values; cannot normalize")

    return data.div(base)
