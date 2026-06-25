"""Tests for the risk/return metrics layer."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from invest_analysis import metrics as m


def test_cumulative_return():
    assert m.cumulative_return(pd.Series([1.0, 0.8, 1.2])) == pytest.approx(0.2)


def test_max_drawdown_monotonic_is_zero():
    assert m.max_drawdown(pd.Series([1.0, 1.1, 1.3, 1.5])) == pytest.approx(0.0)


def test_max_drawdown_known_value():
    assert m.max_drawdown(pd.Series([1.0, 0.8, 1.2])) == pytest.approx(-0.2)


def test_annualized_return_known_value():
    # 4 points => 3 annual periods; total growth 1.331 = 1.1**3 => CAGR 10%.
    nav = pd.Series([1.0, 1.1, 1.21, 1.331])
    assert m.annualized_return(nav, periods_per_year=1) == pytest.approx(0.10)


def test_annualized_volatility_constant_returns_is_zero():
    # Constant +10% each period => zero volatility.
    nav = pd.Series([1.0, 1.1, 1.21, 1.331])
    assert m.annualized_volatility(nav) == pytest.approx(0.0, abs=1e-12)


def test_sharpe_ratio_nan_when_zero_volatility():
    # A flat nav has zero-volatility returns, so Sharpe is undefined (NaN).
    nav = pd.Series([1.0, 1.0, 1.0, 1.0])
    assert math.isnan(m.sharpe_ratio(nav))


def test_calculate_metrics_keys():
    metrics = m.calculate_metrics(pd.Series([1.0, 0.8, 1.2]))
    assert set(metrics) == {
        "cumulative_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "sharpe_ratio",
    }


def test_short_series_raises():
    with pytest.raises(ValueError):
        m.cumulative_return(pd.Series([1.0]))


def test_non_positive_nav_raises():
    with pytest.raises(ValueError):
        m.max_drawdown(pd.Series([1.0, 0.0, 1.2]))
