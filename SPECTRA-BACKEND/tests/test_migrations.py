"""
tests/test_migrations.py
------------------------
Tests for the /api/migrations/execute endpoint.

Requires a running server with seeded data:
    cd SPECTRA-BACKEND
    uvicorn app.main:app --reload
    # In another terminal:
    python -m pytest tests/test_migrations.py -v
"""

import httpx
import pytest

BASE_URL = "http://localhost:8000"


def test_migration_execute():
    """
    POST /api/migrations/execute should move RUNNING instances from one region
    to another and return a summary with 'moved', 'fromRegion', 'toRegion'.
    """
    with httpx.Client(timeout=10.0) as client:
        # 1. Find a migration candidate from the optimizer
        regions_resp = client.get(f"{BASE_URL}/api/optimizer/regions")
        assert regions_resp.status_code == 200, "Could not fetch optimizer regions"

        regions = regions_resp.json()
        candidate = next(
            (r for r in regions if r.get("recommendation", {}).get("type") == "MIGRATE"),
            None,
        )

        if candidate is None:
            pytest.skip("No MIGRATE candidates available — seed data may be fully optimised.")

        rec = candidate["recommendation"]
        payload = {
            "fromRegion": candidate["regionCode"],
            "toRegion": rec["targetCode"],
            "mode": "ALL_RUNNING",
        }

        # 2. Execute migration
        mig_resp = client.post(f"{BASE_URL}/api/migrations/execute", json=payload)
        assert mig_resp.status_code == 200, f"Migration failed: {mig_resp.text}"

        body = mig_resp.json()
        assert "moved" in body
        assert "fromRegion" in body
        assert "toRegion" in body
        assert body["fromRegion"] == candidate["regionCode"]
        assert body["toRegion"] == rec["targetCode"]


def test_migration_same_region_rejected():
    """Migrating from a region to itself should return 400."""
    with httpx.Client(timeout=5.0) as client:
        payload = {"fromRegion": "IE", "toRegion": "IE", "mode": "ALL_RUNNING"}
        resp = client.post(f"{BASE_URL}/api/migrations/execute", json=payload)
    assert resp.status_code == 400
