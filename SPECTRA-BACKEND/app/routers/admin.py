import os
from fastapi import APIRouter
from app.db import db
from app.services.csv_importer import import_csvs
from app.services.sim_clock import tick_time
from app.services.cloudflare_radar import update_latency_metrics
from app.services.seeds import seed_regions, seed_instances, seed_anomalies, seed_team_budgets, seed_scheduled_jobs, seed_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/import")
async def trigger_import():
    if not db.is_connected(): await db.connect()
    csv_dir = os.getenv("CSV_DIR", "./data/electricitymaps")
    await seed_regions()
    await import_csvs(csv_dir)
    await seed_instances()
    await seed_anomalies()
    await seed_team_budgets()
    await seed_scheduled_jobs()
    await seed_settings()
    return {"status": "Import triggered"}

@router.post("/tick")
async def trigger_tick(hours: int = 1):
    if not db.is_connected(): await db.connect()
    new_time = await tick_time(hours)
    return {"status": "Ticked", "simNowUtc": new_time}

@router.post("/latency/fetch-now")
async def trigger_latency_fetch():
    if not db.is_connected(): await db.connect()
    await update_latency_metrics()
    return {"status": "Latency fetch triggered"}
