"""Asset metadata catalog used by the V1 portfolio analysis UI."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path


ASSETS: dict[str, dict[str, str]] = {
    "gold": {
        "name": "黄金",
        "path": "data/processed/gold/gold_price_monthly_1978_2026.csv",
        "value_column": "price_usd_per_troy_oz",
        "unit": "USD / troy oz",
        "frequency": "monthly",
        "notes": "黄金月度美元价格（WGC / LBMA 月均价），非全收益指数；与年度资产混合时按年末月降为年度。",
    },
    "sp500": {
        "name": "标普 500",
        "path": "data/processed/indices/sp500_monthly_1871_2026.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "monthly",
        "notes": "月度价格指数点位（Shiller / DataHub），不含股息、非全收益，月初观测；与年度资产混合时按年末月降为年度。",
    },
    "nasdaq100": {
        "name": "纳斯达克 100",
        "path": "data/processed/indices/nasdaq100_monthly_1986_2026.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "monthly",
        "notes": "月度价格指数点位（FRED NASDAQ100），不含股息、非全收益，月末观测；1985 年缺失（自 1986-01 起）。",
    },
    "sse_composite": {
        "name": "上证指数",
        "path": "data/processed/indices/sse_composite_annual_1990_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末指数点位。",
    },
    "csi300": {
        "name": "沪深 300",
        "path": "data/processed/indices/csi300_annual_2005_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末指数点位。",
    },
    "us_10y_treasury_total_return": {
        "name": "美国 10 年期国债总回报指数",
        "path": "data/processed/bonds/us_10y_treasury_total_return_index_annual_1928_2025.csv",
        "value_column": "index_level",
        "unit": "total return index",
        "frequency": "annual",
        "notes": "10 年期美国国债年度总回报指数。",
    },
    "china_treasury_bond_index": {
        "name": "中国国债指数",
        "path": "data/processed/bonds/china_treasury_bond_index_annual_2003_2025.csv",
        "value_column": "index_level",
        "unit": "index points",
        "frequency": "annual",
        "notes": "年度年末国债指数点位。",
    },
}


def get_asset_catalog() -> dict[str, dict[str, str]]:
    """Return a defensive copy of the configured V1 asset catalog."""
    return deepcopy(ASSETS)


def validate_asset_catalog(repo_root: Path | str = ".") -> None:
    """Validate that every asset file exists and contains its value column."""
    root = Path(repo_root)

    for asset_id, metadata in ASSETS.items():
        csv_path = root / metadata["path"]
        if not csv_path.exists():
            raise FileNotFoundError(f"{asset_id}: missing CSV file {csv_path}")

        header = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        value_column = metadata["value_column"]
        if value_column not in header:
            raise ValueError(
                f"{asset_id}: value column {value_column!r} not found in {csv_path}"
            )
