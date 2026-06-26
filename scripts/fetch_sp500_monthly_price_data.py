"""
Fetch monthly S&P 500 price-return index from DataHub/GitHub (Robert Shiller dataset).

Source : https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv
Coverage: 1871-01 to present (one row per month, beginning-of-month observation)
Output  : data/processed/indices/sp500_monthly_1871_<endYear>.csv

Schema: year_month,index_level,frequency,source,source_url,notes
  - index_level = S&P Composite price-return index level (not total-return)
  - frequency   = monthly
  - Pre-1926 data is the Cowles Commission stock-price index extended to 1871.
  - Dividends NOT included.
"""

from __future__ import annotations

import csv
import datetime
import io
from pathlib import Path
from urllib.request import Request, urlopen

# ── source constants ──────────────────────────────────────────────────────────
SP500_GITHUB_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv"
)
SP500_SOURCE_PAGE = "https://datahub.io/core/s-and-p-500"
RAW_FILENAME = "datahub_github_sp500_monthly.csv"
START_YEAR = 1871
PROCESSED_DIR = Path("data/processed/indices")
RAW_DIR = Path("data/raw/indices")

NOTES = (
    "S&P Composite price-return index, beginning-of-month observation "
    "(Robert Shiller / DataHub); pre-1926 uses Cowles Commission stock-price "
    "index extended to 1871; dividends excluded (not total-return)"
)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── download ──────────────────────────────────────────────────────────────
    req = Request(SP500_GITHUB_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw_data = urlopen(req, timeout=30).read().decode("utf-8")
    raw_path = RAW_DIR / RAW_FILENAME
    raw_path.write_text(raw_data, encoding="utf-8")
    print(f"Downloaded {len(raw_data):,} bytes → {raw_path}")

    # exclude the current (partial) month
    today = datetime.date.today()
    cutoff_ym = f"{today.year:04d}-{today.month:02d}"

    # ── parse & clean ─────────────────────────────────────────────────────────
    rows_out: list[dict[str, str]] = []
    for row in csv.DictReader(io.StringIO(raw_data)):
        date_str = row.get("Date", "").strip()
        sp500_str = row.get("SP500", "").strip()
        if len(date_str) < 7 or not sp500_str:
            continue
        try:
            val = float(sp500_str)
        except ValueError:
            continue
        if val <= 0:
            continue
        year_month = date_str[:7]  # "YYYY-MM"
        if year_month >= cutoff_ym:
            continue
        if int(date_str[:4]) < START_YEAR:
            continue
        rows_out.append(
            {
                "year_month": year_month,
                "index_level": f"{val:.3f}",
                "frequency": "monthly",
                "source": "DataHub / Robert Shiller S&P Composite",
                "source_url": SP500_GITHUB_URL,
                "notes": NOTES,
            }
        )

    rows_out.sort(key=lambda r: r["year_month"])

    if not rows_out:
        raise RuntimeError("No rows parsed — check source format")

    end_year = int(rows_out[-1]["year_month"][:4])
    out_path = PROCESSED_DIR / f"sp500_monthly_{START_YEAR}_{end_year}.csv"

    fieldnames = ["year_month", "index_level", "frequency", "source", "source_url", "notes"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote {len(rows_out):,} rows → {out_path}")
    print(f"Range : {rows_out[0]['year_month']} → {rows_out[-1]['year_month']}")
    print(f"Head  : {rows_out[:2]}")
    print(f"Tail  : {rows_out[-2:]}")


if __name__ == "__main__":
    main()
