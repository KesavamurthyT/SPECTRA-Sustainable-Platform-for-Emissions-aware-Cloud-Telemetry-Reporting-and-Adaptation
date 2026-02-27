import datetime
from app.db import db
from app.config.settings import settings


def _parse_sim_start() -> datetime.datetime:
    """Parse the SIM_START env variable into an aware UTC datetime."""
    sim_start_str = settings.sim_start
    # fromisoformat in Python <3.11 does not support trailing 'Z'
    if sim_start_str.endswith("Z"):
        sim_start_str = sim_start_str[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(sim_start_str)


async def get_sim_time() -> datetime.datetime:
    """
    Return the current simulation time.
    Initialises the SimClock row from SIM_START env var on first call.
    """
    clock = await db.simclock.find_first()
    if not clock:
        start_time = _parse_sim_start()
        clock = await db.simclock.create(data={"simNowUtc": start_time})
    return clock.simNowUtc

async def tick_time(hours: int = 1) -> datetime.datetime:
    """
    Advance the simulation clock by *hours* hours.
    Initialises the clock first if it has never been set.
    """
    clock = await db.simclock.find_first()
    if not clock:
        return await get_sim_time()

    new_time = clock.simNowUtc + datetime.timedelta(hours=hours)
    updated_clock = await db.simclock.update(
        where={"id": clock.id},
        data={"simNowUtc": new_time},
    )
    return updated_clock.simNowUtc
