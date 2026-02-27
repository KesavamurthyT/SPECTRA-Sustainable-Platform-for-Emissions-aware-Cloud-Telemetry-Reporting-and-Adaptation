"""
app/services/seed.py
--------------------
First-boot database seeder for SPECTRA.

Called automatically from the FastAPI lifespan when the database is empty
(i.e. Region table has 0 rows).  Can also be invoked directly via the CLI
wrapper at the project root:

    python push_mock_data.py           # seed if empty
    python push_mock_data.py --reset   # wipe then re-seed

Public API
----------
    seed_all()           – idempotent: skips any table that already has rows
    reset_and_reseed()   – wipes transactional tables then calls seed_all()
"""

from __future__ import annotations

import datetime
import random

from app.db import db
from app.config.constants import (
    REGIONS,
    INSTANCE_TYPES,
    TEAMS,
    POWER_MODELS,
    DEFAULT_POWER_MODEL,
    REGION_CARBON_INTENSITY_G_PER_KWH,
    REGION_BASE_LATENCY_MS,
    RIGHTSIZING_RECOMMENDATIONS,
    RIGHTSIZING_CPU_THRESHOLD,
    RIGHTSIZING_MEMORY_THRESHOLD,
    RIGHTSIZING_SAVING_RATIO,
    RISK_HIGH_THRESHOLD,
    RISK_MEDIUM_THRESHOLD,
    DEFAULT_SETTINGS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

UTC = datetime.timezone.utc


def _now() -> datetime.datetime:
    return datetime.datetime.now(UTC)


def _calc_co2e(instance_type: str, region_code: str, cpu_util: float) -> float:
    pm = POWER_MODELS.get(instance_type, DEFAULT_POWER_MODEL)
    vcpus = pm.get("vcpus", 2)
    watts = pm["baseline"] + pm["perCpu"] * (cpu_util / 100) * vcpus
    kwh_per_month = (watts / 1000) * 24 * 30
    carbon_g_per_kwh = REGION_CARBON_INTENSITY_G_PER_KWH.get(region_code, 400)
    return round((kwh_per_month * carbon_g_per_kwh) / 1000, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Diurnal carbon pattern (multipliers indexed by hour 0-23)
# ─────────────────────────────────────────────────────────────────────────────

_DIURNAL = [
    1.15, 1.20, 1.18, 1.10, 1.05, 0.95,   # 00–05
    0.85, 0.75, 0.70, 0.68, 0.70, 0.78,   # 06–11
    0.82, 0.88, 0.90, 0.92, 0.95, 1.00,   # 12–17
    1.05, 1.10, 1.12, 1.14, 1.15, 1.15,   # 18–23
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Regions
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_regions() -> None:
    print("[seed] Regions...")
    for reg in REGIONS:
        await db.region.upsert(
            where={"code": reg["code"]},
            data={
                "create": {"code": reg["code"], "displayName": reg["displayName"], "enabled": True},
                "update": {"displayName": reg["displayName"], "enabled": True},
            },
        )
    print(f"[seed]   {len(REGIONS)} regions upserted.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CarbonIntensityHour  (48 h rolling window, all 5 regions)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_carbon_intensity() -> None:
    count = await db.carbonintensityhour.count()
    if count > 0:
        print(f"[seed] CarbonIntensityHour: {count} rows exist, skipping.")
        return

    print("[seed] CarbonIntensityHour (48 h × 5 regions)...")
    rows = []
    for region in REGIONS:
        code = region["code"]
        base = REGION_CARBON_INTENSITY_G_PER_KWH[code]
        for h in range(48):
            dt = _now().replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=47 - h)
            mult = _DIURNAL[dt.hour]
            intensity = round(base * mult * random.uniform(0.92, 1.08))
            rows.append({
                "regionCode": code,
                "timestampUtc": dt,
                "carbonIntensity": int(intensity),
                "rawRowJson": f'{{"region":"{code}","hour":{h},"source":"seed"}}',
            })

    await db.carbonintensityhour.create_many(data=rows)
    print(f"[seed]   {len(rows)} intensity-hour rows created.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. SimClock
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_sim_clock() -> None:
    existing = await db.simclock.find_first()
    if not existing:
        await db.simclock.create(data={"simNowUtc": _now()})
        print("[seed] SimClock created.")
    else:
        print("[seed] SimClock: exists, skipping.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. LatencyMetric  (12 h × 5 regions)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_latency_metrics() -> None:
    count = await db.latencymetric.count()
    if count > 0:
        print(f"[seed] LatencyMetric: {count} rows exist, skipping.")
        return

    print("[seed] LatencyMetric (12 h × 5 regions)...")
    rows = []
    for region in REGIONS:
        code = region["code"]
        base_ms = REGION_BASE_LATENCY_MS[code]
        for h in range(12):
            dt = _now().replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=11 - h)
            latency = round(base_ms * random.uniform(0.85, 1.25), 1)
            rows.append({
                "regionCode": code,
                "timestampUtc": dt,
                "latencyMs": latency,
                "source": "seed",
                "rawJson": f'{{"region":"{code}","latency_ms":{latency}}}',
            })

    await db.latencymetric.create_many(data=rows)
    print(f"[seed]   {len(rows)} latency metrics created.")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Instances  (75 varied workloads across all teams & regions)
# ─────────────────────────────────────────────────────────────────────────────

_SCENARIOS = [
    # (name_prefix,  status,    cpu_range, mem_range, weight)
    ("web-api",      "RUNNING", (30, 70),  (40, 75),  0.25),
    ("ml-train",     "RUNNING", (75, 98),  (60, 95),  0.20),
    ("etl-worker",   "RUNNING", (10, 30),  (20, 50),  0.20),
    ("data-proc",    "STOPPED", (0,  5),   (0,  10),  0.10),
    ("cache",        "RUNNING", (5,  20),  (55, 85),  0.10),
    ("db-replica",   "RUNNING", (15, 45),  (50, 80),  0.10),
    ("batch-job",    "RUNNING", (8,  25),  (15, 40),  0.05),
]
_SCENARIO_WEIGHTS = [s[4] for s in _SCENARIOS]
_REGION_WEIGHTS   = [0.12, 0.25, 0.30, 0.20, 0.13]   # IN, SE, US, IE, JP

async def _seed_instances() -> None:
    count = await db.instance.count()
    if count > 0:
        print(f"[seed] Instances: {count} rows exist, skipping.")
        return

    print("[seed] Instances (75)...")
    rng = random.Random(42)   # deterministic — same data on every fresh seed
    rows = []

    for i in range(75):
        scenario = rng.choices(_SCENARIOS, weights=_SCENARIO_WEIGHTS)[0]
        s_prefix, status, cpu_range, mem_range, _ = scenario
        r_idx       = rng.choices(range(len(REGIONS)), weights=_REGION_WEIGHTS)[0]
        itype       = rng.choice(INSTANCE_TYPES)
        team        = rng.choice(TEAMS)
        region_code = REGIONS[r_idx]["code"]
        cpu_util    = round(rng.uniform(*cpu_range), 1)
        mem_util    = round(rng.uniform(*mem_range), 1)
        co2e        = _calc_co2e(itype["type"], region_code, cpu_util)

        if cpu_util > RISK_HIGH_THRESHOLD or mem_util > RISK_HIGH_THRESHOLD:
            risk = "high"
        elif cpu_util > RISK_MEDIUM_THRESHOLD or mem_util > RISK_MEDIUM_THRESHOLD:
            risk = "medium"
        else:
            risk = "low"

        recommended_type = RIGHTSIZING_RECOMMENDATIONS.get(itype["type"])
        confidence = potential_savings = cost_savings = None
        if (recommended_type
                and cpu_util < RIGHTSIZING_CPU_THRESHOLD
                and mem_util < RIGHTSIZING_MEMORY_THRESHOLD):
            confidence       = round(rng.uniform(72, 97), 1)
            potential_savings = round(co2e * RIGHTSIZING_SAVING_RATIO, 2)
            cost_savings      = round(itype["cost"] * RIGHTSIZING_SAVING_RATIO * 24 * 30, 2)
        else:
            recommended_type = None

        rows.append({
            "name":              f"{team.lower()}-{s_prefix}-{i + 1:03d}",
            "regionCode":        region_code,
            "instanceType":      itype["type"],
            "costPerHour":       itype["cost"],
            "team":              team,
            "status":            status,
            "cpuUtilization":    cpu_util,
            "memoryUtilization": mem_util,
            "co2ePerMonth":      co2e,
            "recommendedType":   recommended_type,
            "confidence":        confidence,
            "potentialSavings":  potential_savings,
            "costSavings":       cost_savings,
            "risk":              risk,
        })

    await db.instance.create_many(data=rows)
    print(f"[seed]   {len(rows)} instances created.")


# ─────────────────────────────────────────────────────────────────────────────
# 6. MigrationActions
# ─────────────────────────────────────────────────────────────────────────────

_MIGRATIONS = [
    ("US", "SE", 12), ("IN", "SE", 8),  ("JP", "IE", 5),
    ("US", "IE", 7),  ("IN", "US", 3),  ("JP", "SE", 10),
    ("US", "IE", 4),  ("IN", "SE", 6),
]

async def _seed_migration_actions() -> None:
    count = await db.migrationaction.count()
    if count > 0:
        print(f"[seed] MigrationActions: {count} rows exist, skipping.")
        return

    print("[seed] MigrationActions (8)...")
    rows = []
    for src, dst, moved in _MIGRATIONS:
        offset_hours = random.randint(1, 720)
        rows.append({
            "fromRegion":    src,
            "toRegion":      dst,
            "movedCount":    moved,
            "executedAtUtc": _now() - datetime.timedelta(hours=offset_hours),
        })

    await db.migrationaction.create_many(data=rows)
    print(f"[seed]   {len(rows)} migration actions created.")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Anomalies  (20 incidents across all types / severities)
# ─────────────────────────────────────────────────────────────────────────────

_ANOMALY_CONFIGS = [
    ("high_cpu",      "high",   (30, 55), (3.0, 6.0), "auto_killed"),
    ("memory_spike",  "high",   (40, 60), (2.5, 5.0), "restarted"),
    ("network_burst", "medium", (20, 40), (4.0, 8.0), "alerted"),
    ("disk_io",       "medium", (15, 35), (3.0, 7.0), "alerted"),
    ("high_cpu",      "low",    (10, 25), (2.0, 3.5), "pending"),
    ("memory_spike",  "medium", (25, 45), (2.0, 4.0), "pending"),
    ("network_burst", "high",   (50, 80), (2.0, 3.0), "auto_killed"),
    ("disk_io",       "low",    (10, 20), (2.5, 5.0), "alerted"),
    ("high_cpu",      "high",   (60, 80), (1.5, 2.5), "restarted"),
    ("memory_spike",  "low",    (20, 35), (1.5, 3.0), "pending"),
    ("network_burst", "low",    (10, 30), (2.0, 4.0), "alerted"),
    ("disk_io",       "high",   (30, 60), (2.0, 4.0), "auto_killed"),
    ("high_cpu",      "medium", (40, 60), (1.5, 2.5), "restarted"),
    ("memory_spike",  "high",   (55, 75), (1.5, 2.0), "auto_killed"),
    ("network_burst", "medium", (25, 45), (3.0, 6.0), "pending"),
    ("disk_io",       "medium", (20, 40), (2.0, 5.0), "alerted"),
    ("high_cpu",      "low",    (5,  15), (2.0, 3.0), "pending"),
    ("memory_spike",  "low",    (15, 30), (1.5, 2.5), "alerted"),
    ("network_burst", "high",   (40, 70), (2.0, 3.5), "auto_killed"),
    ("disk_io",       "low",    (8,  18), (3.0, 6.0), "pending"),
]

async def _seed_anomalies() -> None:
    count = await db.anomaly.count()
    if count > 0:
        print(f"[seed] Anomalies: {count} rows exist, skipping.")
        return

    instances = await db.instance.find_many(take=20)
    if not instances:
        print("[seed] Anomalies: no instances found — skipping.")
        return

    print("[seed] Anomalies (20)...")
    rows = []
    for i, (atype, severity, exp_range, mult_range, action) in enumerate(_ANOMALY_CONFIGS):
        inst     = instances[i % len(instances)]
        expected = round(random.uniform(*exp_range), 1)
        actual   = round(expected * random.uniform(*mult_range), 1)
        co2e_saved = round(random.uniform(5, 80), 1) if action != "pending" else 0.0
        rows.append({
            "instanceId":    f"i-{inst.id:016x}",
            "instanceName":  inst.name,
            "detectedAtUtc": _now() - datetime.timedelta(minutes=random.randint(5, 1440)),
            "type":          atype,
            "score":         round(random.uniform(0.60, 0.99), 2),
            "expectedValue": expected,
            "actualValue":   actual,
            "action":        action,
            "co2eSaved":     co2e_saved,
            "severity":      severity,
        })

    await db.anomaly.create_many(data=rows)
    print(f"[seed]   {len(rows)} anomalies created.")


# ─────────────────────────────────────────────────────────────────────────────
# 8. TeamBudgets  (3 quarters × 5 teams)
# ─────────────────────────────────────────────────────────────────────────────

_BUDGET_DATA: dict[str, list[tuple]] = {
    "DataScience": [("Q3-2025", 4000.0, 3950.0), ("Q4-2025", 4200.0, 4180.0), ("Q1-2026", 4500.0, 3890.0)],
    "Backend":     [("Q3-2025", 2800.0, 2700.0), ("Q4-2025", 2900.0, 2880.0), ("Q1-2026", 3000.0, 2340.0)],
    "Frontend":    [("Q3-2025", 1200.0, 1100.0), ("Q4-2025", 1400.0, 1390.0), ("Q1-2026", 1500.0,  980.0)],
    "Ops":         [("Q3-2025", 1800.0, 1750.0), ("Q4-2025", 1900.0, 1850.0), ("Q1-2026", 2000.0, 1200.0)],
    "ML-Training": [("Q3-2025", 4800.0, 4790.0), ("Q4-2025", 4900.0, 4880.0), ("Q1-2026", 5000.0, 4750.0)],
}

async def _seed_team_budgets() -> None:
    count = await db.teambudget.count()
    if count > 0:
        print(f"[seed] TeamBudgets: {count} rows exist, skipping.")
        return

    print("[seed] TeamBudgets (15)...")
    rows = [
        {"team": team, "allocated": allocated, "used": used, "quarterYear": quarter}
        for team, quarters in _BUDGET_DATA.items()
        for quarter, allocated, used in quarters
    ]
    await db.teambudget.create_many(data=rows)
    print(f"[seed]   {len(rows)} budget rows created.")


# ─────────────────────────────────────────────────────────────────────────────
# 9. ScheduledJobs
# ─────────────────────────────────────────────────────────────────────────────

_SCHEDULED_JOBS = [
    {"name": "Daily ETL Pipeline",         "team": "DataScience",  "currentSchedule": "09:00 UTC",         "recommendedSchedule": "22:00 UTC",                       "durationHours": 2.0,  "carbonSavings": 52.0, "flexibility": "batch",    "accepted": False},
    {"name": "ML Model Training",          "team": "ML-Training",  "currentSchedule": "14:00 UTC",         "recommendedSchedule": "03:00 UTC",                       "durationHours": 4.0,  "carbonSavings": 68.0, "flexibility": "flexible", "accepted": True},
    {"name": "Database Backup",            "team": "Ops",          "currentSchedule": "00:00 UTC",         "recommendedSchedule": "04:00 UTC",                       "durationHours": 1.0,  "carbonSavings": 23.0, "flexibility": "flexible", "accepted": False},
    {"name": "Weekly Report Generation",   "team": "DataScience",  "currentSchedule": "08:00 UTC Mon",     "recommendedSchedule": "23:00 UTC Sun",                   "durationHours": 1.5,  "carbonSavings": 41.0, "flexibility": "batch",    "accepted": False},
    {"name": "Hourly Metrics Aggregation", "team": "Backend",      "currentSchedule": "Every hour",        "recommendedSchedule": "Every hour (green window 01-05)", "durationHours": 0.25, "carbonSavings": 18.0, "flexibility": "flexible", "accepted": False},
    {"name": "Feature Store Refresh",      "team": "ML-Training",  "currentSchedule": "06:00 UTC",         "recommendedSchedule": "01:00 UTC",                       "durationHours": 3.0,  "carbonSavings": 85.0, "flexibility": "flexible", "accepted": True},
    {"name": "Log Archival",               "team": "Ops",          "currentSchedule": "12:00 UTC",         "recommendedSchedule": "03:00 UTC",                       "durationHours": 0.5,  "carbonSavings": 14.0, "flexibility": "batch",    "accepted": False},
    {"name": "A/B Test Analysis",          "team": "Frontend",     "currentSchedule": "10:00 UTC",         "recommendedSchedule": "22:00 UTC",                       "durationHours": 1.0,  "carbonSavings": 30.0, "flexibility": "batch",    "accepted": False},
]

async def _seed_scheduled_jobs() -> None:
    count = await db.scheduledjob.count()
    if count > 0:
        print(f"[seed] ScheduledJobs: {count} rows exist, skipping.")
        return

    print("[seed] ScheduledJobs (8)...")
    await db.scheduledjob.create_many(data=_SCHEDULED_JOBS)
    print(f"[seed]   {len(_SCHEDULED_JOBS)} jobs created.")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Settings
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_settings() -> None:
    print("[seed] Settings...")
    upserted = 0
    for key, value in DEFAULT_SETTINGS.items():
        await db.setting.upsert(
            where={"key": key},
            data={"create": {"key": key, "value": value}, "update": {}},
        )
        upserted += 1
    print(f"[seed]   {upserted} settings upserted.")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def seed_all() -> None:
    """
    Idempotent seed.  Each section is skipped when its table already has rows,
    so running this multiple times is safe.
    """
    print("[seed] Starting first-boot seed...")
    await _seed_regions()
    await _seed_carbon_intensity()
    await _seed_sim_clock()
    await _seed_latency_metrics()
    await _seed_instances()
    await _seed_migration_actions()
    await _seed_anomalies()
    await _seed_team_budgets()
    await _seed_scheduled_jobs()
    await _seed_settings()
    print("[seed] Seed complete.")


async def reset_and_reseed() -> None:
    """Wipe all transactional tables then run seed_all()."""
    print("[seed] Resetting tables...")
    await db.anomaly.delete_many()
    await db.migrationaction.delete_many()
    await db.scheduledjob.delete_many()
    await db.teambudget.delete_many()
    await db.instance.delete_many()
    await db.latencymetric.delete_many()
    await db.carbonintensityhour.delete_many()
    await db.simclock.delete_many()
    await db.setting.delete_many()
    # Regions are preserved; upsert in seed_all() will refresh them
    print("[seed] Tables cleared (regions preserved).")
    await seed_all()
