from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db import db
from app.routers import admin, regions, optimizer, migration
from app.services.sim_clock import tick_time, get_sim_time
from app.services.cloudflare_radar import update_latency_metrics

# Scheduler setup
scheduler = AsyncIOScheduler()

async def scheduled_tick():
    """Advance simulation time by 1 hour every real hour."""
    try:
        print("Ticking simulation clock...")
        await tick_time()
        print("Tick complete.")
    except Exception as e:
        print(f"Tick failed: {e}")

async def scheduled_latency_fetch():
    """Fetch latency every 6 hours."""
    try:
        print("Fetching latency...")
        await update_latency_metrics()
        print("Latency fetch complete.")
    except Exception as e:
        print(f"Latency fetch failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    
    # Initialize DB (check connection)
    if not db.is_connected():
        await db.connect()
    
    # Initialize Clock if missing
    await get_sim_time()
    
    # Initial Latency Fetch if DB is empty
    latency_count = await db.latencymetric.count()
    if latency_count == 0:
        print("Latency table empty, performing initial fetch...")
        await update_latency_metrics()
    
    # Start Scheduler
    scheduler.add_job(scheduled_tick, 'interval', hours=1) # Every real hour
    scheduler.add_job(scheduled_latency_fetch, 'interval', hours=6)
    scheduler.start()
    
    yield
    
    # Shutdown
    print("Shutting down...")
    scheduler.shutdown()
    if db.is_connected():
        await db.disconnect()

app = FastAPI(title="Region Optimizer Backend", lifespan=lifespan)

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8010",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(admin.router)
app.include_router(regions.router)
app.include_router(optimizer.router)
app.include_router(migration.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
