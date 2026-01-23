import httpx
import asyncio

async def test_migration():
    async with httpx.AsyncClient() as client:
        try:
            # 1. Check Regions first
            print("Fetching regions...")
            r = await client.get("http://localhost:8000/api/optimizer/regions")
            regions = r.json()
            
            # Find a candidate
            candidate = next((reg for reg in regions if reg["recommendation"]["type"] == "MIGRATE"), None)
            
            if not candidate:
                print("No migration candidates found to test.")
                return

            rec = candidate["recommendation"]
            print(f"Testing migration from {candidate['regionCode']} to {rec['targetCode']}...")
            
            # 2. Execute Migration
            payload = {
                "fromRegion": candidate["regionCode"],
                "toRegion": rec["targetCode"],
                "mode": "ALL_RUNNING"
            }
            
            r_mig = await client.post("http://localhost:8000/api/migrations/execute", json=payload)
            print(f"Migration Status: {r_mig.status_code}")
            print(f"Migration Response: {r_mig.text}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_migration())
