"""API base-URL constants for the USGS water data services."""

# NWIS daily-values endpoint — suitable for any historical date range
USGS_DV_API_BASE = "https://nwis.waterservices.usgs.gov/nwis/dv/"

# NWIS instantaneous-values endpoint — 15-min data, last ~120 days only
USGS_IV_API_BASE = "https://waterservices.usgs.gov/nwis/iv/"

# Real-Time Flood Impacts API
RTFI_API_BASE = "https://api.waterdata.usgs.gov/rtfi-api"

# OGC API — monitoring locations and reference metadata
OGC_API_BASE = "https://api.waterdata.usgs.gov/ogcapi/v0"
