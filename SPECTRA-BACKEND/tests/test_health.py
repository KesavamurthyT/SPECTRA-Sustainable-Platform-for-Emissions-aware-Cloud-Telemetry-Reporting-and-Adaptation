"""
tests/test_health.py
--------------------
Tests for basic API availability and health endpoint.

Usage:
    cd SPECTRA-BACKEND
    python -m pytest tests/ -v
"""

import httpx
import pytest

BASE_URL = "http://localhost:8000"


def test_health_endpoint():
    """GET /health should return 200 with status=ok."""
    with httpx.Client(timeout=5.0) as client:
        response = client.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_optimizer_regions():
    """GET /api/optimizer/regions should return a non-empty list."""
    with httpx.Client(timeout=5.0) as client:
        response = client.get(f"{BASE_URL}/api/optimizer/regions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "regionCode" in first
        assert "carbonIntensity" in first
        assert "recommendation" in first


def test_signals_latest():
    """GET /api/regions/signals/latest should return simNowUtc and regions."""
    with httpx.Client(timeout=5.0) as client:
        response = client.get(f"{BASE_URL}/api/regions/signals/latest")
    assert response.status_code == 200
    body = response.json()
    assert "simNowUtc" in body
    assert "regions" in body
