import asyncio
import os
import sys

# Add backend to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import db
from app.services.csv_importer import import_csvs
from app.services.seeds import seed_regions, seed_instances

async def main():
    print("Starting manual CSV import script...")
    await db.connect()
    
    csv_dir = os.getenv("CSV_DIR", "./data/electricitymaps")
    await seed_regions()
    await import_csvs(csv_dir)
    await seed_instances()
    
    await db.disconnect()
    print("Import script finished.")

if __name__ == "__main__":
    asyncio.run(main())
