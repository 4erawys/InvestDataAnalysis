from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


SP500_URL = "https://r2.datahub.io/clv1551hg0004mj09hjz069e9/main/raw/data/data.csv"
SP500_METADATA_URL = "https://datahub.io/core/s-and-p-500/datapackage.json"
SP500_PAGE_URL = "https://datahub.io/core/s-and-p-500"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
SP500_START_YEAR = 1926
END_YEAR = 2025


class WikiTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table" and "wikitable" in attrs_dict.get("class", ""):
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_table and tag in {"td", "th"} and self._in_cell:
            text = " ".join("".join(self._current_cell).split())
            self._current_row.append(text)
            self._in_cell = False
        elif self._in_table and tag == "tr":
            if self._current_row:
                self._current_table.append(self._current_row)
        elif self._in_table and tag == "table":
            self.tables.append(self._current_table)
            self._current_table = []
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


def fetch_text(url: str, *, user_agent: bool = False) -> str:
    if not user_agent:
        return urlopen(url, timeout=30).read().decode("utf-8")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(request, timeout=30).read().decode("utf-8")


def parse_number(value: str) -> float:
    return float(re.sub(r"[,%$]", "", value).replace("\u2212", "-").strip())


def build_sp500(raw_dir: Path, processed_dir: Path) -> Path:
    data = fetch_text(SP500_URL)
    raw_path = raw_dir / "datahub_sp500_monthly.csv"
    metadata_path = raw_dir / "datahub_sp500_datapackage.json"
    output_path = processed_dir / "sp500_annual_1926_2025.csv"

    raw_path.write_text(data, encoding="utf-8")
    try:
        metadata = fetch_text(SP500_METADATA_URL)
    except Exception:
        metadata = json.dumps(
            {
                "name": "s-and-p-500",
                "source_page": SP500_PAGE_URL,
                "data_url": SP500_URL,
                "note": "Metadata download failed; raw CSV was downloaded directly.",
            }
        )
    metadata_path.write_text(json.dumps(json.loads(metadata), indent=2), encoding="utf-8")

    by_year: dict[int, list[float]] = defaultdict(list)
    for row in csv.DictReader(data.splitlines()):
        year = int(row["Date"][:4])
        if SP500_START_YEAR <= year <= END_YEAR:
            by_year[year].append(float(row["SP500"]))

    rows = []
    for year in range(SP500_START_YEAR, END_YEAR + 1):
        values = by_year[year]
        rows.append(
            {
                "year": year,
                "index_level": f"{sum(values) / len(values):.3f}",
                "frequency": "annual",
                "source": "DataHub core/s-and-p-500 data.csv",
                "source_url": SP500_PAGE_URL,
                "notes": f"Annual average calculated from {len(values)} monthly S&P 500 observations",
            }
        )

    write_processed(output_path, rows)
    return output_path


def build_nasdaq100(raw_dir: Path, processed_dir: Path) -> Path:
    html = fetch_text(NASDAQ100_URL, user_agent=True)

    raw_path = raw_dir / "wikipedia_nasdaq100.html"
    output_path = processed_dir / "nasdaq100_annual_1985_2025.csv"
    raw_path.write_text(html, encoding="utf-8")

    parser = WikiTableParser()
    parser.feed(html)

    annual_table = None
    for table in parser.tables:
        if table and "Year" in table[0][0] and any("Closing level" in cell for cell in table[0]):
            annual_table = table
            break

    if annual_table is None:
        raise RuntimeError("Could not find Nasdaq-100 annual returns table")

    rows = []
    for table_row in annual_table[1:]:
        if len(table_row) < 2 or not table_row[0].isdigit():
            continue
        year = int(table_row[0])
        if year > END_YEAR:
            continue
        rows.append(
            {
                "year": year,
                "index_level": f"{parse_number(table_row[1]):.2f}",
                "frequency": "annual",
                "source": "Wikipedia Nasdaq-100 annual returns table",
                "source_url": NASDAQ100_URL,
                "notes": "Year-end closing level from annual returns table",
            }
        )

    write_processed(output_path, rows)
    return output_path


def write_processed(path: Path, rows: list[dict[str, str | int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["year", "index_level", "frequency", "source", "source_url", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    raw_dir = Path("data/raw/indices")
    processed_dir = Path("data/processed/indices")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    sp500_path = build_sp500(raw_dir, processed_dir)
    nasdaq100_path = build_nasdaq100(raw_dir, processed_dir)

    print(f"wrote {sp500_path}")
    print(f"wrote {nasdaq100_path}")


if __name__ == "__main__":
    main()
