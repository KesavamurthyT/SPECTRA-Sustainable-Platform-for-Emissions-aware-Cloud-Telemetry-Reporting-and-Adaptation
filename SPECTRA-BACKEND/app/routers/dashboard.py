"""
routers/dashboard.py
--------------------
Aggregated dashboard metrics.

GET /api/dashboard/metrics — single endpoint consumed by Dashboard.tsx
"""

from fastapi import APIRouter
from app.db import db
from app.services.sim_clock import get_sim_time
from app.config.constants import REGION_CARBON_INTENSITY_G_PER_KWH, POWER_MODELS, DEFAULT_POWER_MODEL

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

HOURS_PER_MONTH = 24 * 30
KW_PER_W = 1 / 1000


def _scope2_for_region(region_code: str, carbon_intensity: float, instances: list) -> float:
    """
    Scope 2 = Purchased electricity emissions.
    For each instance in the region: power_kw * hours * carbon_intensity / 1000 (→ kg CO2e)
    """
    total = 0.0
    for inst in instances:
        pm = POWER_MODELS.get(inst.instanceType, DEFAULT_POWER_MODEL)
        vcpus = pm.get("vcpus", 2)
        cpu = getattr(inst, "cpuUtilization", 50.0)
        watts = pm["baseline"] + pm["perCpu"] * (cpu / 100) * vcpus
        kwh = (watts * KW_PER_W) * HOURS_PER_MONTH
        total += kwh * carbon_intensity / 1000   # gCO2 → kg CO2e
    return round(total, 2)


@router.get("/metrics")
async def get_dashboard_metrics():
    """
    Aggregate dashboard numbers:
    - co2eToday, co2eMonth, co2eYear, trend
    - budget: quarterly, used, remaining
    - scopes: scope1 (zero — no direct combustion), scope2, scope3
    - savedThisMonth (CO2e from resolved anomalies)
    - anomaliesDetected, instancesOptimized
    - quickActions: pendingOptimizations, activeAnomalies, jobsToReschedule
    """
    if not db.is_connected():
        await db.connect()

    # ── Instances ────────────────────────────────────────────────────────────
    instances = await db.instance.find_many(where={"status": "RUNNING"})

    total_co2e_month = round(sum(i.co2ePerMonth for i in instances), 2)
    co2e_today = round(total_co2e_month / 30, 2)
    co2e_year = round(total_co2e_month * 12, 2)

    # Rightsizing: how many have a pending recommendation
    pending_optimizations = sum(1 for i in instances if i.recommendedType)

    # ── Scope 2 — region-level electricity emissions ─────────────────────────
    sim_now = await get_sim_time()
    regions = await db.region.find_many(where={"enabled": True})
    scope2 = 0.0
    for reg in regions:
        entry = await db.carbonintensityhour.find_first(
            where={"regionCode": reg.code, "timestampUtc": sim_now}
        )
        ci = entry.carbonIntensity if entry else REGION_CARBON_INTENSITY_G_PER_KWH.get(reg.code, 400)
        reg_instances = [i for i in instances if i.regionCode == reg.code]
        scope2 += _scope2_for_region(reg.code, ci, reg_instances)

    scope2 = round(scope2, 2)
    scope3 = round(scope2 * 0.20, 2)   # upstream estimate: 20 % of Scope 2
    scope1 = 0.0                        # no direct combustion in cloud

    # ── Budget ────────────────────────────────────────────────────────────────
    budgets = await db.teambudget.find_many()
    quarterly_allocated = round(sum(b.allocated for b in budgets), 2)
    # Recompute used from live instances
    team_co2e: dict = {}
    for inst in instances:
        team_co2e[inst.team] = team_co2e.get(inst.team, 0.0) + inst.co2ePerMonth
    quarterly_used = round(sum(team_co2e.values()), 2)
    quarterly_remaining = round(max(quarterly_allocated - quarterly_used, 0.0), 2)

    # ── Anomalies ─────────────────────────────────────────────────────────────
    all_anomalies = await db.anomaly.find_many()
    anomalies_detected = len(all_anomalies)
    active_anomalies = sum(1 for a in all_anomalies if a.action == "pending")
    saved_this_month = round(sum(a.co2eSaved for a in all_anomalies), 2)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    jobs_to_reschedule = await db.scheduledjob.count(where={"accepted": False, "flexibility": {"not": "critical"}})

    # ── Trend (placeholder -12.5 %, real impl would compare to prior month) ──
    trend = -12.5

    return {
        "co2eToday": co2e_today,
        "co2eMonth": total_co2e_month,
        "co2eYear": co2e_year,
        "trend": trend,
        "budget": {
            "quarterly": quarterly_allocated,
            "used": quarterly_used,
            "remaining": quarterly_remaining,
        },
        "scopes": {
            "scope1": scope1,
            "scope2": scope2,
            "scope3": scope3,
        },
        "savedThisMonth": saved_this_month,
        "anomaliesDetected": anomalies_detected,
        "instancesOptimized": pending_optimizations,
        "quickActions": {
            "pendingOptimizations": pending_optimizations,
            "activeAnomalies": active_anomalies,
            "jobsToReschedule": jobs_to_reschedule,
        },
    }
