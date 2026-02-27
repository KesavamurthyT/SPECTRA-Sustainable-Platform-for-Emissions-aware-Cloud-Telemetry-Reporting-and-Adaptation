import os
import csv
import json
import datetime
from app.db import db
from app.config.constants import REGION_KEYWORDS


async def import_csvs(csv_dir: str) -> None:
    """
    Import all ElectricityMaps CSV snapshot files from *csv_dir* into the
    CarbonIntensityHour table.  Region codes are inferred from the filenames
    using the REGION_KEYWORDS mapping defined in app/config/constants.py.

    Expected CSV columns (auto-detected, case-insensitive):
        - A timestamp column containing "timestamp", "datetime" or "date"
        - A carbon intensity column containing both "carbon" and "intensity"
    """
    if not os.path.exists(csv_dir):
        print(f"[csv_importer] CSV directory '{csv_dir}' does not exist. Skipping.")
        return
    
    files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]

    for filename in files:
        file_path = os.path.join(csv_dir, filename)
        region_code = None

        upper_name = filename.upper()
        for code, keywords in REGION_KEYWORDS.items():
            if any(k.upper() in upper_name for k in keywords):
                region_code = code
                break

        if not region_code:
            print(f"[csv_importer] Skipping '{filename}': could not determine region code from filename.")
            print(f"[csv_importer] Expected filename to contain one of: {list(REGION_KEYWORDS.keys())}")
            continue

        print(f"[csv_importer] Importing '{filename}' → region {region_code} ...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Auto-detect timestamp and carbon intensity columns
            timestamp_col = next(
                (h for h in headers if any(k in h.lower() for k in ("timestamp", "datetime", "date"))),
                None,
            )
            carbon_col = next(
                (h for h in headers if "carbon" in h.lower() and "intensity" in h.lower()),
                None,
            )

            if not timestamp_col or not carbon_col:
                print(
                    f"[csv_importer] Skipping '{filename}': "
                    f"could not find required columns. "
                    f"Found headers: {headers}"
                )
                continue

            batch_size = 500
            batch_data: list[dict] = []
            skipped = 0

            for row in reader:
                ts_str = row.get(timestamp_col, "").strip()
                carbon_str = row.get(carbon_col, "").strip()

                if not ts_str or not carbon_str:
                    skipped += 1
                    continue

                try:
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    ts = datetime.datetime.fromisoformat(ts_str)
                    carbon_val = int(float(carbon_str))

                    batch_data.append({
                        "regionCode": region_code,
                        "timestampUtc": ts,
                        "carbonIntensity": carbon_val,
                        "rawRowJson": json.dumps(row),
                    })

                    if len(batch_data) >= batch_size:
                        await db.carbonintensityhour.create_many(data=batch_data)
                        batch_data = []

                except Exception as exc:
                    skipped += 1
                    continue

            if batch_data:
                await db.carbonintensityhour.create_many(data=batch_data)

        print(f"[csv_importer] Finished '{filename}' — skipped {skipped} rows.")
