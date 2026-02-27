SPECTRA Backend

**Sustainable Platform for Emissions-aware Cloud Telemetry, Reporting and Adaptation**

A FastAPI backend that tracks cloud infrastructure carbon emissions, detects anomalies, optimises workload scheduling, and enforces team carbon budgets — backed by a Prisma ORM + SQLite database.

---

## Project Structure

```
SPECTRA-BACKEND/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── db.py                    # Prisma client singleton
│   │
│   ├── config/
│   │   ├── settings.py          # Pydantic-settings (env-driven config)
│   │   └── constants.py         # Domain constants (thresholds, enums, defaults)
│   │
│   ├── routers/
│   │   ├── admin.py             # /api/admin — import, tick, latency fetch
│   │   ├── migrations.py        # /api/migrations — execute & history
│   │   ├── optimizer.py         # /api/optimizer — region ranking
│   │   ├── regions.py           # /api/regions — region list & carbon data
│   │   ├── instances.py         # /api/instances — instance list & optimize
│   │   ├── anomalies.py         # /api/anomalies — anomaly list, stats & actions
│   │   ├── budgets.py           # /api/budgets — team budgets & CSV export
│   │   ├── scheduler.py         # /api/scheduler — jobs & forecast
│   │   ├── dashboard.py         # /api/dashboard — aggregated metrics
│   │   ├── reports.py           # /api/reports — summary, history & export
│   │   └── settings.py          # /api/settings — platform config
│   │
│   └── services/
│       ├── seed.py              # First-boot DB seeder (auto-runs on empty DB)
│       ├── seeds.py             # Legacy seed helpers (used by admin router)
│       ├── sim_clock.py         # Simulation clock get/tick
│       ├── cloudflare_radar.py  # Latency fetching via Cloudflare Radar API
│       └── csv_importer.py      # ElectricityMaps CSV → CarbonIntensityHour
│
├── data/
│   └── electricitymaps/         # Place CSV snapshot files here for import
│       └── *.csv
│
├── migrations/                  # Prisma migration history (do not edit manually)
│
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_health.py           # Health + optimizer endpoint tests
│   └── test_migrations.py       # Migration endpoint tests
│
├── schema.prisma                # Database schema (source of truth)
├── push_mock_data.py            # CLI tool to seed / reset the database
├── requirements.txt             # Python dependencies
├── .env.example                 # Copy this to .env and fill in your values
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
| npm / npx | latest | Run `prisma` commands |

Install the Prisma CLI once globally:

```bash
npm install -g prisma
```

---

## First-Time Setup

```bash
# 1. Navigate to the backend folder
cd SPECTRA-BACKEND

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy the example env file and fill in your values
cp .env.example .env

# 5. Apply the database schema
prisma migrate deploy --schema schema.prisma

# 6. Generate the Prisma Python client
prisma generate --schema schema.prisma

# 7. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server detects an empty database on first boot and **automatically seeds it** with demo data — no manual step required.

The API is live at **http://localhost:8000** and interactive docs are at **http://localhost:8000/docs**.

---

## Running the Server

```bash
# Development (auto-reload on file changes)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Database Seeding

The database is seeded automatically the first time the server starts against an empty database.

To manually seed or reset:

```bash
# Seed if the database is empty (safe to run on an already-seeded DB)
python push_mock_data.py

# Wipe all data and re-seed from scratch
python push_mock_data.py --reset
```

To wipe the database entirely and start fresh:

```bash
# Windows
Remove-Item dev.db
prisma migrate deploy --schema schema.prisma
uvicorn app.main:app --reload --port 8000
# Server auto-seeds on first boot
```

---

## API Endpoints

| Router | Prefix | Description |
|--------|--------|-------------|
| admin | `/api/admin` | Trigger CSV import, sim-clock tick, latency fetch |
| migrations | `/api/migrations` | Execute migrations, view history |
| optimizer | `/api/optimizer` | Rank regions by carbon intensity |
| regions | `/api/regions` | List regions, carbon intensity data |
| instances | `/api/instances` | List instances, optimize, patch |
| anomalies | `/api/anomalies` | List anomalies, stats, resolve/dismiss |
| budgets | `/api/budgets` | Team carbon budgets, CSV export |
| scheduler | `/api/scheduler` | Scheduled jobs, forecast |
| dashboard | `/api/dashboard` | Aggregated live metrics |
| reports | `/api/reports` | Summary, history, CSV export |
| settings | `/api/settings` | Platform configuration |

Full interactive documentation (with request/response schemas) is available at **http://localhost:8000/docs**.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `file:./dev.db` | Prisma database connection string |
| `CSV_DIR` | `data/electricitymaps` | Directory scanned for CSV imports |
| `CLOUDFLARE_API_TOKEN` | — | Token for Cloudflare Radar latency API |
| `SIM_CLOCK_ENABLED` | `true` | Enable/disable the simulation clock |
| `LOG_LEVEL` | `info` | Uvicorn log level |

See `.env.example` for the full list with descriptions.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Database Schema

The schema lives in `schema.prisma`. The ten models are:

| Model | Description |
|-------|-------------|
| `Region` | Cloud regions (code, name, provider, coordinates) |
| `CarbonIntensityHour` | Hourly carbon intensity readings per region |
| `SimClock` | Simulation clock state |
| `LatencyMetric` | Inter-region latency measurements |
| `Instance` | Cloud compute instances with workload metadata |
| `MigrationAction` | Record of cross-region migration events |
| `Anomaly` | Detected carbon/cost/performance anomalies |
| `TeamBudget` | Per-team quarterly carbon budget allocations |
| `ScheduledJob` | Batch/flexible jobs with scheduling recommendations |
| `Setting` | Key-value platform configuration store |

To modify the schema:

```bash
# Edit schema.prisma, then:
prisma migrate dev --schema schema.prisma --name describe_your_change
prisma generate --schema schema.prisma
```