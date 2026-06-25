"""Risk and return metrics computed from a portfolio net-value series.

Pure computation layer for the V1 portfolio analysis tool. Must not import
streamlit. Inputs are pandas Series (nav starting at 1.0); outputs are floats.

Annual data uses ``periods_per_year=1``. The same functions extend to monthly
or daily data by passing the matching periods-per-year (12, 252, ...).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _validate_nav(nav: pd.Series, min_length: int = 2) -> None:
    """Ensure the nav series is long enough and free of invalid values."""
    if len(nav) < min_length:
        raise ValueError(
            f"nav must have at least {min_length} points; got {len(nav)}"
        )
    if nav.isna().any():
        raise ValueError("nav contains missing values")
    if (nav <= 0).any():
        raise ValueError("nav must be strictly positive")


def cumulative_return(nav: pd.Series) -> float:
    """Total return over the whole series: last / first - 1."""
    _validate_nav(nav)
    return float(nav.iloc[-1] / nav.iloc[0] - 1.0)


def annualized_return(nav: pd.Series, periods_per_year: int = 1) -> float:
    """Geometric annualized return (CAGR) from the nav series.

    The number of elapsed periods is ``len(nav) - 1`` (intervals between
    observations), so years = (len - 1) / periods_per_year.
    """
    _validate_nav(nav)
    n_periods = len(nav) - 1
    years = n_periods / periods_per_year
    if years <= 0:
        raise ValueError("series spans less than one period; cannot annualize")
    total_growth = nav.iloc[-1] / nav.iloc[0]
    return float(total_growth ** (1.0 / years) - 1.0)


def annualized_volatility(nav: pd.Series, periods_per_year: int = 1) -> float:
    """Annualized volatility of per-period simple returns (sample std)."""
    _validate_nav(nav)
    returns = nav.pct_change().dropna()
    if len(returns) < 2:
        raise ValueError("need at least 2 returns to compute volatility")
    # Sample standard deviation (ddof=1), scaled by sqrt(periods_per_year).
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(nav: pd.Series) -> float:
    """Maximum drawdown on the nav curve, as a non-positive fraction.

    Returns 0.0 for a monotonically non-decreasing series. A trough that is
    20% below its prior peak yields -0.20.
    """
    _validate_nav(nav)
    running_peak = nav.cummax()
    drawdown = nav / running_peak - 1.0
    return float(drawdown.min())


def sharpe_ratio(
    nav: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 1,
) -> float:
    """Annualized Sharpe ratio.

    ``risk_free_rate`` is the annual risk-free rate; it is converted to the
    per-period rate before subtracting from each period's return. Returns NaN
    when volatility is zero (no meaningful risk-adjusted return).
    """
    _validate_nav(nav)
    returns = nav.pct_change().dropna()
    if len(returns) < 2:
        raise ValueError("need at least 2 returns to compute Sharpe ratio")

    per_period_rf = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess = returns - per_period_rf
    std = excess.std(ddof=1)
    if std == 0:
        return float("nan")
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def calculate_metrics(nav: pd.Series, periods_per_year: int = 1) -> dict[str, float]:
    """Compute the V1 metric bundle from a portfolio nav series."""
    return {
        "cumulative_return": cumulative_return(nav),
        "annualized_return": annualized_return(nav, periods_per_year),
        "annualized_volatility": annualized_volatility(nav, periods_per_year),
        "max_drawdown": max_drawdown(nav),
        "sharpe_ratio": sharpe_ratio(nav, periods_per_year=periods_per_year),
    }
