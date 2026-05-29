from typing import Any, Dict, Optional
import httpx
from mcp.server.fastmcp import FastMCP

USGS_API_BASE = "https://nwis.waterservices.usgs.gov/nwis/dv/"
USGS_IV_API_BASE = "https://waterservices.usgs.gov/nwis/iv/"

async def get_water_data_values(
    sites: str,
    parameter_codes: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stat_codes: Optional[str] = None,
    period: Optional[str] = None,
    base_url: str = USGS_API_BASE,
    format: str = "json"
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "sites": sites,
        "format": format
    }

    if parameter_codes:
        params["parameterCd"] = parameter_codes
    if start_date:
        params["startDT"] = start_date
    if end_date:
        params["endDT"] = end_date
    if stat_codes:
        params["statCd"] = stat_codes
    if period:
        params["period"] = period

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        if format == "json":
            return response.json()
        else:
            return {"data": response.text}


def register_water_data_tools(mcp: FastMCP):
    """Register water data API tools with the MCP server"""

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
