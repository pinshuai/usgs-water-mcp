"""Tools for querying USGS NWIS water data (daily and real-time)."""

from __future__ import annotations

from typing import Any, Dict

from usgs_water_mcp.client import get_water_data_values
from usgs_water_mcp.config import USGS_IV_API_BASE
from usgs_water_mcp.server import mcp


@mcp.tool()
async def fetch_usgs_data(
    sites: str,
    parameter_codes: str = "",
    start_date: str = "",
    end_date: str = "",
    stat_codes: str = "00003",
) -> Dict[str, Any]:
    """Fetch daily water data from USGS for specified sites (default: daily mean).
    Uses the NWIS daily-values endpoint — suitable for any date range.
    stat_codes: "00003"=mean (default), "00001"=max, "00002"=min.
    parameter_codes: "00060"=streamflow (ft³/s), "00065"=gage height (ft)."""
    return await get_water_data_values(
        sites=sites,
        parameter_codes=parameter_codes if parameter_codes else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        stat_codes=stat_codes if stat_codes else None,
    )


@mcp.tool()
async def fetch_usgs_realtime_data(
    sites: str,
    parameter_codes: str = "",
    start_date: str = "",
    end_date: str = "",
    period: str = "",
) -> Dict[str, Any]:
    """Fetch real-time instantaneous water data from USGS (15-min intervals, last ~120 days only).
    Use fetch_usgs_data for historical or daily analysis.
    parameter_codes: "00060"=streamflow (ft³/s), "00065"=gage height (ft)."""
    return await get_water_data_values(
        sites=sites,
        parameter_codes=parameter_codes if parameter_codes else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        period=period if period else None,
        base_url=USGS_IV_API_BASE,
    )
