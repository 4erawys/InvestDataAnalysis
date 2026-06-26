from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


SERIES = [
    {
        "title": "Gold Price",
        "path": Path("data/processed/gold/gold_price_monthly_1978_2026.csv"),
        "value_column": "price_usd_per_troy_oz",
        "ylabel": "USD per troy oz",
        "color": "#b8860b",
    },
    {
        "title": "S&P 500",
        "path": Path("data/processed/indices/sp500_annual_1926_2025.csv"),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#1f77b4",
    },
    {
        "title": "Nasdaq-100",
        "path": Path("data/processed/indices/nasdaq100_annual_1985_2025.csv"),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#9467bd",
    },
    {
        "title": "SSE Composite",
        "path": Path("data/processed/indices/sse_composite_annual_1990_2025.csv"),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#d62728",
    },
    {
        "title": "CSI 300",
        "path": Path("data/processed/indices/csi300_annual_2005_2025.csv"),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#ff7f0e",
    },
    {
        "title": "U.S. 10Y Treasury Total Return Index",
        "path": Path(
            "data/processed/bonds/us_10y_treasury_total_return_index_annual_1928_2025.csv"
        ),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#2ca02c",
    },
    {
        "title": "China Treasury Bond Index",
        "path": Path("data/processed/bonds/china_treasury_bond_index_annual_2003_2025.csv"),
        "value_column": "index_level",
        "ylabel": "Index level",
        "color": "#17becf",
    },
]

OUTPUT_PATH = Path("reports/figures/all_asset_curves.png")


def load_series(path: Path, value_column: str) -> tuple[list[int], list[float]]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if rows and "year_month" in rows[0]:
        # Monthly CSV: downsample to annual using each year's last month
        # (rows are chronologically sorted, so the last write per year wins).
        by_year: dict[int, float] = {}
        for row in rows:
            by_year[int(row["year_month"][:4])] = float(row[value_column])
        years = sorted(by_year)
        return years, [by_year[year] for year in years]

    years = [int(row["year"]) for row in rows]
    values = [float(row[value_column]) for row in rows]
    return years, values


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(4, 2, figsize=(15, 17), sharex=False)
    flat_axes = list(axes.ravel())

    for ax, series in zip(flat_axes, SERIES):
        years, values = load_series(series["path"], series["value_column"])
        ax.plot(years, values, color=series["color"], linewidth=2.0)
        ax.fill_between(years, values, color=series["color"], alpha=0.10)
        ax.set_title(f"{series['title']} ({years[0]}-{years[-1]})", fontsize=12, pad=8)
        ax.set_ylabel(series["ylabel"])
        ax.set_xlim(years[0], years[-1])
        ax.grid(True, axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for ax in flat_axes[len(SERIES) :]:
        ax.axis("off")

    fig.suptitle("Annual Asset and Bond Market Curves", fontsize=18, y=0.995)
    fig.text(
        0.01,
        0.01,
        "Sources: DataHub, Wikipedia, Eastmoney, FRED. Values are annual prices/index levels; "
        "U.S. Treasury is a cumulative total return index from Damodaran data.",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.025, 1, 0.98))
    fig.savefig(OUTPUT_PATH, dpi=180)
    plt.close(fig)

    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
