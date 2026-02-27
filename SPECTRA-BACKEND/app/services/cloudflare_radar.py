import os
import httpx
import datetime
import json
from app.db import db
from app.config.settings import settings
from app.config.constants import REGION_TO_ISO, REGION_BASE_LATENCY_MS

CLOUDFLARE_RADAR_URL = "https://api.cloudflare.com/client/v4/radar/performance/iq"


async def fetch_latency_for_region(
    client: httpx.AsyncClient,
    region_code: str,
    token: str,
) -> float:
    """
    Fetch round-trip latency (ms) for a region via Cloudflare Radar.
    Falls back to a preconfigured baseline value when no token is supplied
    or the API call fails — this allows the app to run in demo mode.
    """
    if not token:
        # Demo / CI mode: return stable baseline + small jitter
        baseline = REGION_BASE_LATENCY_MS.get(region_code, 100.0)
        jitter = os.urandom(1)[0] % 10
        return round(baseline + jitter, 1)

    iso_code = REGION_TO_ISO.get(region_code, region_code)
    try:
        response = await client.get(
            CLOUDFLARE_RADAR_URL,
            params={"location": iso_code, "dateRange": "1d"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            # Extract p50 latency from Cloudflare Radar response structure
            p50 = (
                data.get("result", {})
                    .get("summary_0", {})
                    .get("p50", None)
            )
            if p50 is not None:
                return float(p50)
    except Exception as exc:
        print(f"[cloudflare_radar] Latency fetch failed for {region_code}: {exc}")

    # Fall back to baseline if real fetch failed
    return REGION_BASE_LATENCY_MS.get(region_code, 100.0)


async def update_latency_metrics() -> None:
    """Fetch and persist the latest latency for every enabled region."""
    print("[cloudflare_radar] Updating latency metrics...")
    token = settings.cloudflare_api_token
    regions = await db.region.find_many(where={"enabled": True})

    async with httpx.AsyncClient() as client:
        for reg in regions:
            latency = await fetch_latency_for_region(client, reg.code, token)
            await db.latencymetric.create(
                data={
                    "regionCode": reg.code,
                    "timestampUtc": datetime.datetime.now(datetime.timezone.utc),
                    "latencyMs": latency,
                    "source": "cloudflare_radar",
                    "rawJson": json.dumps({
                        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }),
                }
            )
    print("[cloudflare_radar] Latency update complete.")


async def get_latest_latency(region_code: str) -> float:
    """Return the most recently stored latency (ms) for a region."""
    latest = await db.latencymetric.find_first(
        where={"regionCode": region_code},
        order={"timestampUtc": "desc"},
    )
    return latest.latencyMs if latest else REGION_BASE_LATENCY_MS.get(region_code, 0.0)
