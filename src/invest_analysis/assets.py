"""Asset metadata catalog used by the V1 portfolio analysis UI."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path


# Synthetic (data-free) asset id. Cash has no CSV: it is a constant series that
# adopts whatever index/frequency the real assets resolve to (see data_loader).
CASH_ID = "cash"

# Display order and Chinese labels for the asset categories shown in the UI's
# grouped asset picker. Each asset carries a ``category`` matching a key here.
CATEGORY_ORDER = ("commodity", "bond", "equity", "cash")
CATEGORY_NAMES = {
    "commodity": "大宗商品",
    "bond": "债券",
    "equity": "股票ETF",
    "cash": "现金",
}


ASSETS: dict[str, dict] = {
    "gold": {
        "name": "黄金",
        "category": "commodity",
        "path": "data/processed/gold/gold_price_monthly_1978_2026.csv",
        "value_column": "price_usd_per_troy_oz",
        "unit": "USD / troy oz",
        "frequency": "monthly",
        "notes": "黄金月度美元价格（WGC / LBMA 月均价），非全收益指数；与年度资产混合时按年末月降为年度。",
    },
    "sp500": {
        "name": "标普 500",
        "category": "equity",
        "path": "data/processed/indices/sp500_monthly_1871_2026.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "monthly",
        "notes": "月度价格指数点位（Shiller / DataHub），不含股息、非全收益，月初观测；与年度资产混合时按年末月降为年度。",
    },
    "nasdaq100": {
        "name": "纳斯达克 100",
        "category": "equity",
        "path": "data/processed/indices/nasdaq100_monthly_1986_2026.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "monthly",
        "notes": "月度价格指数点位（FRED NASDAQ100），不含股息、非全收益，月末观测；1985 年缺失（自 1986-01 起）。",
    },
    "sse_composite": {
        "name": "上证指数",
        "category": "equity",
        "path": "data/processed/indices/sse_composite_annual_1990_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末指数点位。",
    },
    "csi300": {
        "name": "沪深 300",
        "category": "equity",
        "path": "data/processed/indices/csi300_annual_2005_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末指数点位。",
    },
    "us_10y_treasury_total_return": {
        "name": "美国 10 年期国债总回报指数",
        "category": "bond",
        "path": "data/processed/bonds/us_10y_treasury_total_return_index_annual_1928_2025.csv",
        "value_column": "index_level",
        "unit": "total return index",
        "frequency": "annual",
        "notes": "10 年期美国国债年度总回报指数。",
    },
    "china_treasury_bond_index": {
        "name": "中国国债指数",
        "category": "bond",
        "path": "data/processed/bonds/china_treasury_bond_index_annual_2003_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末国债指数点位。",
    },
    CASH_ID: {
        "name": "现金",
        "category": "cash",
        "synthetic": True,
        "unit": "constant",
        "notes": "现金（什么都不买）：0% 回报、0 波动的合成资产，不需要数据；"
        "频率随其余资产，需至少搭配一个真实资产以确定时间轴。",
    },
}


def is_synthetic(asset_id: str) -> bool:
    """Whether an asset id is a data-free synthetic asset (e.g. cash)."""
    return bool(ASSETS.get(asset_id, {}).get("synthetic", False))


def get_asset_catalog() -> dict[str, dict]:
    """Return a defensive copy of the configured V1 asset catalog."""
    return deepcopy(ASSETS)


def get_grouped_catalog() -> list[tuple[str, list[tuple[str, dict]]]]:
    """Catalog grouped by category in display order for the UI asset picker.

    Returns ``[(category_label, [(asset_id, metadata), ...]), ...]`` following
    ``CATEGORY_ORDER``; within a category, assets keep their declared order.
    Empty categories are omitted.
    """
    catalog = get_asset_catalog()
    groups: list[tuple[str, list[tuple[str, dict]]]] = []
    for category in CATEGORY_ORDER:
        members = [
            (asset_id, metadata)
            for asset_id, metadata in catalog.items()
            if metadata.get("category") == category
        ]
        if members:
            groups.append((CATEGORY_NAMES[category], members))
    return groups


def validate_asset_catalog(repo_root: Path | str = ".") -> None:
    """Validate that every asset file exists and contains its value column.

    Synthetic assets (cash) carry no CSV and are skipped.
    """
    root = Path(repo_root)

    for asset_id, metadata in ASSETS.items():
        if is_synthetic(asset_id):
            continue
        csv_path = root / metadata["path"]
        if not csv_path.exists():
            raise FileNotFoundError(f"{asset_id}: missing CSV file {csv_path}")

        header = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        value_column = metadata["value_column"]
        if value_column not in header:
            raise ValueError(
                f"{asset_id}: value column {value_column!r} not found in {csv_path}"
            )
