"""Tests for the data loading and normalization layer."""

from __future__ import annotations

import pandas as pd
import pytest

from invest_analysis import data_loader as dl


def test_load_asset_series_is_year_indexed():
    series = dl.load_asset_series("sp500")
    assert series.name == "sp500"
    assert series.index.name == "year"
    assert series.index.is_monotonic_increasing  # sorted by year
    assert series.notna().all()


def test_load_asset_series_unknown_id():
    with pytest.raises(KeyError):
        dl.load_asset_series("not_an_asset")


def test_load_assets_inner_join_full_overlap():
    data = dl.load_assets(["gold", "sp500"])
    assert int(data.index.min()) == 1926
    assert int(data.index.max()) == 2025
    assert list(data.columns) == ["gold", "sp500"]


def test_load_assets_inner_join_partial_overlap():
    data = dl.load_assets(["nasdaq100", "csi300"])
    # csi300 starts in 2005, so the intersection starts there.
    assert int(data.index.min()) == 2005
    assert int(data.index.max()) == 2025


def test_load_assets_empty_list_raises():
    with pytest.raises(ValueError):
        dl.load_assets([])


def test_normalize_prices_first_row_is_one():
    data = dl.load_assets(["gold", "sp500"])
    normalized = dl.normalize_prices(data)
    assert (normalized.iloc[0] == 1.0).all()


def test_normalize_prices_rejects_empty():
    with pytest.raises(ValueError):
        dl.normalize_prices(pd.DataFrame())


def test_filter_date_range_inclusive():
    data = dl.load_assets(["gold", "sp500"])
    sliced = dl.filter_date_range(data, 2000, 2010)
    assert int(sliced.index.min()) == 2000
    assert int(sliced.index.max()) == 2010


def test_filter_date_range_empty_raises():
    data = dl.load_assets(["gold", "sp500"])
    with pytest.raises(ValueError):
        dl.filter_date_range(data, 3000, 3100)
