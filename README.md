# Region Optimizer Backend

FastAPI backend for the Region Optimizer.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Copy `.env.example` to `.env`.
    ```bash
    cp .env.example .env
    ```

3.  **Database Setup**:
    Generate Prisma client and push schema to SQLite.
    ```bash
    prisma generate
    prisma db push
    ```

## Running

Start the development server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.
Docs at `http://localhost:8000/docs`.

## Data Import

1.  Place Electricity Maps CSV files in `data/electricitymaps/`.
2.  Run the import script:
    ```bash
    python scripts/import_electricitymaps_csv.py
    ```
    Or call the admin endpoint:
    ```bash
    curl -X POST http://localhost:8000/api/admin/import
    ```

## Admin Endpoints

- `POST /api/admin/tick`: Advance simulation time manually.
- `POST /api/admin/latency/fetch-now`: Trigger latency fetch from Cloudflare.
