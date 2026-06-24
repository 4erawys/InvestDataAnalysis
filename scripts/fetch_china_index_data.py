from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SOURCE_PAGE = "https://quote.eastmoney.com/"
END_YEAR = 2025

INDICES = [
    {
        "name": "上证指数",
        "file_stem": "sse_composite",
        "code": "000001",
        "secid": "1.000001",
        "start": "19900101",
    },
    {
        "name": "沪深300",
        "file_stem": "csi300",
        "code": "000300",
        "secid": "1.000300",
        "start": "20040101",
    },
]


def fetch_kline(secid: str, start: str) -> dict:
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": start,
        "end": "20260624",
    }
    url = f"{EASTMONEY_KLINE_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urlopen(request, timeout=30).read().decode("utf-8"))


def parse_klines(payload: dict) -> list[dict[str, str]]:
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


def write_daily(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_annual(path: Path, rows: list[dict[str, str]], index: dict[str, str]) -> None:
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
                "source_url": SOURCE_PAGE,
                "notes": (
                    f"{index['name']} year-end close from last trading day "
                    f"{last_row['date']}"
                ),
            }
        )

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["year", "index_level", "frequency", "source", "source_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> None:
    raw_dir = Path("data/raw/indices")
    processed_dir = Path("data/processed/indices")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    for index in INDICES:
        payload = fetch_kline(index["secid"], index["start"])
        rows = parse_klines(payload)

        raw_path = raw_dir / f"eastmoney_{index['file_stem']}_daily.csv"
        processed_path = (
            processed_dir
            / f"{index['file_stem']}_annual_{rows[0]['date'][:4]}_{END_YEAR}.csv"
        )

        write_daily(raw_path, rows)
        write_annual(processed_path, rows, index)

        print(f"wrote {raw_path} rows={len(rows)}")
        print(f"wrote {processed_path}")


if __name__ == "__main__":
    main()
