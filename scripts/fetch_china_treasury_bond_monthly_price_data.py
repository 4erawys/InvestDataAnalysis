"""
Fetch monthly China Treasury Bond Index (国债指数) close from Eastmoney kline API.

Source     : https://push2his.eastmoney.com/api/qt/stock/kline/get
             secid=1.000012, klt=103 (monthly), fqt=0 (unadjusted)
Coverage   : 2003-02 to present (last complete month)
Output     : data/processed/bonds/china_treasury_bond_index_monthly_2003_<endYear>.csv

Schema: year_month,index_level,frequency,source,source_url,notes
  - index_level = China Treasury Bond Index month-end last-trading-day close (unadjusted)
  - frequency   = monthly
"""

from __future__ import annotations

import csv
import datetime
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ── source constants ──────────────────────────────────────────────────────────
EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_SOURCE_PAGE = "https://quote.eastmoney.com/"
SECID = "1.000012"
BEG = "20000101"
END = "20300101"
RAW_DIR = Path("data/raw/bonds")
PROCESSED_DIR = Path("data/processed/bonds")
START_YEAR = 2003

NOTES = (
    "China Treasury Bond Index (国债指数, 000012) monthly close, last trading day of each month; "
    "unadjusted (fqt=0); total-return bond index (includes coupon reinvestment); "
    "source: Eastmoney kline API secid=1.000012 klt=103"
)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # exclude the current (partial) month
    today = datetime.date.today()
    cutoff_ym = f"{today.year:04d}-{today.month:02d}"

    # ── download ──────────────────────────────────────────────────────────────
    params = {
        "secid": SECID,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "103",
        "fqt": "0",
        "beg": BEG,
        "end": END,
    }
    url = f"{EASTMONEY_KLINE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": EASTMONEY_SOURCE_PAGE})
    payload = json.loads(urlopen(req, timeout=30).read().decode("utf-8"))
    klines = payload["data"]["klines"]
    print(f"Downloaded {len(klines)} monthly klines from Eastmoney")

    raw_path = RAW_DIR / "eastmoney_china_treasury_bond_index_monthly.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved raw → {raw_path}")

    # ── parse & clean ─────────────────────────────────────────────────────────
    rows_out: list[dict[str, str]] = []
    for line in klines:
        fields = line.split(",")
        date_str = fields[0]          # e.g. "2003-02-28"
        close_str = fields[2]         # month-end close
        year_month = date_str[:7]     # "YYYY-MM"
        if year_month >= cutoff_ym:
            continue
        if int(date_str[:4]) < START_YEAR:
            continue
        try:
            val = float(close_str)
        except ValueError:
            continue
        if val <= 0:
            continue
        rows_out.append(
            {
                "year_month": year_month,
                "index_level": f"{val:.2f}",
                "frequency": "monthly",
                "source": "Eastmoney kline API",
                "source_url": EASTMONEY_SOURCE_PAGE,
                "notes": NOTES,
            }
        )

    rows_out.sort(key=lambda r: r["year_month"])

    if not rows_out:
        raise RuntimeError("No rows parsed — check source format")

    start_year = int(rows_out[0]["year_month"][:4])
    end_year = int(rows_out[-1]["year_month"][:4])
    out_path = PROCESSED_DIR / f"china_treasury_bond_index_monthly_{start_year}_{end_year}.csv"

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
