import random
import datetime
from app.db import db
from app.config.constants import (
    REGIONS,
    INSTANCE_TYPES,
    TEAMS,
    POWER_MODELS,
    DEFAULT_POWER_MODEL,
    REGION_CARBON_INTENSITY_G_PER_KWH,
    RIGHTSIZING_RECOMMENDATIONS,
    RIGHTSIZING_CPU_THRESHOLD,
    RIGHTSIZING_MEMORY_THRESHOLD,
    RIGHTSIZING_SAVING_RATIO,
    RISK_HIGH_THRESHOLD,
    RISK_MEDIUM_THRESHOLD,
    DEFAULT_SETTINGS,
)


async def seed_regions():
    print("Seeding regions...")
    for reg in REGIONS:
        await db.region.upsert(
            where={"code": reg["code"]},
            data={
                "create": {"code": reg["code"], "displayName": reg["displayName"], "enabled": True},
                "update": {"displayName": reg["displayName"]}
            }
        )

def _calc_co2e(instance_type: str, region_code: str, cpu_util: float) -> float:
    """Estimate monthly kg CO2e for an instance using the SPECTRA power model."""
    pm = POWER_MODELS.get(instance_type, DEFAULT_POWER_MODEL)
    vcpus = pm.get("vcpus", 2)
    watts = pm["baseline"] + pm["perCpu"] * (cpu_util / 100) * vcpus
    kwh_per_month = (watts / 1000) * 24 * 30
    carbon_g_per_kwh = REGION_CARBON_INTENSITY_G_PER_KWH.get(region_code, 400)
    return round((kwh_per_month * carbon_g_per_kwh) / 1000, 2)  # kg CO2e


async def seed_instances():
    count = await db.instance.count()
    if count > 0:
        return

    print("Seeding instances...")
    instances = []
    region_weights = [0.35, 0.1, 0.35, 0.1, 0.1]

    # Instance type pairs for rightsizing recommendations
    rightsizing_map = RIGHTSIZING_RECOMMENDATIONS

    for i in range(50):
        r_idx = random.choices(range(len(REGIONS)), weights=region_weights)[0]
        itype = random.choice(INSTANCE_TYPES)
        team = random.choice(TEAMS)
        region_code = REGIONS[r_idx]["code"]
        cpu_util = round(random.uniform(5, 90), 1)
        mem_util = round(random.uniform(10, 85), 1)
        co2e = _calc_co2e(itype["type"], region_code, cpu_util)

        # Determine risk using centralised thresholds
        if cpu_util > RISK_HIGH_THRESHOLD or mem_util > RISK_HIGH_THRESHOLD:
            risk = "high"
        elif cpu_util > RISK_MEDIUM_THRESHOLD or mem_util > RISK_MEDIUM_THRESHOLD:
            risk = "medium"
        else:
            risk = "low"

        # Generate rightsizing recommendation for low-utilisation instances
        recommended_type = RIGHTSIZING_RECOMMENDATIONS.get(itype["type"])
        confidence = None
        potential_savings = None
        cost_savings = None
        if (recommended_type
                and cpu_util < RIGHTSIZING_CPU_THRESHOLD
                and mem_util < RIGHTSIZING_MEMORY_THRESHOLD):
            confidence = round(random.uniform(75, 97), 1)
            potential_savings = round(co2e * RIGHTSIZING_SAVING_RATIO, 2)
            cost_savings = round(itype["cost"] * RIGHTSIZING_SAVING_RATIO * 24 * 30, 2)
        else:
            recommended_type = None  # only show recommendation when thresholds met

        instances.append({
            "name": f"{team}-{itype['type']}-{i}",
            "regionCode": region_code,
            "instanceType": itype["type"],
            "costPerHour": itype["cost"],
            "team": team,
            "status": "RUNNING" if random.random() > 0.1 else "STOPPED",
            "cpuUtilization": cpu_util,
            "memoryUtilization": mem_util,
            "co2ePerMonth": co2e,
            "recommendedType": recommended_type,
            "confidence": confidence,
            "potentialSavings": potential_savings,
            "costSavings": cost_savings,
            "risk": risk,
        })

    await db.instance.create_many(data=instances)


async def seed_anomalies():
    count = await db.anomaly.count()
    if count > 0:
        return

    print("Seeding anomalies...")
    anomaly_types = ["high_cpu", "memory_spike", "network_burst", "disk_io"]
    actions = ["auto_killed", "restarted", "alerted", "pending"]
    severities = ["low", "medium", "high"]

    # Pull some instance names to reference
    instances = await db.instance.find_many(take=10)
    if not instances:
        return

    anomalies = []
    for i, inst in enumerate(instances[:8]):
        atype = anomaly_types[i % len(anomaly_types)]
        severity = severities[i % len(severities)]
        expected = round(random.uniform(20, 60), 1)
        actual = round(expected * random.uniform(2.5, 8), 1)
        score = round(random.uniform(0.60, 0.99), 2)
        action = "pending" if i % 4 == 3 else actions[i % 3]
        co2e_saved = round(random.uniform(5, 60), 1) if action != "pending" else 0.0
        offset_minutes = random.randint(5, 300)
        anomalies.append({
            "instanceId": f"i-{inst.id:016x}",
            "instanceName": inst.name,
            "detectedAtUtc": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=offset_minutes),
            "type": atype,
            "score": score,
            "expectedValue": expected,
            "actualValue": actual,
            "action": action,
            "co2eSaved": co2e_saved,
            "severity": severity,
        })

    await db.anomaly.create_many(data=anomalies)


async def seed_team_budgets():
    count = await db.teambudget.count()
    if count > 0:
        return

    print("Seeding team budgets...")
    quarter = "Q1-2026"
    budgets = [
        {"team": "DataScience",  "allocated": 4500.0, "used": 3890.0, "quarterYear": quarter},
        {"team": "Backend",      "allocated": 3000.0, "used": 2340.0, "quarterYear": quarter},
        {"team": "Frontend",     "allocated": 1500.0, "used": 980.0,  "quarterYear": quarter},
        {"team": "Ops",          "allocated": 2000.0, "used": 1200.0, "quarterYear": quarter},
        {"team": "ML-Training",  "allocated": 5000.0, "used": 4750.0, "quarterYear": quarter},
    ]
    await db.teambudget.create_many(data=budgets)


async def seed_scheduled_jobs():
    count = await db.scheduledjob.count()
    if count > 0:
        return

    print("Seeding scheduled jobs...")
    jobs = [
        {
            "name": "Daily ETL Pipeline",
            "team": "DataScience",
            "currentSchedule": "09:00 UTC",
            "recommendedSchedule": "22:00 UTC",
            "durationHours": 2.0,
            "carbonSavings": 52.0,
            "flexibility": "batch",
            "accepted": False,
        },
        {
            "name": "ML Model Training",
            "team": "ML-Training",
            "currentSchedule": "14:00 UTC",
            "recommendedSchedule": "03:00 UTC",
            "durationHours": 4.0,
            "carbonSavings": 68.0,
            "flexibility": "flexible",
            "accepted": False,
        },
        {
            "name": "Database Backup",
            "team": "Ops",
            "currentSchedule": "00:00 UTC",
            "recommendedSchedule": "04:00 UTC",
            "durationHours": 1.0,
            "carbonSavings": 23.0,
            "flexibility": "flexible",
            "accepted": False,
        },
        {
            "name": "Report Generation",
            "team": "DataScience",
            "currentSchedule": "08:00 UTC",
            "recommendedSchedule": "23:00 UTC",
            "durationHours": 1.0,
            "carbonSavings": 41.0,
            "flexibility": "batch",
            "accepted": False,
        },
        {
            "name": "Hourly Metrics Aggregation",
            "team": "Backend",
            "currentSchedule": "Every hour",
            "recommendedSchedule": "Every hour (green window)",
            "durationHours": 0.25,
            "carbonSavings": 18.0,
            "flexibility": "flexible",
            "accepted": False,
        },
    ]
    await db.scheduledjob.create_many(data=jobs)


async def seed_settings():
    print("Seeding default settings...")
    for key, value in DEFAULT_SETTINGS.items():
        await db.setting.upsert(
            where={"key": key},
            data={
                "create": {"key": key, "value": value},
                "update": {}  # Do not overwrite existing user-configured values
            }
        )
