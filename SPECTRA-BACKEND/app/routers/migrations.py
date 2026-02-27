from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db
import datetime

router = APIRouter(prefix="/api/migrations", tags=["migrations"])


@router.get("/history")
async def get_migration_history(limit: int = 20, offset: int = 0):
    """Return a paginated list of past migration actions."""
    if not db.is_connected():
        await db.connect()

    total = await db.migrationaction.count()
    records = await db.migrationaction.find_many(
        order={"executedAtUtc": "desc"},
        take=limit,
        skip=offset,
    )
    return {"total": total, "limit": limit, "offset": offset, "records": records}

class MigrationRequest(BaseModel):
    fromRegion: str
    toRegion: str
    mode: str = "ALL_RUNNING"

@router.post("/execute")
async def execute_migration(req: MigrationRequest):
    if not db.is_connected(): await db.connect()

    # Validate regions
    from_region = await db.region.find_unique(where={"code": req.fromRegion})
    to_region = await db.region.find_unique(where={"code": req.toRegion})
    
    if not from_region or not to_region:
        raise HTTPException(status_code=400, detail="Invalid source or target region")
        
    if req.fromRegion == req.toRegion:
        raise HTTPException(status_code=400, detail="Source and target regions must be different")

    # Find affected instances
    instances_to_move = await db.instance.find_many(
        where={
            "regionCode": req.fromRegion,
            "status": "RUNNING"
        }
    )
    
    count = len(instances_to_move)
    
    if count > 0:
        # Move them
        # Note: Prisma Client Python update_many syntax
        await db.instance.update_many(
            where={
                "regionCode": req.fromRegion,
                "status": "RUNNING"
            },
            data={
                "regionCode": req.toRegion
            }
        )
        
        # Log action
        await db.migrationaction.create(
            data={
                "fromRegion": req.fromRegion,
                "toRegion": req.toRegion,
                "movedCount": count,
                "executedAtUtc": datetime.datetime.now(datetime.timezone.utc)
            }
        )
        
    return {
        "moved": count,
        "fromRegion": req.fromRegion,
        "toRegion": req.toRegion,
        "executedAtUtc": datetime.datetime.now(datetime.timezone.utc)
    }
