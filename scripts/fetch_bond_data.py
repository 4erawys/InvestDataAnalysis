from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import xlrd


FRED_DGS10_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
FRED_DGS10_PAGE = "https://fred.stlouisfed.org/series/DGS10"
DAMODARAN_HISTRET_URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histretSP.xls"
DAMODARAN_DATA_PAGE = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html"
EASTMONEY_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_PAGE = "https://quote.eastmoney.com/"
END_YEAR = 2025


def fetch_text(url: str, *, user_agent: bool = False) -> str:
    if not user_agent:
        return urlopen(url, timeout=30).read().decode("utf-8")
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": EASTMONEY_PAGE,
        },
    )
    return urlopen(request, timeout=30).read().decode("utf-8")


def fetch_bytes_with_retries(url: str, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return urlopen(url, timeout=60).read()
        except Exception as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2)
    raise RuntimeError(f"Failed to fetch {url}") from last_error


def fetch_eastmoney_kline() -> dict:
    params = {
        "secid": "1.000012",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": "20000101",
        "end": "20260624",
    }
    url = f"{EASTMONEY_KLINE_URL}?{urlencode(params)}"
    return json.loads(fetch_text(url, user_agent=True))


def parse_eastmoney_klines(payload: dict) -> list[dict[str, str]]:
    rows = []
    for line in payload["data"]["klines"]:
        fields = line.split(",")
        rows.append(
            {
                "date": fields[0],
                "open": fields[1],
                "close": fields[2],
                "high": fields[3],
                "low": fields[4],
                "volume": fields[5],
                "amount": fields[6],
                "amplitude_pct": fields[7],
                "change_pct": fields[8],
                "change": fields[9],
                "turnover_pct": fields[10],
            }
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_us_treasury_yield(raw_dir: Path, processed_dir: Path) -> Path:
    raw_data = fetch_text(FRED_DGS10_URL)
    raw_path = raw_dir / "fred_dgs10_daily.csv"
    output_path = processed_dir / "us_10y_treasury_yield_annual_1962_2025.csv"
    raw_path.write_text(raw_data, encoding="utf-8")

    by_year: dict[int, list[float]] = defaultdict(list)
    for row in csv.DictReader(raw_data.splitlines()):
        value = row["DGS10"].strip()
        if not value or value == ".":
            continue
        year = int(row["observation_date"][:4])
        if year <= END_YEAR:
            by_year[year].append(float(value))

    rows = []
    for year in sorted(by_year):
        values = by_year[year]
        rows.append(
            {
                "year": year,
                "yield_pct": f"{sum(values) / len(values):.3f}",
                "frequency": "annual",
                "source": "FRED DGS10",
                "source_url": FRED_DGS10_PAGE,
                "notes": (
                    "Annual average of daily 10-year U.S. Treasury constant maturity yield; "
                    "yield series, not a total return bond index"
                ),
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["year", "yield_pct", "frequency", "source", "source_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def build_us_treasury_total_return_index(raw_dir: Path, processed_dir: Path) -> Path:
    raw_xls_path = raw_dir / "damodaran_histretSP.xls"
    raw_extract_path = raw_dir / "damodaran_us_10y_treasury_returns_annual.csv"
    output_path = processed_dir / "us_10y_treasury_total_return_index_annual_1928_2025.csv"

    if raw_xls_path.exists():
        workbook_data = raw_xls_path.read_bytes()
    else:
        workbook_data = fetch_bytes_with_retries(DAMODARAN_HISTRET_URL)
        raw_xls_path.write_bytes(workbook_data)

    sheet = xlrd.open_workbook(file_contents=workbook_data).sheet_by_name("Returns by year")
    extracted_rows = []
    output_rows = []

    for row_index in range(20, sheet.nrows):
        row = sheet.row_values(row_index)
        if not isinstance(row[0], float):
            continue
        year = int(row[0])
        if year > END_YEAR:
            continue

        annual_return = float(row[4])
        index_level = float(row[11])
        extracted_rows.append(
            {
                "year": year,
                "annual_return_pct": f"{annual_return * 100:.4f}",
                "index_level": f"{index_level:.4f}",
            }
        )
        output_rows.append(
            {
                "year": year,
                "index_level": f"{index_level:.4f}",
                "frequency": "annual",
                "source": "Damodaran historical returns: US T. Bond (10-year)",
                "source_url": DAMODARAN_DATA_PAGE,
                "notes": (
                    "Value of $100 invested at start of 1928 in 10-year U.S. Treasury bonds; "
                    "annual total return series derived from constant-maturity 10-year Treasury yields"
                ),
            }
        )

    write_rows(raw_extract_path, extracted_rows)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["year", "index_level", "frequency", "source", "source_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return output_path


def build_china_treasury_index(raw_dir: Path, processed_dir: Path) -> Path:
    payload = fetch_eastmoney_kline()
    rows = parse_eastmoney_klines(payload)

    raw_path = raw_dir / "eastmoney_china_treasury_bond_index_daily.csv"
    output_path = processed_dir / "china_treasury_bond_index_annual_2003_2025.csv"
    write_rows(raw_path, rows)

    by_year: dict[int, dict[str, str]] = {}
    for row in rows:
        year = int(row["date"][:4])
        if year <= END_YEAR:
            by_year[year] = row

    output_rows = []
    for year in sorted(by_year):
        last_row = by_year[year]
        output_rows.append(
            {
                "year": year,
                "index_level": f"{float(last_row['close']):.2f}",
                "frequency": "annual",
                "source": "Eastmoney historical daily kline",
                "source_url": EASTMONEY_PAGE,
                "notes": f"国债指数 year-end close from last trading day {last_row['date']}",
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["year", "index_level", "frequency", "source", "source_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return output_path


def main() -> None:
    raw_dir = Path("data/raw/bonds")
    processed_dir = Path("data/processed/bonds")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    us_yield_path = build_us_treasury_yield(raw_dir, processed_dir)
    us_index_path = build_us_treasury_total_return_index(raw_dir, processed_dir)
    china_path = build_china_treasury_index(raw_dir, processed_dir)

    print(f"wrote {us_yield_path}")
    print(f"wrote {us_index_path}")
    print(f"wrote {china_path}")


if __name__ == "__main__":
    main()
