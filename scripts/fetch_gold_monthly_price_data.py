"""Build the monthly gold price series from the World Gold Council workbook.

The source is the World Gold Council (WGC) "Gold price averages in a range of
currencies since 1978" Excel workbook. WGC requires a manual download (no stable
direct-download URL), so the .xlsx is kept under data/manual_get_resources/
(gitignored, like data/raw/). This script reads the ``Monthly_Avg`` sheet, takes
the USD column (LBMA Gold Price, monthly average, USD per troy ounce), and writes
the cleaned, committed CSV under data/processed/gold/.

WGC is authoritative for the full 1978-2026 range. We previously used DataHub's
monthly file, but cross-checking showed DataHub has an ~11-month shift error over
1978-1998, so it was dropped in favor of WGC.

Source page: https://www.gold.org/goldhub/data/gold-prices

Run (inside the invest env, from the repo root):
    conda run -n invest python scripts/fetch_gold_monthly_price_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SOURCE_XLSX = Path(
    "data/manual_get_resources/"
    "Gold_price_averages_in_a range_of_currencies_since_1978.xlsx"
)
SHEET = "Monthly_Avg"
OUTPUT_PATH = Path("data/processed/gold/gold_price_monthly_1978_2026.csv")

# Layout of the Monthly_Avg sheet (0-indexed): currency labels sit on row 5
# (col 3 == "USD"); data starts on row 6 with col 2 = month-end date and
# col 3 = USD monthly-average price.
DATE_COL = 2
USD_COL = 3

SOURCE_NAME = "World Gold Council (WGC) – Monthly_Avg, USD (LBMA Gold Price)"
SOURCE_URL = "https://www.gold.org/goldhub/data/gold-prices"
NOTES = "Monthly average USD price per troy ounce; year-end-month value used when downsampled to annual."


def main() -> None:
    raw = pd.read_excel(SOURCE_XLSX, sheet_name=SHEET, header=None)

    dates = pd.to_datetime(raw.iloc[:, DATE_COL], errors="coerce")
    prices = pd.to_numeric(raw.iloc[:, USD_COL], errors="coerce")

    valid = dates.notna() & prices.notna()
    frame = pd.DataFrame(
        {
            "year_month": dates[valid].dt.strftime("%Y-%m"),
            "price_usd_per_troy_oz": prices[valid].round(2),
        }
    ).sort_values("year_month")

    if frame["year_month"].duplicated().any():
        raise ValueError("duplicate months found in source; check the sheet layout")

    frame["frequency"] = "monthly"
    frame["source"] = SOURCE_NAME
    frame["source_url"] = SOURCE_URL
    frame["notes"] = NOTES

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_PATH, index=False)

    print(
        f"wrote {OUTPUT_PATH} rows={len(frame)} "
        f"range={frame['year_month'].iloc[0]}..{frame['year_month'].iloc[-1]} "
        f"price={frame['price_usd_per_troy_oz'].min()}..{frame['price_usd_per_troy_oz'].max()}"
    )


if __name__ == "__main__":
    main()
