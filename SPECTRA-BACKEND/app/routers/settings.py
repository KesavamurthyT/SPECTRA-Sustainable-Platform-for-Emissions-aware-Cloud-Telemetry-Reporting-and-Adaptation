"""
routers/settings.py
-------------------
Application settings CRUD backed by the `Setting` DB model.

GET  /api/settings                 — return all settings as {key: value}
PUT  /api/settings                 — bulk upsert settings
PATCH /api/settings/{key}          — update a single setting value
POST /api/settings/test-connection — stub: test external API connectivity
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db
from app.config.constants import DEFAULT_SETTINGS

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SingleSettingPatch(BaseModel):
    value: str


class BulkSettingsUpdate(BaseModel):
    settings: dict[str, str]


class TestConnectionRequest(BaseModel):
    service: str   # "aws" | "electricitymaps" | "cloudflare"
    apiKey: str = ""
    roleArn: str = ""


# ─────────── /test-connection must be declared before /{key} ────────────────

@router.post("/test-connection")
async def test_connection(body: TestConnectionRequest):
    """
    Stub endpoint that simulates a connectivity check.
    Returns a success/failure response without making real external calls.
    """
    # In a real implementation you would attempt an API handshake here.
    if not body.service:
        raise HTTPException(status_code=400, detail="service field is required")

    return {
        "service": body.service,
        "status": "ok",
        "message": f"{body.service} connection test passed (demo mode)",
    }


@router.get("/")
async def get_settings():
    """Return all settings as a flat {key: value} dict, seeding defaults if empty."""
    if not db.is_connected():
        await db.connect()

    rows = await db.setting.find_many()

    # Seed defaults if the table is empty
    if not rows:
        for key, value in DEFAULT_SETTINGS.items():
            await db.setting.upsert(
                where={"key": key},
                data={"create": {"key": key, "value": str(value)}, "update": {}},
            )
        rows = await db.setting.find_many()

    return {row.key: row.value for row in rows}


@router.put("/")
async def bulk_update_settings(body: BulkSettingsUpdate):
    """Upsert multiple settings at once."""
    if not db.is_connected():
        await db.connect()

    updated = {}
    for key, value in body.settings.items():
        row = await db.setting.upsert(
            where={"key": key},
            data={
                "create": {"key": key, "value": str(value)},
                "update": {"value": str(value)},
            },
        )
        updated[row.key] = row.value

    return updated


@router.patch("/{key}")
async def update_setting(key: str, body: SingleSettingPatch):
    """Update a single setting by key."""
    if not db.is_connected():
        await db.connect()

    row = await db.setting.upsert(
        where={"key": key},
        data={
            "create": {"key": key, "value": body.value},
            "update": {"value": body.value},
        },
    )
    return {row.key: row.value}
