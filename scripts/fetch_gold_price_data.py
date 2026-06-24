from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.request import urlopen


ANNUAL_URL = "https://datahub.io/core/gold-prices/r/annual.csv"
MONTHLY_URL = "https://datahub.io/core/gold-prices/r/monthly.csv"
DATAPACKAGE_URL = "https://datahub.io/core/gold-prices/datapackage.json"
START_YEAR = 1926
END_YEAR = 2025


def main() -> None:
    raw_dir = Path("data/raw/gold")
    processed_dir = Path("data/processed/gold")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    annual_data = urlopen(ANNUAL_URL, timeout=30).read().decode("utf-8")
    monthly_data = urlopen(MONTHLY_URL, timeout=30).read().decode("utf-8")
    metadata = urlopen(DATAPACKAGE_URL, timeout=30).read().decode("utf-8")

    raw_annual_path = raw_dir / "datahub_gold_prices_annual.csv"
    raw_monthly_path = raw_dir / "datahub_gold_prices_monthly.csv"
    metadata_path = raw_dir / "datahub_gold_prices_datapackage.json"
    output_path = processed_dir / "gold_price_annual_1926_2025.csv"

    raw_annual_path.write_text(annual_data, encoding="utf-8")
    raw_monthly_path.write_text(monthly_data, encoding="utf-8")
    metadata_path.write_text(json.dumps(json.loads(metadata), indent=2), encoding="utf-8")

    annual_prices = {
        int(row["Date"]): float(row["Price"])
        for row in csv.DictReader(annual_data.splitlines())
    }

    monthly_prices: dict[int, list[float]] = {}
    for row in csv.DictReader(monthly_data.splitlines()):
        year = int(row["Date"][:4])
        monthly_prices.setdefault(year, []).append(float(row["Price"]))

    filtered_rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        if year in annual_prices:
            price = annual_prices[year]
            source = "DataHub core/gold-prices annual.csv"
            source_url = ANNUAL_URL
            notes = "Annual observation from source file"
        else:
            prices = monthly_prices[year]
            price = sum(prices) / len(prices)
            source = "DataHub core/gold-prices monthly.csv"
            source_url = MONTHLY_URL
            notes = f"Annual average calculated from {len(prices)} monthly observations"
        filtered_rows.append(
            {
                "year": year,
                "price_usd_per_troy_oz": f"{price:.3f}",
                "frequency": "annual",
                "source": source,
                "source_url": source_url,
                "notes": notes,
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "year",
                "price_usd_per_troy_oz",
                "frequency",
                "source",
                "source_url",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(filtered_rows)

    print(
        f"wrote {output_path} rows={len(filtered_rows)} "
        f"years={filtered_rows[0]['year']}-{filtered_rows[-1]['year']}"
    )
    print(f"wrote {raw_annual_path}")
    print(f"wrote {raw_monthly_path}")
    print(f"wrote {metadata_path}")


if __name__ == "__main__":
    main()
