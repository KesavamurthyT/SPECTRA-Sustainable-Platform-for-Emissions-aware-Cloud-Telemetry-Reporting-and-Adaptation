# SPECTRA Backend

**Sustainable Platform for Emissions-aware Cloud Telemetry, Reporting and Adaptation**

FastAPI backend powering the SPECTRA carbon monitoring dashboard. Connects to AWS (EC2, CloudWatch, Cost Explorer), ElectricityMaps, and Cloudflare Radar to provide real-time carbon intelligence for cloud workloads.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [First-Time Setup](#first-time-setup)
4. [Running the Server](#running-the-server)
5. [Seeding the Database](#seeding-the-database)
6. [Environment Variables](#environment-variables)
7. [Demo Mode vs. Live Mode](#demo-mode-vs-live-mode)
8. [API Overview](#api-overview)
9. [Running Tests](#running-tests)
10. [Adding a New Region](#adding-a-new-region)
11. [Project Architecture](#project-architecture)

---

## Project Structure

```
SPECTRA-BACKEND/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan, CORS, router wiring
│   ├── db.py                    # Prisma client singleton
│   │
│   ├── config/                  # ★ All configuration lives here
│   │   ├── __init__.py          # Re-exports settings + all constants
│   │   ├── settings.py          # Env-var config (reads from .env via pydantic-settings)
│   │   └── constants.py         # Static domain constants (regions, power models, thresholds)
│   │
│   ├── routers/                 # One file per API domain
│   │   ├── admin.py             # /api/admin  — import, tick, latency fetch
│   │   ├── regions.py           # /api/regions — carbon signals, latency
│   │   ├── optimizer.py         # /api/optimizer — region ranking
│   │   └── migrations.py        # /api/migrations — execute & history
│   │
│   └── services/                # Business logic (no HTTP concerns)
│       ├── seeds.py             # DB seed functions for all models
│       ├── sim_clock.py         # Simulation clock get/tick
│       ├── cloudflare_radar.py  # Latency fetching via Cloudflare Radar API
│       └── csv_importer.py      # ElectricityMaps CSV → CarbonIntensityHour
│
├── data/
│   └── electricitymaps/         # Place CSV snapshot files here for import
│       └── *.csv
│
├── migrations/                  # Prisma migration history (auto-generated, do not edit)
│
├── tests/                       # Pytest test suite
│   ├── conftest.py              # Shared fixtures
│   ├── test_health.py           # Health + optimizer endpoint tests
│   └── test_migrations.py       # Migration endpoint tests
│
├── schema.prisma                # Database schema (source of truth)
├── requirements.txt             # Python dependencies
├── .env.example                 # ★ Copy this to .env and fill in your values
├── .env                         # Your local config (git-ignored)
├── BACKEND_PLAN.md              # Full implementation roadmap
└── FEASIBILITY.md               # AWS integration feasibility analysis
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Runtime |
| pip | latest | Package install |
| Node.js | 18+ | Prisma CLI (runs on Node) |
| npm or npx | latest | Run `prisma` commands |

Install Prisma CLI globally (one-time):

```bash
npm install -g prisma
```

---

## First-Time Setup

```bash
# 1. Clone the repo and navigate to the backend
cd SPECTRA-BACKEND

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy the example env file and edit it
cp .env.example .env
# Open .env and set at minimum: DATABASE_URL (default is fine for SQLite)

# 5. Apply the database schema
prisma migrate dev --schema schema.prisma

# 6. Generate the Prisma Python client
prisma generate --schema schema.prisma

# 7. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. In a separate terminal — seed the database with demo data
curl -X POST http://localhost:8000/api/admin/import
```

The API is now running at **http://localhost:8000** and the interactive docs are at **http://localhost:8000/docs**.

---

## Running the Server

```bash
# Development (with auto-reload on file changes)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Seeding the Database

All seed functions are triggered by a single admin endpoint. This is safe to call multiple times — each function checks for existing data before inserting.

```bash
curl -X POST http://localhost:8000/api/admin/import
```

What this does:
1. Seeds 5 cloud regions (`Region` table)
2. Imports ElectricityMaps CSV files from `CSV_DIR` → `CarbonIntensityHour`
3. Seeds 50 demo EC2 instances with realistic utilisation data
4. Seeds demo anomalies
5. Seeds team carbon budgets for Q1-2026
6. Seeds scheduled job recommendations
7. Seeds default app settings (only fills missing keys, never overwrites)

To reset and re-seed from scratch:

```bash
# Delete the database and re-migrate
del dev.db                          # Windows
# rm dev.db                         # macOS/Linux
prisma migrate dev --schema schema.prisma
curl -X POST http://localhost:8000/api/admin/import
```

---

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `file:./dev.db` | Yes | SQLite or PostgreSQL connection string |
| `SIM_START` | `2024-01-01T00:00:00Z` | No | UTC datetime the simulation clock starts at |
| `SIM_TICK_INTERVAL_HOURS` | `1` | No | How often (hours) the sim clock auto-advances |
| `LATENCY_FETCH_INTERVAL_HOURS` | `6` | No | How often (hours) Cloudflare latency refreshes |
| `CSV_DIR` | `./data/electricitymaps` | No | Directory containing ElectricityMaps CSVs |
| `CLOUDFLARE_API_TOKEN` | _(empty)_ | No | Enables live latency data; uses baseline fallbacks if absent |
| `ELECTRICITY_MAPS_API_KEY` | _(empty)_ | No | Enables live carbon intensity; uses CSV snapshots if absent |
| `AWS_ROLE_ARN` | _(empty)_ | No | IAM Role ARN for AWS data (can be set via Settings UI) |
| `AWS_ACCESS_KEY_ID` | _(empty)_ | No | AWS access key (can be set via Settings UI) |
| `AWS_SECRET_ACCESS_KEY` | _(empty)_ | No | AWS secret key (can be set via Settings UI) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | No | Comma-separated allowed frontend origins |
| `APP_ENV` | `development` | No | `development` \| `staging` \| `production` |

---

## Demo Mode vs. Live Mode

SPECTRA is designed to run fully without any external API keys — useful for development, CI, and demos.

| Feature | Demo mode (no keys) | Live mode (with keys) |
|---------|--------------------|-----------------------|
| Carbon intensity | From imported CSV files | ElectricityMaps live API |
| Latency data | Preconfigured baseline values | Cloudflare Radar API |
| EC2 instances | Seeded fake instances (50) | Fetched from AWS EC2 |
| CPU/memory utilisation | Randomly generated | AWS CloudWatch metrics |
| Cost data | Estimated from instance type | AWS Cost Explorer |

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/api/optimizer/regions` | Ranked regions with carbon, latency, cost, recommendation |
| GET | `/api/regions/signals/latest` | Latest carbon intensity per region + sim clock |
| GET | `/api/regions/signals/history` | Historical carbon intensity for a region |
| GET | `/api/regions/latency/latest` | Latest latency per region |
| GET | `/api/regions/latency/history` | Historical latency for a region |
| POST | `/api/migrations/execute` | Move workloads from one region to another |
| POST | `/api/admin/import` | Seed/import all data |
| POST | `/api/admin/tick` | Advance simulation clock |
| POST | `/api/admin/latency/fetch-now` | Trigger immediate latency refresh |

Full interactive docs: **http://localhost:8000/docs**

---

## Running Tests

Requires the server to be running locally on port 8000 with seeded data.

```bash
# Install pytest (already in requirements if you ran pip install -r requirements.txt)
pip install pytest

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_health.py -v
```

---

## Adding a New Region

All region configuration is centralised in **`app/config/constants.py`**. To add a new region:

1. Add an entry to `REGIONS`:
   ```python
   {"code": "AU", "displayName": "Sydney (Australia)"},
   ```

2. Add a fallback latency to `REGION_BASE_LATENCY_MS`:
   ```python
   "AU": 160.0,
   ```

3. Add an annual average carbon intensity to `REGION_CARBON_INTENSITY_G_PER_KWH`:
   ```python
   "AU": 550,   # Australia — coal-heavy grid
   ```

4. Add keywords for CSV filename detection to `REGION_KEYWORDS`:
   ```python
   "AU": ["AU-", "_AU_", "Australia", "Sydney"],
   ```

5. Drop the corresponding ElectricityMaps CSV into `data/electricitymaps/` and re-run:
   ```bash
   curl -X POST http://localhost:8000/api/admin/import
   ```

No other code changes are needed — seeds, importer, and optimizer all read from constants dynamically.

---

## Project Architecture

```
Request → FastAPI Router → Service function → Prisma DB
                              ↑
                        app/config/
                        settings.py  (env vars)
                        constants.py (domain values)
```

- **Routers** handle HTTP concerns only (validation, response shape).
- **Services** contain all business logic and are importable without HTTP context.
- **Config** is the single source of truth — no `os.getenv()` calls outside `app/config/settings.py`.
- **Constants** change only when the physical model changes (new region, new instance type), not in response to user config.
