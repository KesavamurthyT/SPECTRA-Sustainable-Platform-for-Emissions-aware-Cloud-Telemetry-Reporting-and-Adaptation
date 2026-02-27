"""
routers/scheduler.py
--------------------
Job scheduling optimisation and carbon intensity forecasting.

GET  /api/scheduler/jobs              — list all scheduled jobs
POST /api/scheduler/jobs              — create a new job
POST /api/scheduler/jobs/{id}/accept  — accept recommendation
PATCH /api/scheduler/jobs/{id}        — manually update a job's schedule
GET  /api/scheduler/forecast          — 24-hour carbon intensity forecast
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db
from app.services.sim_clock import get_sim_time
import datetime

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

OPTIMAL_THRESHOLD = 100   # g CO2/kWh
PEAK_THRESHOLD    = 180   # g CO2/kWh


class JobCreate(BaseModel):
    name: str
    team: str
    currentSchedule: str
    recommendedSchedule: str
    durationHours: float
    carbonSavings: float
    flexibility: str  # "critical" | "flexible" | "batch"


class JobPatch(BaseModel):
    currentSchedule: Optional[str] = None
    recommendedSchedule: Optional[str] = None
    flexibility: Optional[str] = None


@router.get("/jobs")
async def list_jobs():
    """Return all scheduled jobs ordered by carbonSavings descending."""
    if not db.is_connected():
        await db.connect()

    jobs = await db.scheduledjob.find_many(order={"carbonSavings": "desc"})
    return jobs


@router.post("/jobs")
async def create_job(body: JobCreate):
    """Create a new scheduled job entry."""
    if not db.is_connected():
        await db.connect()

    job = await db.scheduledjob.create(
        data={
            "name": body.name,
            "team": body.team,
            "currentSchedule": body.currentSchedule,
            "recommendedSchedule": body.recommendedSchedule,
            "durationHours": body.durationHours,
            "carbonSavings": body.carbonSavings,
            "flexibility": body.flexibility,
            "accepted": False,
        }
    )
    return job


@router.post("/jobs/{job_id}/accept")
async def accept_job_recommendation(job_id: int):
    """
    Accept the recommended schedule: sets currentSchedule = recommendedSchedule
    and marks accepted = True.
    """
    if not db.is_connected():
        await db.connect()

    job = await db.scheduledjob.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    updated = await db.scheduledjob.update(
        where={"id": job_id},
        data={
            "currentSchedule": job.recommendedSchedule,
            "accepted": True,
        },
    )
    return updated


@router.patch("/jobs/{job_id}")
async def patch_job(job_id: int, body: JobPatch):
    """Manually update a job's schedule fields."""
    if not db.is_connected():
        await db.connect()

    job = await db.scheduledjob.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await db.scheduledjob.update(where={"id": job_id}, data=update_data)
    return updated


@router.get("/forecast")
async def get_forecast(region: Optional[str] = None):
    """
    Return the next 24 CarbonIntensityHour records for a given region.
    If no region is specified, picks the region currently showing
    the lowest carbon intensity (greenest).

    Each item includes `isOptimal` (< 100 g) and `isPeak` (> 180 g) flags.
    """
    if not db.is_connected():
        await db.connect()

    sim_now = await get_sim_time()

    if not region:
        # Find the region with the lowest carbon intensity at sim_now
        entry = await db.carbonintensityhour.find_first(
            where={"timestampUtc": sim_now},
            order={"carbonIntensity": "asc"},
        )
        region = entry.regionCode if entry else None

    if not region:
        return []

    # Fetch next 24 rows for this region after sim_now
    rows = await db.carbonintensityhour.find_many(
        where={
            "regionCode": region,
            "timestampUtc": {"gte": sim_now},
        },
        order={"timestampUtc": "asc"},
        take=24,
    )

    forecast = []
    for i, row in enumerate(rows):
        forecast.append({
            "hour": i,
            "timestampUtc": row.timestampUtc.isoformat(),
            "regionCode": row.regionCode,
            "intensity": row.carbonIntensity,
            "isOptimal": row.carbonIntensity < OPTIMAL_THRESHOLD,
            "isPeak": row.carbonIntensity > PEAK_THRESHOLD,
        })

    return forecast
