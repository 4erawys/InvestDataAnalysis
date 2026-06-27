"""Tests for the portfolio backtest layer."""

from __future__ import annotations

import pandas as pd
import pytest

from invest_analysis import data_loader as dl
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


def _monthly_prices(a: list[float], b: list[float]) -> pd.DataFrame:
    """Two assets on a monthly PeriodIndex starting 2000-01."""
    index = pd.period_range("2000-01", periods=len(a), freq="M")
    return pd.DataFrame({"a": a, "b": b}, index=index)


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
    for mode in ("none", "monthly", "quarterly", "annual"):
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


def test_annual_data_periodic_modes_coincide():
    # On annual (integer-year) data every row is the finest node, so monthly,
    # quarterly and annual rebalancing all reset every row and coincide.
    prices = _sample_prices()
    weights = {"a": 0.5, "b": 0.5}
    nav_m = pf.backtest_portfolio(prices, weights, "monthly")
    nav_q = pf.backtest_portfolio(prices, weights, "quarterly")
    nav_a = pf.backtest_portfolio(prices, weights, "annual")
    pd.testing.assert_series_equal(nav_m, nav_q)
    pd.testing.assert_series_equal(nav_m, nav_a)


# --- per-boundary rebalancing on monthly data --------------------------------


def test_boundary_mask_on_monthly_index():
    index = pd.period_range("2000-01", periods=12, freq="M")
    quarterly = pf._rebalance_boundary_mask(index, "quarterly")
    annual = pf._rebalance_boundary_mask(index, "annual")
    monthly = pf._rebalance_boundary_mask(index, "monthly")
    # Quarter-ends are months 3/6/9/12 -> positions 2,5,8,11.
    assert list(index.month[quarterly]) == [3, 6, 9, 12]
    # Year-end is month 12 only.
    assert list(index.month[annual]) == [12]
    # Monthly resets every period.
    assert monthly.all()


def test_boundary_mask_on_annual_index_is_all_true():
    index = pd.Index([2000, 2001, 2002])
    for mode in ("monthly", "quarterly", "annual"):
        assert pf._rebalance_boundary_mask(index, mode).all()


def test_quarterly_differs_from_buy_and_hold():
    # a doubles in month 2 then holds; b halves in month 4. Quarter-end at
    # 2000-03 rebalances before b's drop, changing the final value.
    prices = _monthly_prices(a=[1.0, 2.0, 2.0, 2.0], b=[1.0, 1.0, 1.0, 0.5])
    weights = {"a": 0.5, "b": 0.5}
    nav_none = pf.backtest_portfolio(prices, weights, "none")
    nav_q = pf.backtest_portfolio(prices, weights, "quarterly")
    assert nav_none.iloc[-1] == pytest.approx(1.25)
    assert nav_q.iloc[-1] == pytest.approx(1.125)


def test_monthly_differs_from_quarterly():
    # a spikes in month 2 then reverts; b doubles in month 4. Monthly resets at
    # the month-2 peak (locking in the gain) while quarterly does not.
    prices = _monthly_prices(a=[1.0, 2.0, 1.0, 1.0], b=[1.0, 1.0, 1.0, 2.0])
    weights = {"a": 0.5, "b": 0.5}
    nav_m = pf.backtest_portfolio(prices, weights, "monthly")
    nav_q = pf.backtest_portfolio(prices, weights, "quarterly")
    assert nav_m.iloc[-1] == pytest.approx(1.6875)
    assert nav_q.iloc[-1] == pytest.approx(1.5)


def test_periodic_without_boundary_equals_buy_and_hold():
    # Two months only (no quarter-end), so quarterly never rebalances.
    prices = _monthly_prices(a=[1.0, 2.0], b=[1.0, 0.5])
    weights = {"a": 0.5, "b": 0.5}
    nav_none = pf.backtest_portfolio(prices, weights, "none")
    nav_q = pf.backtest_portfolio(prices, weights, "quarterly")
    pd.testing.assert_series_equal(nav_none, nav_q, check_names=False)


def test_cash_weight_one_is_flat_nav():
    # 100% cash: nav stays at 1.0 regardless of the co-selected asset's path.
    prices = pd.DataFrame(
        {"a": [1.0, 2.0, 0.5], "cash": [1.0, 1.0, 1.0]},
        index=[2000, 2001, 2002],
    )
    nav = pf.backtest_portfolio(prices, {"a": 0.0, "cash": 1.0}, "none")
    assert (nav == 1.0).all()


def test_cash_dampens_buy_and_hold():
    # 50% a (doubles) + 50% cash (flat), buy-and-hold: end value 1.5, between
    # the asset's 2.0 and cash's 1.0.
    prices = pd.DataFrame(
        {"a": [1.0, 2.0], "cash": [1.0, 1.0]},
        index=[2000, 2001],
    )
    nav = pf.backtest_portfolio(prices, {"a": 0.5, "cash": 0.5}, "none")
    assert nav.iloc[0] == pytest.approx(1.0)
    assert nav.iloc[-1] == pytest.approx(1.5)


def test_real_all_monthly_modes_diverge():
    # On a genuinely monthly selection the three periodic modes follow distinct
    # calendar boundaries and must produce different paths.
    data = dl.load_assets(["gold", "sp500", "nasdaq100"])
    normalized = dl.normalize_prices(data)
    weights = {"gold": 1 / 3, "sp500": 1 / 3, "nasdaq100": 1 / 3}
    ends = {
        mode: pf.backtest_portfolio(normalized, weights, mode).iloc[-1]
        for mode in ("monthly", "quarterly", "annual")
    }
    assert ends["monthly"] != pytest.approx(ends["quarterly"])
    assert ends["quarterly"] != pytest.approx(ends["annual"])
    assert ends["monthly"] != pytest.approx(ends["annual"])
