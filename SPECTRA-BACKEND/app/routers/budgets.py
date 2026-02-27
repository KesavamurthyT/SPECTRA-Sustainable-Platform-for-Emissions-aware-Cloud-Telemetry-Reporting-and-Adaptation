"""
routers/budgets.py
------------------
Team carbon budget management and chargeback reporting.

GET  /api/budgets              — list all team budgets for the current quarter
POST /api/budgets              — create a new team budget allocation
PUT  /api/budgets/{team}       — update allocated amount for a team
GET  /api/budgets/export       — CSV chargeback report (attachment)
"""

import io
import csv
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.db import db

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _current_quarter() -> str:
    """Return the current quarter string e.g. 'Q1-2025'."""
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year
    quarter = (month - 1) // 3 + 1
    return f"Q{quarter}-{year}"


class BudgetCreate(BaseModel):
    team: str
    allocated: float
    quarterYear: Optional[str] = None


class BudgetUpdate(BaseModel):
    allocated: float


# ───────────────── GET /export must be declared before /{team} ──────────────

@router.get("/export")
async def export_budgets_csv():
    """
    Download a chargeback CSV: team, allocated, used, instances, pct_used.
    """
    if not db.is_connected():
        await db.connect()

    quarter = _current_quarter()
    budgets = await db.teambudget.find_many(where={"quarterYear": quarter})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["team", "quarterYear", "allocated_kg", "used_kg", "instances", "pct_used"])

    for b in budgets:
        # Count instances for this team
        instance_count = await db.instance.count(where={"team": b.team})

        pct = round((b.used / b.allocated * 100), 1) if b.allocated > 0 else 0.0
        writer.writerow([b.team, b.quarterYear, b.allocated, b.used, instance_count, pct])

    output.seek(0)
    filename = f"chargeback_{quarter}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/")
async def list_budgets():
    """
    Return team budgets for the current quarter.
    The `used` field is recomputed live from instance co2ePerMonth grouped by team.
    """
    if not db.is_connected():
        await db.connect()

    quarter = _current_quarter()
    budgets = await db.teambudget.find_many(where={"quarterYear": quarter})

    # Recompute `used` from live instance data
    all_instances = await db.instance.find_many()
    team_co2e: dict[str, float] = {}
    team_count: dict[str, int] = {}
    for inst in all_instances:
        team_co2e[inst.team] = round(team_co2e.get(inst.team, 0.0) + inst.co2ePerMonth, 2)
        team_count[inst.team] = team_count.get(inst.team, 0) + 1

    result = []
    for b in budgets:
        used = team_co2e.get(b.team, 0.0)
        result.append({
            "id": b.id,
            "team": b.team,
            "allocated": b.allocated,
            "used": used,
            "remaining": round(b.allocated - used, 2),
            "instances": team_count.get(b.team, 0),
            "quarterYear": b.quarterYear,
            "pctUsed": round(used / b.allocated * 100, 1) if b.allocated > 0 else 0.0,
        })

    return result


@router.post("/")
async def create_budget(body: BudgetCreate):
    """Create a new budget allocation for a team."""
    if not db.is_connected():
        await db.connect()

    quarter = body.quarterYear or _current_quarter()

    # Check uniqueness
    existing = await db.teambudget.find_first(
        where={"team": body.team, "quarterYear": quarter}
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Budget for {body.team} in {quarter} already exists"
        )

    budget = await db.teambudget.create(
        data={
            "team": body.team,
            "allocated": body.allocated,
            "used": 0.0,
            "quarterYear": quarter,
        }
    )
    return budget


@router.put("/{team}")
async def update_budget(team: str, body: BudgetUpdate):
    """Update the allocated budget for a team in the current quarter."""
    if not db.is_connected():
        await db.connect()

    quarter = _current_quarter()
    existing = await db.teambudget.find_first(
        where={"team": team, "quarterYear": quarter}
    )
    if not existing:
        raise HTTPException(
            status_code=404, detail=f"No budget found for team '{team}' in {quarter}"
        )

    updated = await db.teambudget.update(
        where={"id": existing.id},
        data={"allocated": body.allocated},
    )
    return updated
