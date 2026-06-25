"""Tests for the portfolio backtest layer."""

from __future__ import annotations

import pandas as pd
import pytest

from invest_analysis import portfolio as pf


def _sample_prices() -> pd.DataFrame:
    """Two assets normalized to start at 1, with known per-period returns."""
    return pd.DataFrame(
        {
            "a": [1.0, 1.10, 1.21],  # +10% each period
            "b": [1.0, 1.00, 1.00],  # flat
        },
        index=[2000, 2001, 2002],
    )


# --- weight validation -------------------------------------------------------


def test_validate_weights_ok():
    pf.validate_weights({"a": 0.25, "b": 0.75})  # no raise


def test_validate_weights_sum_not_one():
    with pytest.raises(ValueError):
        pf.validate_weights({"a": 0.3, "b": 0.3})


def test_validate_weights_negative():
    with pytest.raises(ValueError):
        pf.validate_weights({"a": 1.2, "b": -0.2})


def test_validate_weights_empty():
    with pytest.raises(ValueError):
        pf.validate_weights({})


# --- backtest ----------------------------------------------------------------


def test_single_asset_equals_normalized_series():
    prices = _sample_prices()
    nav = pf.backtest_portfolio(prices, {"a": 1.0}, "none")
    pd.testing.assert_series_equal(
        nav, prices["a"], check_names=False
    )


def test_buy_and_hold_known_values():
    # 50/50 of a(+10%/period) and b(flat), buy-and-hold.
    # t0: 0.5*1 + 0.5*1 = 1.0
    # t1: 0.5*1.10 + 0.5*1.00 = 1.05
    # t2: 0.5*1.21 + 0.5*1.00 = 1.105
    prices = _sample_prices()
    nav = pf.backtest_portfolio(prices, {"a": 0.5, "b": 0.5}, "none")
    assert nav.iloc[0] == pytest.approx(1.0)
    assert nav.iloc[1] == pytest.approx(1.05)
    assert nav.iloc[2] == pytest.approx(1.105)


def test_nav_starts_at_one():
    prices = _sample_prices()
    for mode in ("none", "monthly", "quarterly"):
        nav = pf.backtest_portfolio(prices, {"a": 0.5, "b": 0.5}, mode)
        assert nav.iloc[0] == pytest.approx(1.0)


def test_unknown_rebalance_mode():
    prices = _sample_prices()
    with pytest.raises(ValueError):
        pf.backtest_portfolio(prices, {"a": 1.0}, "weekly")


def test_weights_reference_unknown_asset():
    prices = _sample_prices()
    with pytest.raises(ValueError):
        pf.backtest_portfolio(prices, {"a": 0.5, "z": 0.5}, "none")


def test_annual_data_monthly_equals_quarterly():
    # On annual data every row is a rebalance node, so monthly and quarterly
    # reduce to the same annual-node approximation.
    prices = _sample_prices()
    weights = {"a": 0.5, "b": 0.5}
    nav_m = pf.backtest_portfolio(prices, weights, "monthly")
    nav_q = pf.backtest_portfolio(prices, weights, "quarterly")
    pd.testing.assert_series_equal(nav_m, nav_q)
