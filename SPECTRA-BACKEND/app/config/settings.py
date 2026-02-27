"""
app/config/settings.py
----------------------
All environment variables for SPECTRA, loaded from the .env file at startup.

New developers: copy .env.example to .env and fill in the required values.
Every setting has a sensible default so the app runs in demo mode without
configuration — only external API calls (AWS, Cloudflare, ElectricityMaps)
require real keys.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # silently ignore unknown env vars
        case_sensitive=False,    # DATABASE_URL == database_url
    )

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    database_url: str = "file:./dev.db"

    # ------------------------------------------------------------------ #
    # Simulation Clock                                                     #
    # ------------------------------------------------------------------ #
    # ISO-8601 UTC datetime that the sim clock starts at on first boot.
    sim_start: str = "2024-01-01T00:00:00Z"
    # How many real hours between automatic sim-clock ticks.
    sim_tick_interval_hours: int = 1
    # How many real hours between automatic Cloudflare latency refreshes.
    latency_fetch_interval_hours: int = 6

    # ------------------------------------------------------------------ #
    # CSV Data Import                                                      #
    # ------------------------------------------------------------------ #
    # Directory that contains ElectricityMaps CSV snapshot files.
    csv_dir: str = "./data/electricitymaps"

    # ------------------------------------------------------------------ #
    # Cloudflare Radar (latency data)                                      #
    # ------------------------------------------------------------------ #
    cloudflare_api_token: str = ""
    cloudflare_account_id: str = ""

    # ------------------------------------------------------------------ #
    # AWS Integration (overrides DB Settings when present)                #
    # ------------------------------------------------------------------ #
    aws_role_arn: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_regions_to_monitor: str = "US,IE,SE"
    aws_cost_allocation_tag: str = "CostCenter"

    # ------------------------------------------------------------------ #
    # ElectricityMaps (live carbon intensity)                              #
    # ------------------------------------------------------------------ #
    electricity_maps_api_key: str = ""

    # ------------------------------------------------------------------ #
    # FastAPI Application                                                  #
    # ------------------------------------------------------------------ #
    app_title: str = "SPECTRA API"
    app_description: str = (
        "Sustainable Platform for Emissions-aware Cloud Telemetry, "
        "Reporting and Adaptation"
    )
    app_version: str = "1.0.0"
    app_env: str = "development"   # development | staging | production

    # ------------------------------------------------------------------ #
    # CORS — comma-separated list of allowed origins                      #
    # ------------------------------------------------------------------ #
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def aws_regions_list(self) -> list[str]:
        """Parse the comma-separated AWS_REGIONS_TO_MONITOR into a list."""
        return [r.strip() for r in self.aws_regions_to_monitor.split(",") if r.strip()]


@lru_cache
def get_settings() -> AppSettings:
    """
    Return a cached singleton of AppSettings.
    Using lru_cache means .env is only read once per process.
    """
    return AppSettings()


# Convenience module-level singleton used throughout the app:
#   from app.config.settings import settings
settings: AppSettings = get_settings()
