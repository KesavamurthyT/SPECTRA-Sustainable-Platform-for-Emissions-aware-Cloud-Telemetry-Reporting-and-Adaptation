"""
routers/instances.py
--------------------
Instance management and rightsizing recommendations.

GET  /api/instances           — list all instances (supports ?region=, ?risk=, ?search=)
POST /api/instances/{id}/optimize — apply rightsizing recommendation
PATCH /api/instances/{id}     — update instance fields
"""

import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db
from app.config.constants import RIGHTSIZING_RECOMMENDATIONS

router = APIRouter(prefix="/api/instances", tags=["instances"])


# ─────────────────────────────── Pydantic models ────────────────────────────

class InstancePatch(BaseModel):
    team: Optional[str] = None
    status: Optional[str] = None
    regionCode: Optional[str] = None


# ─────────────────────────────────── Routes ─────────────────────────────────

@router.get("/")
async def list_instances(
    region: Optional[str] = None,
    risk: Optional[str] = None,
    search: Optional[str] = None,
):
    """Return all instances, optionally filtered by region, risk level, or name search."""
    if not db.is_connected():
        await db.connect()

    where: dict = {}
    if region:
        where["regionCode"] = region
    if risk:
        where["risk"] = risk

    instances = await db.instance.find_many(where=where, order={"id": "asc"})

    if search:
        search_lower = search.lower()
        instances = [
            i for i in instances
            if search_lower in i.name.lower() or search_lower in i.instanceType.lower()
        ]

    return instances


@router.post("/{instance_id}/optimize")
async def optimize_instance(instance_id: int):
    """
    Apply the rightsizing recommendation for a given instance.
    Updates instanceType and costPerHour, clears the recommendation fields,
    and logs a MigrationAction record.
    """
    if not db.is_connected():
        await db.connect()

    instance = await db.instance.find_unique(where={"id": instance_id})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    if not instance.recommendedType:
        raise HTTPException(status_code=400, detail="No recommendation available for this instance")

    # Derive new cost from instance type constants
    from app.config.constants import INSTANCE_TYPES
    new_type = instance.recommendedType
    type_info = next((t for t in INSTANCE_TYPES if t["type"] == new_type), None)
    new_cost = type_info["cost"] if type_info else instance.costPerHour * 0.5

    # Recalculate estimated CO2e after downsizing (use savings ratio)
    new_co2e = round(instance.co2ePerMonth - (instance.potentialSavings or 0), 2)

    updated = await db.instance.update(
        where={"id": instance_id},
        data={
            "instanceType": new_type,
            "costPerHour": new_cost,
            "co2ePerMonth": max(new_co2e, 0.0),
            "recommendedType": None,
            "confidence": None,
            "potentialSavings": None,
            "costSavings": None,
            "risk": "low",
        },
    )

    # Log the action as a migration action (region unchanged means it's in-place)
    await db.migrationaction.create(
        data={
            "fromRegion": instance.regionCode,
            "toRegion": instance.regionCode,
            "movedCount": 1,
            "executedAtUtc": datetime.datetime.now(datetime.timezone.utc),
        }
    )

    return {"optimized": True, "instance": updated}


@router.patch("/{instance_id}")
async def patch_instance(instance_id: int, body: InstancePatch):
    """Update mutable fields on an instance."""
    if not db.is_connected():
        await db.connect()

    instance = await db.instance.find_unique(where={"id": instance_id})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await db.instance.update(where={"id": instance_id}, data=update_data)
    return updated
