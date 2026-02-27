"""
routers/anomalies.py
--------------------
Anomaly detection feed and action management.

GET   /api/anomalies           — list anomalies (?status=pending|resolved)
POST  /api/anomalies           — create / inject a new anomaly (admin/seed use)
PATCH /api/anomalies/{id}/action — update the action field
GET   /api/anomalies/stats     — summary stats
"""

import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])

CO2E_SAVINGS = {
    "restarted": 12.0,
    "auto_killed": 36.0,
    "alerted": 0.0,
    "pending": 0.0,
}


class AnomalyCreate(BaseModel):
    instanceId: str
    instanceName: str
    type: str
    score: float
    expectedValue: float
    actualValue: float
    severity: str
    action: str = "pending"
    co2eSaved: float = 0.0


class AnomalyActionPatch(BaseModel):
    action: str  # "pending" | "alerted" | "restarted" | "auto_killed"


# ────────────────────────────── GET /stats must come before /{id}/* ─────────

@router.get("/stats")
async def get_anomaly_stats():
    """Return aggregate counts and total CO2e saved."""
    if not db.is_connected():
        await db.connect()

    all_anomalies = await db.anomaly.find_many()
    total = len(all_anomalies)
    pending = sum(1 for a in all_anomalies if a.action == "pending")
    resolved = total - pending
    total_co2e_saved = round(sum(a.co2eSaved for a in all_anomalies), 2)

    return {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "totalCo2eSaved": total_co2e_saved,
    }


@router.get("/")
async def list_anomalies(status: Optional[str] = None):
    """
    List anomalies ordered by detectedAtUtc descending.
    Use ?status=pending or ?status=resolved to filter.
    """
    if not db.is_connected():
        await db.connect()

    where: dict = {}
    if status == "pending":
        where["action"] = "pending"
    elif status == "resolved":
        where["action"] = {"not": "pending"}

    anomalies = await db.anomaly.find_many(
        where=where,
        order={"detectedAtUtc": "desc"},
    )
    return anomalies


@router.post("/")
async def create_anomaly(body: AnomalyCreate):
    """Inject a new anomaly record (used by admin seed or external integrations)."""
    if not db.is_connected():
        await db.connect()

    anomaly = await db.anomaly.create(
        data={
            "instanceId": body.instanceId,
            "instanceName": body.instanceName,
            "detectedAtUtc": datetime.datetime.now(datetime.timezone.utc),
            "type": body.type,
            "score": body.score,
            "expectedValue": body.expectedValue,
            "actualValue": body.actualValue,
            "action": body.action,
            "co2eSaved": body.co2eSaved,
            "severity": body.severity,
        }
    )
    return anomaly


@router.patch("/{anomaly_id}/action")
async def update_anomaly_action(anomaly_id: int, body: AnomalyActionPatch):
    """
    Update the action field of an anomaly.
    Automatically sets co2eSaved based on the action taken.
    """
    if not db.is_connected():
        await db.connect()

    valid_actions = {"pending", "alerted", "restarted", "auto_killed"}
    if body.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}",
        )

    anomaly = await db.anomaly.find_unique(where={"id": anomaly_id})
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    co2e_saved = CO2E_SAVINGS.get(body.action, 0.0)

    updated = await db.anomaly.update(
        where={"id": anomaly_id},
        data={"action": body.action, "co2eSaved": co2e_saved},
    )
    return updated
