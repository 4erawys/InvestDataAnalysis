"""Tests for the data loading and normalization layer."""

from __future__ import annotations

import pandas as pd
import pytest

from invest_analysis import data_loader as dl


def test_load_asset_series_is_year_indexed():
    series = dl.load_asset_series("sse_composite")
    assert series.name == "sse_composite"
    assert series.index.name == "year"
    assert series.index.is_monotonic_increasing  # sorted by year
    assert series.notna().all()


def test_load_asset_series_unknown_id():
    with pytest.raises(KeyError):
        dl.load_asset_series("not_an_asset")


def test_load_monthly_asset_is_period_indexed():
    series = dl.load_asset_series("gold")
    assert series.name == "gold"
    assert isinstance(series.index, pd.PeriodIndex)
    assert series.index.freqstr.startswith("M")
    assert series.index.is_monotonic_increasing
    assert series.index.min().year == 1978


def test_load_asset_series_downsamples_monthly_to_annual():
    series = dl.load_asset_series("gold", target_freq="annual")
    # Now integer-year indexed, one point per year.
    assert series.index.name == "year"
    assert not isinstance(series.index, pd.PeriodIndex)
    assert series.index.is_unique
    assert int(series.index.min()) == 1978


def test_load_assets_pure_annual_overlap():
    data = dl.load_assets(["sse_composite", "us_10y_treasury_total_return"])
    # sse starts 1990, treasury 1928 -> intersection starts 1990.
    assert int(data.index.min()) == 1990
    assert int(data.index.max()) == 2025
    assert list(data.columns) == ["sse_composite", "us_10y_treasury_total_return"]


def test_load_assets_partial_overlap():
    data = dl.load_assets(["csi300", "sse_composite"])
    # csi300 starts in 2005, so the intersection starts there.
    assert int(data.index.min()) == 2005
    assert int(data.index.max()) == 2025


def test_load_assets_mixed_frequency_resolves_to_annual():
    data = dl.load_assets(["gold", "us_10y_treasury_total_return"])
    # Monthly gold is downsampled to annual; intersection starts at gold's 1978.
    assert not isinstance(data.index, pd.PeriodIndex)
    assert int(data.index.min()) == 1978
    assert int(data.index.max()) == 2025
    assert list(data.columns) == ["gold", "us_10y_treasury_total_return"]


def test_load_assets_all_monthly_stays_monthly():
    data = dl.load_assets(["gold"])
    assert isinstance(data.index, pd.PeriodIndex)
    assert dl.infer_periods_per_year(data) == 12


def test_load_assets_two_monthly_indices_stay_monthly():
    data = dl.load_assets(["sp500", "nasdaq100"])
    # Both monthly; Nasdaq-100 starts 1986-01, so the intersection starts there.
    assert isinstance(data.index, pd.PeriodIndex)
    assert dl.infer_periods_per_year(data) == 12
    assert data.index.min().year == 1986
    assert list(data.columns) == ["sp500", "nasdaq100"]


def test_infer_periods_per_year():
    monthly = dl.load_assets(["gold"])
    annual = dl.load_assets(["gold", "us_10y_treasury_total_return"])
    assert dl.infer_periods_per_year(monthly) == 12
    assert dl.infer_periods_per_year(annual) == 1


def test_load_assets_empty_list_raises():
    with pytest.raises(ValueError):
        dl.load_assets([])


# --- cash (synthetic asset) --------------------------------------------------


def test_cash_is_constant_and_frequency_neutral_on_monthly():
    data = dl.load_assets(["gold", "cash"])
    # Monthly gold keeps the selection monthly; cash does not drag it to annual.
    assert isinstance(data.index, pd.PeriodIndex)
    assert dl.infer_periods_per_year(data) == 12
    assert list(data.columns) == ["gold", "cash"]
    assert (data["cash"] == 1.0).all()


def test_cash_adopts_annual_index_with_annual_asset():
    data = dl.load_assets(["csi300", "cash"])
    assert not isinstance(data.index, pd.PeriodIndex)
    assert dl.infer_periods_per_year(data) == 1
    assert (data["cash"] == 1.0).all()
    # Cash spans exactly the real asset's index.
    assert len(data) == len(dl.load_assets(["csi300"]))


def test_cash_preserves_caller_column_order():
    data = dl.load_assets(["cash", "gold"])
    assert list(data.columns) == ["cash", "gold"]


def test_cash_only_raises():
    with pytest.raises(ValueError):
        dl.load_assets(["cash"])


def test_cash_normalizes_to_flat_one():
    normalized = dl.normalize_prices(dl.load_assets(["gold", "cash"]))
    assert (normalized["cash"] == 1.0).all()


def test_normalize_prices_first_row_is_one():
    data = dl.load_assets(["gold", "sp500"])
    normalized = dl.normalize_prices(data)
    assert (normalized.iloc[0] == 1.0).all()


def test_normalize_prices_rejects_empty():
    with pytest.raises(ValueError):
        dl.normalize_prices(pd.DataFrame())


def test_filter_date_range_inclusive():
    data = dl.load_assets(["gold", "us_10y_treasury_total_return"])  # resolves to annual
    sliced = dl.filter_date_range(data, 2000, 2010)
    assert int(sliced.index.min()) == 2000
    assert int(sliced.index.max()) == 2010


def test_filter_date_range_monthly_keeps_whole_years():
    data = dl.load_assets(["gold"])  # monthly PeriodIndex
    sliced = dl.filter_date_range(data, 2000, 2000)
    assert isinstance(sliced.index, pd.PeriodIndex)
    assert (sliced.index.year == 2000).all()
    assert len(sliced) == 12


def test_filter_date_range_empty_raises():
    data = dl.load_assets(["gold", "sp500"])
    with pytest.raises(ValueError):
        dl.filter_date_range(data, 3000, 3100)
