"""Backtest a weighted asset portfolio from normalized net-value series.

Pure computation layer for the V1 portfolio analysis tool. Must not import
streamlit. Inputs and outputs are pandas objects only.
"""

from __future__ import annotations

import pandas as pd


# Tolerance for the "weights sum to 1" check.
_WEIGHT_TOLERANCE = 1e-6

# Rebalancing modes understood by backtest_portfolio.
_REBALANCE_MODES = ("none", "monthly", "quarterly")


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
    - ``monthly`` / ``quarterly``: reset to target weights at the end of each
      period. NOTE: the current data is annual, so with this data both modes
      reset at every annual node and are therefore an interface-level annual
      approximation. They will take effect precisely once higher-frequency data
      is introduced (the resampling rule changes, this function does not).

    Returns a year-indexed Series starting at 1.0.
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


def _backtest_periodic_rebalance(
    prices: pd.DataFrame, weights: pd.Series, rebalance: str
) -> pd.Series:
    """Reset to target weights at each rebalance node.

    With annual data every row is a rebalance node, so this reduces to chaining
    per-period weighted returns. The per-period return of the rebalanced
    portfolio is the weight-dot-product of each asset's per-period return.
    """
    # Per-period simple returns of each asset.
    asset_returns = prices.pct_change()

    # Portfolio per-period return = sum(weight_i * asset_return_i), rebalanced.
    portfolio_returns = asset_returns.mul(weights, axis=1).sum(axis=1)

    # First period has no prior point; its return is 0 so nav starts at 1.
    portfolio_returns.iloc[0] = 0.0
    nav = (1.0 + portfolio_returns).cumprod()
    return nav
