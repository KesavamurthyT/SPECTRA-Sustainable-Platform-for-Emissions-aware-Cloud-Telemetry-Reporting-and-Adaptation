"""
app/config/constants.py
-----------------------
Static domain constants for SPECTRA.

These values describe the physical/logical world (AWS regions, EC2 instance
power profiles, carbon intensity averages, etc.) and should only change when
the supported region set or hardware models change — NOT in response to user
configuration.  Runtime user preferences belong in app/config/settings.py or
the database Setting model.
"""

# ========================================================================== #
# Regions                                                                      #
# ========================================================================== #

# Master list of supported cloud regions.
# Each entry maps the short region code (used as Prisma FK) to a display name.
# Add new regions here; seeds and CSV importer will pick them up automatically.
REGIONS: list[dict] = [
    {"code": "IN", "displayName": "Mumbai (India)"},
    {"code": "SE", "displayName": "Stockholm (Sweden)"},
    {"code": "US", "displayName": "Virginia (US)"},
    {"code": "IE", "displayName": "Dublin (Ireland)"},
    {"code": "JP", "displayName": "Tokyo (Japan)"},
]

# Maps SPECTRA region code → ISO 3166-1 alpha-2 country code used by
# Cloudflare Radar and ElectricityMaps APIs.
REGION_TO_ISO: dict[str, str] = {r["code"]: r["code"] for r in REGIONS}

# Keywords used to identify a region from a CSV filename during import.
# Order matters — more specific keywords should come first.
REGION_KEYWORDS: dict[str, list[str]] = {
    "IN": ["IN-", "_IN_", "India", "Mumbai"],
    "SE": ["SE-", "_SE_", "Sweden", "Stockholm"],
    "US": ["US-", "_US_", "United States", "USA", "Virginia"],
    "IE": ["IE-", "_IE_", "Ireland", "Dublin"],
    "JP": ["JP-", "_JP_", "Japan", "Tokyo"],
}

# Fallback latency (ms) used when Cloudflare token is absent or the API call
# fails; represents approximate round-trip time from a typical EU client.
REGION_BASE_LATENCY_MS: dict[str, float] = {
    "US": 20.0,
    "IE": 80.0,
    "SE": 90.0,
    "JP": 150.0,
    "IN": 180.0,
}

# Average grid carbon intensity (gCO2e/kWh) per region.
# Used for CO2e estimation when live ElectricityMaps data is unavailable.
# Sources: ElectricityMaps annual averages, 2023–2024.
REGION_CARBON_INTENSITY_G_PER_KWH: dict[str, int] = {
    "IN": 720,   # India         — coal-heavy grid
    "SE": 13,    # Sweden        — mostly hydro + nuclear
    "US": 380,   # US Virginia   — mixed grid
    "IE": 320,   # Ireland       — gas-heavy, growing wind
    "JP": 500,   # Japan         — gas + coal post-Fukushima
}

# ========================================================================== #
# EC2 Instance Types                                                           #
# ========================================================================== #

# Instance types available in SPECTRA seeds and rightsizing logic.
# cost = on-demand USD/hour (us-east-1 pricing, approximate).
INSTANCE_TYPES: list[dict] = [
    {"type": "t3.micro",  "cost": 0.0104},
    {"type": "t3.medium", "cost": 0.0416},
    {"type": "m5.large",  "cost": 0.0960},
    {"type": "c5.large",  "cost": 0.0850},
    {"type": "r5.large",  "cost": 0.1260},
]

# Power consumption models for CO2e estimation.
# baseline = idle watts; perCpu = additional watts per vCPU at 100% utilisation.
# vcpus = number of virtual CPUs for the instance family.
# Reference: Cloud Carbon Footprint methodology, Etsy Cloud Jewels.
POWER_MODELS: dict[str, dict] = {
    "t3.micro":  {"baseline": 15, "perCpu": 4,  "vcpus": 2},
    "t3.medium": {"baseline": 20, "perCpu": 5,  "vcpus": 2},
    "m5.large":  {"baseline": 50, "perCpu": 10, "vcpus": 2},
    "c5.large":  {"baseline": 45, "perCpu": 8,  "vcpus": 2},
    "r5.large":  {"baseline": 55, "perCpu": 12, "vcpus": 2},
}

# Default power model used when an instance type is not in POWER_MODELS.
DEFAULT_POWER_MODEL: dict = {"baseline": 30, "perCpu": 8, "vcpus": 2}

# ========================================================================== #
# Teams                                                                        #
# ========================================================================== #

# Engineering teams used for seeding instances, budgets, and scheduled jobs.
TEAMS: list[str] = ["DataScience", "Backend", "Frontend", "Ops", "ML-Training"]

# ========================================================================== #
# Rightsizing Thresholds                                                       #
# ========================================================================== #

# Maps an overprovisioned instance type to its recommended smaller replacement.
RIGHTSIZING_RECOMMENDATIONS: dict[str, str] = {
    "m5.large":  "t3.medium",
    "c5.large":  "t3.medium",
    "r5.large":  "t3.medium",
    "t3.medium": "t3.micro",
}

# An instance is a rightsizing candidate only when cpu AND memory are below
# these thresholds (percentage).
RIGHTSIZING_CPU_THRESHOLD: float    = 25.0
RIGHTSIZING_MEMORY_THRESHOLD: float = 40.0

# Fraction of current cost and CO2e that is saved after rightsizing.
RIGHTSIZING_SAVING_RATIO: float = 0.45

# ========================================================================== #
# Risk Classification                                                          #
# ========================================================================== #

# An instance is HIGH risk when CPU or memory utilisation exceeds this value.
RISK_HIGH_THRESHOLD: float   = 75.0
# An instance is MEDIUM risk when utilisation is between MEDIUM and HIGH.
RISK_MEDIUM_THRESHOLD: float = 40.0

# ========================================================================== #
# Scheduler / Carbon Forecast                                                  #
# ========================================================================== #

# gCO2e/kWh thresholds for labelling hourly forecast slots.
CARBON_OPTIMAL_THRESHOLD: int = 100   # below → isOptimal = True
CARBON_PEAK_THRESHOLD: int    = 180   # above → isPeak    = True

# ========================================================================== #
# Default Settings (seeded into the Setting DB table on first boot)           #
# ========================================================================== #

DEFAULT_SETTINGS: dict[str, str] = {
    # ---- Alerts & automation ------------------------------------------ #
    "carbonBudgetAlertThreshold":    "90",       # % used before alert fires
    "anomalyDetectionEnabled":       "true",
    "autoMigrateEnabled":            "false",    # safety default: manual only
    "rightsizingConfidenceThreshold":"85",        # minimum confidence to show

    # ---- Defaults ----------------------------------------------------- #
    "defaultRegion":                 "IE",        # greenest default region
    "reportingCurrency":             "USD",
    "simClockEnabled":               "true",

    # ---- AWS (will be overwritten by Settings UI and stored in DB) ---- #
    "awsRoleArn":                    "",
    "awsAccessKeyId":                "",
    "awsSecretAccessKey":            "",
    "awsRegionsToMonitor":           "US,IE,SE",
    "awsCostAllocationTag":          "CostCenter",

    # ---- External APIs ------------------------------------------------ #
    "electricityMapsApiKey":         "",
    "cloudflareApiToken":            "",

    # ---- Notifications ------------------------------------------------ #
    "alertChannel":                  "email",     # email | slack | webhook
    "actionOnAnomaly":               "alert",     # alert | auto_kill | ask

    # ---- Data governance ---------------------------------------------- #
    "dataRetentionDays":             "90",
}
