from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt


DATA_PATH = Path("data/processed/gold/gold_price_monthly_1978_2026.csv")
OUTPUT_PATH = Path("reports/figures/gold_price_monthly_1978_2026.png")


def load_gold_prices() -> tuple[list[date], list[float]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    months = [date(int(ym[:4]), int(ym[5:7]), 1) for ym in (r["year_month"] for r in rows)]
    prices = [float(row["price_usd_per_troy_oz"]) for row in rows]
    return months, prices


def main() -> None:
    months, prices = load_gold_prices()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.plot(months, prices, color="#b8860b", linewidth=2.2)
    ax.fill_between(months, prices, color="#b8860b", alpha=0.14)

    ax.set_title(
        f"Gold Price Trend, {months[0].year}-{months[-1].year} (monthly)",
        fontsize=16,
        pad=14,
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("USD per troy ounce")
    ax.set_xlim(months[0], months[-1])
    ax.grid(True, axis="y", alpha=0.28)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.text(
        0.01,
        0.01,
        "Source: World Gold Council (LBMA Gold Price); monthly average USD price per troy ounce.",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUTPUT_PATH, dpi=180)
    plt.close(fig)

    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
