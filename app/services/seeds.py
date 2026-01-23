import random
from app.db import db

REGIONS = [
    {"code": "IN", "displayName": "Mumbai (India)"},
    {"code": "SE", "displayName": "Stockholm (Sweden)"},
    {"code": "US", "displayName": "Virginia (US)"},
    {"code": "IE", "displayName": "Dublin (Ireland)"},
    {"code": "JP", "displayName": "Tokyo (Japan)"}
]

INSTANCE_TYPES = [
    {"type": "t3.micro", "cost": 0.0104},
    {"type": "t3.medium", "cost": 0.0416},
    {"type": "m5.large", "cost": 0.096},
    {"type": "c5.large", "cost": 0.085},
    {"type": "r5.large", "cost": 0.126},
]

TEAMS = ["DataScience", "Backend", "Frontend", "Ops", "ML-Training"]

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

async def seed_instances():
    count = await db.instance.count()
    if count > 0:
        return

    print("Seeding instances...")
    instances = []
    region_weights = [0.35, 0.1, 0.35, 0.1, 0.1]
    
    for i in range(50):
        r_idx = random.choices(range(len(REGIONS)), weights=region_weights)[0]
        itype = random.choice(INSTANCE_TYPES)
        team = random.choice(TEAMS)
        instances.append({
            "name": f"{team}-{itype['type']}-{i}",
            "regionCode": REGIONS[r_idx]["code"],
            "instanceType": itype['type'],
            "costPerHour": itype['cost'],
            "team": team,
            "status": "RUNNING" if random.random() > 0.1 else "STOPPED"
        })
        
    await db.instance.create_many(data=instances)
