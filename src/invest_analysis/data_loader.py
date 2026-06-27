"""Load processed asset CSVs, align them, and normalize to a start value of 1.

Pure computation layer for the V1 portfolio analysis tool. Must not import
streamlit.

Frequency-aware: an asset CSV is annual when it has a ``year`` column (integer
year index) or monthly when it has a ``year_month`` column (``YYYY-MM``, parsed
to a monthly PeriodIndex). When assets of different frequencies are combined we
align to the *coarsest* common frequency — i.e. any annual asset forces the whole
set to annual, downsampling monthly series to each year's last available month.
No upsampling/interpolation is ever fabricated. Once every asset is monthly the
combined frame stays monthly with no code change.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .assets import ASSETS, is_synthetic

# Observations per calendar year for each supported frequency.
PERIODS_PER_YEAR = {"annual": 1, "monthly": 12}


def _resolve_repo_root() -> Path:
    """Locate the directory that contains ``data/processed/``.

    In a normal checkout this file lives at src/invest_analysis/data_loader.py,
    so the repo root is parents[2]. When frozen by PyInstaller the source tree
    is gone; the bundled data is unpacked under ``sys._MEIPASS`` (we add it via
    ``--add-data data/processed:data/processed``), so that dir is the root.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


# Directory containing data/processed/; differs between source and frozen runs.
_REPO_ROOT = _resolve_repo_root()


def _downsample_to_annual(series: pd.Series) -> pd.Series:
    """Reduce a monthly (PeriodIndex) series to one integer-year-indexed point.

    Each year is represented by its last available month, mirroring how the
    annual index/bond series carry year-end levels.
    """
    annual = series.groupby(series.index.year).last()
    annual.index.name = "year"
    annual.name = series.name
    return annual


def load_asset_series(
    asset_id: str,
    repo_root: Path | str = _REPO_ROOT,
    target_freq: str | None = None,
) -> pd.Series:
    """Load a single asset as a Series named by its asset id.

    The index is an integer year (annual CSV) or a monthly PeriodIndex (monthly
    CSV). When ``target_freq="annual"`` a monthly series is downsampled to annual
    so it can be aligned with annual assets.
    """
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

    if "year_month" in frame.columns:
        index = pd.PeriodIndex(frame["year_month"], freq="M")
        series = pd.Series(frame[value_column].to_numpy(), index=index).sort_index()
    elif "year" in frame.columns:
        series = frame.set_index("year")[value_column].sort_index()
    else:
        raise ValueError(
            f"{asset_id}: CSV must have a 'year' or 'year_month' column ({csv_path})"
        )

    series.name = asset_id

    if target_freq == "annual" and isinstance(series.index, pd.PeriodIndex):
        series = _downsample_to_annual(series)
    return series


def load_assets(
    asset_ids: list[str], repo_root: Path | str = _REPO_ROOT
) -> pd.DataFrame:
    """Load multiple assets aligned on their common periods (inner join).

    Mixed frequencies are resolved to the coarsest common frequency: any annual
    asset forces the whole set to annual (monthly series are downsampled). If the
    assets share no common periods the result is empty and a ValueError is raised.

    Synthetic assets (cash) carry no CSV: they are frequency-neutral and are
    added as a constant column over the real assets' resolved index. Cash must be
    combined with at least one real asset, which supplies the time axis.
    """
    if not asset_ids:
        raise ValueError("asset_ids must not be empty")

    unknown = [aid for aid in asset_ids if aid not in ASSETS]
    if unknown:
        raise KeyError(f"unknown asset ids: {unknown}")

    synthetic_ids = [aid for aid in asset_ids if is_synthetic(aid)]
    real_ids = [aid for aid in asset_ids if not is_synthetic(aid)]

    if not real_ids:
        raise ValueError(
            "synthetic assets (cash) need at least one real asset to provide a "
            f"time axis; got only {synthetic_ids}"
        )

    # Cash is frequency-neutral: resolve the frequency from real assets only.
    frequencies = {ASSETS[aid]["frequency"] for aid in real_ids}
    resolved = "annual" if "annual" in frequencies else "monthly"

    series = [
        load_asset_series(aid, repo_root, target_freq=resolved) for aid in real_ids
    ]
    data = pd.concat(series, axis=1, join="inner")

    if data.empty:
        raise ValueError(
            f"no common dates across assets: {real_ids}; cannot build a comparable series"
        )

    # A constant column normalizes to a flat 1.0 nav (0% return, 0 volatility).
    for aid in synthetic_ids:
        data[aid] = 1.0

    # Restore the caller's column order so weights line up intuitively.
    return data[asset_ids]


def infer_periods_per_year(data: pd.DataFrame | pd.Series) -> int:
    """Return observations-per-year implied by the frame's index.

    Monthly PeriodIndex -> 12; integer-year (annual) index -> 1. Drives the
    annualization in ``metrics`` so callers need not track frequency separately.
    """
    index = data.index
    if isinstance(index, pd.PeriodIndex) and index.freqstr.startswith("M"):
        return PERIODS_PER_YEAR["monthly"]
    return PERIODS_PER_YEAR["annual"]


def filter_date_range(
    data: pd.DataFrame, start: int | None = None, end: int | None = None
) -> pd.DataFrame:
    """Slice the (sorted) frame to the inclusive [start, end] **year** range.

    Frequency-agnostic: integer-year indices compare directly; a monthly
    PeriodIndex compares on its ``.year``, so the whole calendar year is kept.
    """
    index = data.index
    years = index.year if isinstance(index, pd.PeriodIndex) else np.asarray(index)

    mask = np.ones(len(data), dtype=bool)
    if start is not None:
        mask &= years >= start
    if end is not None:
        mask &= years <= end

    sliced = data[mask]
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
