"""Backtest a weighted asset portfolio from normalized net-value series.

Pure computation layer for the V1 portfolio analysis tool. Must not import
streamlit. Inputs and outputs are pandas objects only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# Tolerance for the "weights sum to 1" check.
_WEIGHT_TOLERANCE = 1e-6

# Rebalancing modes understood by backtest_portfolio.
_REBALANCE_MODES = ("none", "monthly", "quarterly", "annual")


def validate_weights(weights: dict[str, float]) -> None:
    """Validate that weights are non-empty, non-negative, and sum to ~1.

    Weights are decimals (0.25 means 25%). Raises ValueError on any violation.
    """
    if not weights:
        raise ValueError("weights must not be empty")

    negative = {k: v for k, v in weights.items() if v < 0}
    if negative:
        raise ValueError(f"weights must be non-negative; got {negative}")

    total = sum(weights.values())
    if abs(total - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError(f"weights must sum to 1 (got {total})")


def backtest_portfolio(
    normalized_prices: pd.DataFrame,
    weights: dict[str, float],
    rebalance: str = "none",
) -> pd.Series:
    """Compute the portfolio net-value series from normalized asset prices.

    ``normalized_prices`` must start at 1 for every column (see
    ``data_loader.normalize_prices``). ``weights`` are decimals summing to 1.

    Rebalancing modes:

    - ``none``: true buy-and-hold. Initial capital is split by target weights;
      holdings then drift with each asset's return, no further trading.
    - ``monthly`` / ``quarterly`` / ``annual``: reset to target weights at each
      calendar boundary — every month, every quarter-end (Mar/Jun/Sep/Dec), or
      every year-end (Dec) respectively. The boundary is read from the price
      index (see ``_rebalance_boundary_mask``). On a monthly PeriodIndex the
      three modes follow their true calendar boundaries and generally diverge.
      On an integer-year (annual, or mixed-frequency downsampled to annual)
      index every row is the finest available node, so all three reset every
      row and coincide.

    Returns a Series indexed like ``normalized_prices`` and starting at 1.0.
    """
    if rebalance not in _REBALANCE_MODES:
        raise ValueError(
            f"unknown rebalance mode {rebalance!r}; expected one of {_REBALANCE_MODES}"
        )

    if normalized_prices.empty:
        raise ValueError("normalized_prices must not be empty")

    validate_weights(weights)

    missing = set(weights) - set(normalized_prices.columns)
    if missing:
        raise ValueError(f"weights reference unknown assets: {missing}")

    # Order weights to match the price columns we will operate on.
    assets = [col for col in normalized_prices.columns if col in weights]
    prices = normalized_prices[assets]
    weight_vector = pd.Series({asset: weights[asset] for asset in assets})

    if rebalance == "none":
        nav = _backtest_buy_and_hold(prices, weight_vector)
    else:
        nav = _backtest_periodic_rebalance(prices, weight_vector, rebalance)

    nav.name = "portfolio"
    return nav


def _backtest_buy_and_hold(prices: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Buy at target weights once; let holdings drift with returns afterward."""
    # Units bought per asset at t0 (prices normalized to 1, so units == weight),
    # but express generally as weight / first_price for robustness.
    units = weights / prices.iloc[0]
    holdings_value = prices.mul(units, axis=1)
    return holdings_value.sum(axis=1)


def _rebalance_boundary_mask(index: pd.Index, rebalance: str) -> np.ndarray:
    """Boolean mask marking the rows at which to reset holdings to target.

    - ``monthly``: every existing period is a boundary (monthly data -> every
      month; annual data -> every year).
    - ``quarterly`` / ``annual`` on a monthly PeriodIndex: calendar quarter-ends
      (months 3/6/9/12) and year-ends (month 12) respectively.
    - any mode on a non-PeriodIndex (integer-year) index: every row, because an
      annual node is already the finest data we have — so the three periodic
      modes coincide there.
    """
    n = len(index)
    if rebalance == "monthly" or not isinstance(index, pd.PeriodIndex):
        return np.ones(n, dtype=bool)

    months = np.asarray(index.month)
    if rebalance == "quarterly":
        return months % 3 == 0
    # annual
    return months == 12


def _backtest_periodic_rebalance(
    prices: pd.DataFrame, weights: pd.Series, rebalance: str
) -> pd.Series:
    """Hold units between calendar boundaries; reset to target weights on them.

    Initial capital is bought at target weights. Holdings then drift with
    returns; on each boundary row (``_rebalance_boundary_mask``) the position is
    reset to the target weights using the current total value (a costless
    reallocation that leaves the booked nav unchanged but redirects future
    drift). When every row is a boundary this is equivalent to chaining
    per-period weighted returns.
    """
    boundary = _rebalance_boundary_mask(prices.index, rebalance)
    price_matrix = prices.to_numpy(dtype=float)
    weight_vector = weights.to_numpy(dtype=float)  # aligned to prices columns

    units = weight_vector / price_matrix[0]
    nav = np.empty(len(prices), dtype=float)
    for i in range(len(prices)):
        row = price_matrix[i]
        value = float(units @ row)
        nav[i] = value
        if boundary[i]:
            units = weight_vector * value / row

    return pd.Series(nav, index=prices.index)
