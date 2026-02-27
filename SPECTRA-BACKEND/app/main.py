from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db import db
from app.config.settings import settings
from app.routers import admin, regions, optimizer, migrations
from app.services.sim_clock import tick_time, get_sim_time
from app.services.cloudflare_radar import update_latency_metrics

# ---------------------------------------------------------------------------- #
# Background Scheduler                                                           #
# ---------------------------------------------------------------------------- #
scheduler = AsyncIOScheduler()


async def _scheduled_tick() -> None:
    """Advance the simulation clock by 1 hour on each real-world tick interval."""
    try:
        print("[scheduler] Ticking simulation clock...")
        await tick_time()
        print("[scheduler] Tick complete.")
    except Exception as exc:
        print(f"[scheduler] Tick failed: {exc}")


async def _scheduled_latency_fetch() -> None:
    """Refresh Cloudflare Radar latency data on a configurable interval."""
    try:
        print("[scheduler] Fetching latency metrics...")
        await update_latency_metrics()
        print("[scheduler] Latency fetch complete.")
    except Exception as exc:
        print(f"[scheduler] Latency fetch failed: {exc}")


# ---------------------------------------------------------------------------- #
# Application Lifespan                                                           #
# ---------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] Starting {settings.app_title} v{settings.app_version} ({settings.app_env})")

    if not db.is_connected():
        await db.connect()

    # Initialise the simulation clock if this is the first boot
    await get_sim_time()

    # Perform initial latency fetch if the table is empty
    if await db.latencymetric.count() == 0:
        print("[startup] Latency table empty — performing initial fetch...")
        await update_latency_metrics()

    # Schedule recurring background jobs using intervals from .env
    scheduler.add_job(
        _scheduled_tick,
        "interval",
        hours=settings.sim_tick_interval_hours,
        id="sim_clock_tick",
    )
    scheduler.add_job(
        _scheduled_latency_fetch,
        "interval",
        hours=settings.latency_fetch_interval_hours,
        id="latency_fetch",
    )
    scheduler.start()
    print(
        f"[startup] Scheduler started — "
        f"clock tick every {settings.sim_tick_interval_hours}h, "
        f"latency fetch every {settings.latency_fetch_interval_hours}h"
    )

    yield

    # Graceful shutdown
    print("[shutdown] Stopping scheduler and closing DB connection...")
    scheduler.shutdown()
    if db.is_connected():
        await db.disconnect()
    print("[shutdown] Done.")


# ---------------------------------------------------------------------------- #
# FastAPI Application                                                            #
# ---------------------------------------------------------------------------- #
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — origins are configured via CORS_ORIGINS in .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------- #
# Routers                                                                       #
# ---------------------------------------------------------------------------- #
app.include_router(admin.router)
app.include_router(regions.router)
app.include_router(optimizer.router)
app.include_router(migrations.router)


@app.get("/health", tags=["health"])
def health_check():
    """Liveness probe — returns 200 when the API is running."""
    return {
        "status": "ok",
        "app": settings.app_title,
        "version": settings.app_version,
        "env": settings.app_env,
    }
