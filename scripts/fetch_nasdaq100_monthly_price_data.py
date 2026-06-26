"""
Fetch monthly Nasdaq-100 price-return index from FRED (series NASDAQ100).

Source : https://fred.stlouisfed.org/series/NASDAQ100  (daily data)
Coverage: 1986-01 onwards (daily series starts 1986-01-02)
Output  : data/processed/indices/nasdaq100_monthly_1986_<endYear>.csv

Schema: year_month,index_level,frequency,source,source_url,notes
  - index_level = Nasdaq-100 price-return index, month-end last-trading-day close
  - frequency   = monthly
  - FRED daily data is aggregated here to month-end (last trading day per month).
  - Dividends NOT included (price return, not total-return).
  - NDX launched 1985-01-31; FRED series begins 1986-01-02 (1985 not covered).
"""

from __future__ import annotations

import csv
import datetime
import io
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

# ── source constants ──────────────────────────────────────────────────────────
FRED_NASDAQ100_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQ100"
NASDAQ100_SOURCE_PAGE = "https://fred.stlouisfed.org/series/NASDAQ100"
RAW_FILENAME = "fred_nasdaq100_daily.csv"
START_YEAR = 1986
PROCESSED_DIR = Path("data/processed/indices")
RAW_DIR = Path("data/raw/indices")

NOTES = (
    "Nasdaq-100 price-return index, month-end last-trading-day close; "
    "aggregated from FRED series NASDAQ100 (daily); "
    "FRED coverage starts 1986-01-02 (NDX launched 1985-01-31, 1985 not available); "
    "dividends excluded (not total-return)"
)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── download daily data ───────────────────────────────────────────────────
    req = Request(FRED_NASDAQ100_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw_data = urlopen(req, timeout=30).read().decode("utf-8")
    raw_path = RAW_DIR / RAW_FILENAME
    raw_path.write_text(raw_data, encoding="utf-8")
    print(f"Downloaded {len(raw_data):,} bytes → {raw_path}")

    # exclude the current (partial) month
    today = datetime.date.today()
    cutoff_ym = f"{today.year:04d}-{today.month:02d}"

    # ── aggregate daily → month-end ───────────────────────────────────────────
    by_month: dict[str, list[tuple[datetime.date, float]]] = defaultdict(list)
    for row in csv.DictReader(io.StringIO(raw_data)):
        date_str = row.get("observation_date", "").strip()
        val_str = row.get("NASDAQ100", "").strip()
        if not date_str or not val_str or val_str == ".":
            continue
        try:
            val = float(val_str)
        except ValueError:
            continue
        if val <= 0:
            continue
        try:
            dt = datetime.date.fromisoformat(date_str)
        except ValueError:
            continue
        if dt.year < START_YEAR:
            continue
        ym = f"{dt.year:04d}-{dt.month:02d}"
        if ym >= cutoff_ym:
            continue
        by_month[ym].append((dt, val))

    rows_out: list[dict[str, str]] = []
    for ym in sorted(by_month):
        pts = sorted(by_month[ym])        # sort ascending by date
        _last_dt, last_val = pts[-1]      # last trading day of the month
        rows_out.append(
            {
                "year_month": ym,
                "index_level": f"{last_val:.3f}",
                "frequency": "monthly",
                "source": "FRED NASDAQ100",
                "source_url": NASDAQ100_SOURCE_PAGE,
                "notes": NOTES,
            }
        )

    if not rows_out:
        raise RuntimeError("No rows produced — check source format")

    end_year = int(rows_out[-1]["year_month"][:4])
    out_path = PROCESSED_DIR / f"nasdaq100_monthly_{START_YEAR}_{end_year}.csv"

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
