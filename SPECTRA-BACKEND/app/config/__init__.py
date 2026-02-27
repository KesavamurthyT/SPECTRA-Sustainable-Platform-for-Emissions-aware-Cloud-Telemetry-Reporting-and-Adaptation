"""
app/config — Centralised configuration and domain constants for SPECTRA.

Submodules
----------
settings  : All environment variables loaded from .env (via pydantic-settings).
constants : Static domain values (region codes, instance types, thresholds, etc.)
"""

from app.config.settings import settings
from app.config.constants import (
    REGIONS,
    REGION_TO_ISO,
    REGION_KEYWORDS,
    REGION_BASE_LATENCY_MS,
    REGION_CARBON_INTENSITY_G_PER_KWH,
    INSTANCE_TYPES,
    POWER_MODELS,
    TEAMS,
    RIGHTSIZING_RECOMMENDATIONS,
    RIGHTSIZING_CPU_THRESHOLD,
    RIGHTSIZING_MEMORY_THRESHOLD,
    RIGHTSIZING_SAVING_RATIO,
    CARBON_OPTIMAL_THRESHOLD,
    CARBON_PEAK_THRESHOLD,
    RISK_HIGH_THRESHOLD,
    RISK_MEDIUM_THRESHOLD,
)

__all__ = [
    "settings",
    "REGIONS",
    "REGION_TO_ISO",
    "REGION_KEYWORDS",
    "REGION_BASE_LATENCY_MS",
    "REGION_CARBON_INTENSITY_G_PER_KWH",
    "INSTANCE_TYPES",
    "POWER_MODELS",
    "TEAMS",
    "RIGHTSIZING_RECOMMENDATIONS",
    "RIGHTSIZING_CPU_THRESHOLD",
    "RIGHTSIZING_MEMORY_THRESHOLD",
    "RIGHTSIZING_SAVING_RATIO",
    "CARBON_OPTIMAL_THRESHOLD",
    "CARBON_PEAK_THRESHOLD",
    "RISK_HIGH_THRESHOLD",
    "RISK_MEDIUM_THRESHOLD",
]
