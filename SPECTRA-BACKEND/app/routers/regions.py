from fastapi import APIRouter
from app.db import db
from app.services.sim_clock import get_sim_time
import datetime

router = APIRouter(prefix="/api/regions", tags=["regions"])

@router.get("/signals/latest")
async def get_latest_signals():
    if not db.is_connected(): await db.connect()
    sim_now = await get_sim_time()
    regions = await db.region.find_many(where={"enabled": True})
    results = []
    
    for reg in regions:
        data = await db.carbonintensityhour.find_first(
            where={ "regionCode": reg.code, "timestampUtc": sim_now }
        )
        results.append({
            "code": reg.code,
            "displayName": reg.displayName,
            "carbonIntensity": data.carbonIntensity if data else None,
            "timestampUtc": data.timestampUtc if data else sim_now
        })
        
    return { "simNowUtc": sim_now, "regions": results }

@router.get("/signals/history")
async def get_signals_history(code: str, hours: int = 168):
    if not db.is_connected(): await db.connect()
    sim_now = await get_sim_time()
    start_time = sim_now - datetime.timedelta(hours=hours)
    return await db.carbonintensityhour.find_many(
        where={ "regionCode": code, "timestampUtc": { "lte": sim_now, "gte": start_time } },
        order={"timestampUtc": "asc"}
    )

@router.get("/latency/latest")
async def get_latency_latest():
    if not db.is_connected(): await db.connect()
    regions = await db.region.find_many(where={"enabled": True})
    results = []
    for reg in regions:
        latest = await db.latencymetric.find_first(where={"regionCode": reg.code}, order={"timestampUtc": "desc"})
        results.append({ "code": reg.code, "latencyMs": latest.latencyMs if latest else None, "timestampUtc": latest.timestampUtc if latest else None })
    return results

@router.get("/latency/history")
async def get_latency_history(code: str, days: int = 90):
    if not db.is_connected(): await db.connect()
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return await db.latencymetric.find_many(where={ "regionCode": code, "timestampUtc": {"gte": cutoff} }, order={"timestampUtc": "asc"})
