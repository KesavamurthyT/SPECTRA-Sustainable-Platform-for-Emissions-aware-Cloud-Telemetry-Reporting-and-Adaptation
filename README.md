# SPECTRA

**Sustainable Platform for Emissions-aware Cloud Telemetry, Reporting and Adaptation**

SPECTRA is a full-stack carbon intelligence dashboard for cloud infrastructure. It monitors EC2 instances across AWS regions, tracks real-time carbon intensity via ElectricityMaps, detects anomalies, recommends rightsizing, and generates Scope 1/2/3 ESG reports — all in one place.

---

## Repository Structure

```
SPECTRA/
├── SPECTRA-BACKEND/     # FastAPI + Prisma (SQLite) backend
│   ├── app/
│   │   ├── config/      # All env vars and domain constants (single source of truth)
│   │   ├── routers/     # One file per API domain
│   │   └── services/    # Business logic (seeds, sim clock, CSV import, Cloudflare)
│   ├── data/
│   │   └── electricitymaps/   # CSV snapshots for carbon intensity
│   ├── migrations/      # Prisma migration history (committed)
│   ├── tests/           # Pytest test suite
│   ├── schema.prisma    # Database schema
│   ├── .env.example     # Copy to .env and configure
│   └── README.md        # Backend-specific setup guide
│
├── SPECTRA-FRONTEND/    # React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── pages/       # One file per dashboard page
│   │   ├── components/  # Reusable UI components
│   │   ├── lib/api.ts   # Typed API client
│   │   └── data/        # Mock data (replaced by API in Phase 2)
│   └── README.md        # Frontend-specific setup guide
│
├── BACKEND_PLAN.md      # Full backend implementation roadmap
├── FEASIBILITY.md       # AWS integration feasibility analysis
└── README.md            # This file
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python 3.11, FastAPI, Prisma (prisma-client-py) |
| Database | SQLite (dev) — swappable to PostgreSQL via `DATABASE_URL` |
| Carbon data | ElectricityMaps API + local CSV snapshots |
| Latency data | Cloudflare Radar API |
| Cloud data | AWS SDK (boto3) — EC2, CloudWatch, Cost Explorer |
| Scheduling | APScheduler (async background jobs) |

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm / npx | latest |
| Prisma CLI | `npm install -g prisma` |

---

### 1 — Backend

```bash
cd SPECTRA-BACKEND

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — DATABASE_URL default works for local SQLite

# Apply database schema
prisma migrate deploy --schema schema.prisma

# Start the API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal — seed with demo data
curl -X POST http://localhost:8000/api/admin/import
```

API available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

---

### 2 — Frontend

```bash
cd SPECTRA-FRONTEND

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend available at **http://localhost:5173**

> Make sure the backend is running first so API calls resolve correctly.

---

## Pages & Features

| Page | Description | Backend status |
|------|-------------|---------------|
| **Dashboard** | Live CO₂e metrics, scope breakdown, budget overview | 🔄 Phase 2 |
| **Regions** | Carbon intensity, latency, cost per region + migration tool | ✅ Live |
| **Instances** | EC2 rightsizing recommendations with CO₂e and cost savings | 🔄 Phase 2 |
| **Anomalies** | Real-time detection of runaway processes and carbon waste | 🔄 Phase 2 |
| **Budgets** | Per-team carbon budget tracking + CSV chargeback export | 🔄 Phase 2 |
| **Scheduler** | Carbon-aware job scheduling with 24h intensity forecast | 🔄 Phase 2 |
| **Reports** | Scope 1/2/3 ESG report generation and export | 🔄 Phase 2 |
| **Settings** | AWS credentials, ElectricityMaps key, automation config | 🔄 Phase 2 |

---


## Running Tests

```bash
cd SPECTRA-BACKEND

# Ensure the server is running, then:
python -m pytest tests/ -v
```

---


