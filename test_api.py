import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        try:
            print("Testing /api/optimizer/regions...")
            r = await client.get("http://localhost:8000/api/optimizer/regions", timeout=5.0)
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
            
            print("\nTesting /api/regions/signals/latest...")
            r2 = await client.get("http://localhost:8000/api/regions/signals/latest", timeout=5.0)
            print(f"Status: {r2.status_code}")
            print(f"Response: {r2.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
