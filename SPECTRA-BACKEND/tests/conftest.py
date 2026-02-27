"""
tests/conftest.py
-----------------
Shared pytest fixtures for the SPECTRA backend test suite.
"""

import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    """Synchronous HTTP client pointed at the running local server."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="session")
async def async_client() -> httpx.AsyncClient:
    """Async HTTP client for use with pytest-anyio."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c
