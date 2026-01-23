import os
import csv
import json
import datetime
from app.db import db

async def import_csvs(csv_dir: str):
    """
    Import all CSVs from the directory into CarbonIntensityHour table.
    """
    if not os.path.exists(csv_dir):
        print(f"CSV directory {csv_dir} does not exist.")
        return

    known_regions = {
        "IN": ["IN", "India"],
        "SE": ["SE", "Sweden"],
        "US": ["US", "United States", "USA"],
        "IE": ["IE", "Ireland"],
        "JP": ["JP", "Japan"]
    }
    
    files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    
    for filename in files:
        file_path = os.path.join(csv_dir, filename)
        region_code = None
        
        upper_name = filename.upper()
        for code, keywords in known_regions.items():
            if any(k.upper() in upper_name for k in keywords):
                region_code = code
                break
        
        if not region_code:
            print(f"Skipping {filename}: Could not determine region code.")
            continue
            
        print(f"Importing {filename} for region {region_code}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            timestamp_col = next((h for h in headers if "timestamp" in h.lower() or "datetime" in h.lower() or "date" in h.lower()), None)
            carbon_col = next((h for h in headers if "carbon" in h.lower() and "intensity" in h.lower()), None)
            
            if not timestamp_col or not carbon_col:
                print(f"Skipping {filename}: Could not find timestamp or carbon intensity columns.")
                continue
                
            batch_size = 500
            batch_data = []
            
            for row in reader:
                ts_str = row[timestamp_col]
                carbon_str = row[carbon_col]
                
                if not ts_str or not carbon_str:
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
                        "rawRowJson": json.dumps(row)
                    })
                    
                    if len(batch_data) >= batch_size:
                        await db.carbonintensityhour.create_many(data=batch_data)
                        batch_data = []
                        
                except Exception:
                    continue
            
            if batch_data:
                await db.carbonintensityhour.create_many(data=batch_data)
        
        print(f"Finished {filename}.")
