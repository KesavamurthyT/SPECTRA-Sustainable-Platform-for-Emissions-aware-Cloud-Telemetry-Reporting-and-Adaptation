from fastapi import APIRouter
from app.db import db
from app.services.sim_clock import get_sim_time
from app.services.cloudflare_radar import get_latest_latency

router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])

@router.get("/regions")
async def get_optimizer_regions():
    if not db.is_connected(): await db.connect()
    
    sim_now = await get_sim_time()
    regions = await db.region.find_many(where={"enabled": True})
    
    region_stats = []
    for reg in regions:
        carbon_entry = await db.carbonintensityhour.find_first(
            where={"regionCode": reg.code, "timestampUtc": sim_now}
        )
        carbon_intensity = carbon_entry.carbonIntensity if carbon_entry else 999
        latency = await get_latest_latency(reg.code)
        instances = await db.instance.find_many(where={"regionCode": reg.code, "status": "RUNNING"})
        workload_count = len(instances)
        avg_cost = sum(i.costPerHour for i in instances) / workload_count if workload_count > 0 else 0.0
            
        region_stats.append({
            "region": reg.displayName,
            "regionCode": reg.code,
            "carbonIntensity": carbon_intensity,
            "latency": latency,
            "costPerHour": avg_cost,
            "workloads": workload_count
        })
    
    if not region_stats: return []

    min_carbon_region = min(region_stats, key=lambda x: x["carbonIntensity"])
    greenest_name = min_carbon_region["region"]
    
    final_output = []
    for stat in region_stats:
        if stat["regionCode"] == min_carbon_region["regionCode"]:
            rec = {"type": "OPTIMAL"}
        else:
            rec = {
                "type": "MIGRATE",
                "target": greenest_name,
                "targetCode": min_carbon_region["regionCode"]
            }
        stat["recommendation"] = rec
        final_output.append(stat)
        
    return final_output
