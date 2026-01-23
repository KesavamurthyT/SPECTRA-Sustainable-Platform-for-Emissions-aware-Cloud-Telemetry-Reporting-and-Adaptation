import os
import datetime
from app.db import db
from prisma.models import SimClock

async def get_sim_time() -> datetime.datetime:
    """
    Get the current simulation time.
    If not initialized, initialize it with SIM_START.
    """
    clock = await db.simclock.find_first()
    if not clock:
        sim_start_str = os.getenv("SIM_START", "2024-01-01T00:00:00Z")
        # Handle trailing Z if present for fromisoformat (Python 3.10 support)
        if sim_start_str.endswith("Z"):
            sim_start_str = sim_start_str[:-1] + "+00:00"
        
        start_time = datetime.datetime.fromisoformat(sim_start_str)
        clock = await db.simclock.create(
            data={
                "simNowUtc": start_time
            }
        )
    return clock.simNowUtc

async def tick_time(hours: int = 1) -> datetime.datetime:
    """
    Advance the simulation time by N hours.
    """
    clock = await db.simclock.find_first()
    # Ensure initialized
    if not clock:
        return await get_sim_time()
    
    new_time = clock.simNowUtc + datetime.timedelta(hours=hours)
    
    updated_clock = await db.simclock.update(
        where={"id": clock.id},
        data={"simNowUtc": new_time}
    )
    return updated_clock.simNowUtc
