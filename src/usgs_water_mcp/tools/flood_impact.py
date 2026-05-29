"""Tools for the USGS Real-Time Flood Impacts API."""

from __future__ import annotations

from typing import Any, Dict

from usgs_water_mcp.client import get_rtfi_data
from usgs_water_mcp.server import mcp


@mcp.tool()
async def get_flooding_reference_points() -> Dict[str, Any]:
    """Get currently flooding reference points from USGS Real-Time Flood Impacts API."""
    return await get_rtfi_data("referencepoints/flooding")


@mcp.tool()
async def get_reference_points(page: int = 1, limit: int = 100) -> Dict[str, Any]:
    """Get paginated list of reference points from USGS Real-Time Flood Impacts API.

    Args:
        page: Page number (default: 1)
        limit: Number of results per page (default: 100)
    """
    return await get_rtfi_data("referencepoints", {"page": page, "limit": limit})


@mcp.tool()
async def get_reference_point_by_id(reference_point_id: str) -> Dict[str, Any]:
    """Get specific reference point by ID from USGS Real-Time Flood Impacts API.

    Args:
        reference_point_id: The reference point ID
    """
    return await get_rtfi_data(f"referencepoints/{reference_point_id}")


@mcp.tool()
async def get_reference_points_by_state(state_id: str) -> Dict[str, Any]:
    """Get reference points for a specific state from USGS Real-Time Flood Impacts API.

    Args:
        state_id: State ID (e.g., "CA", "TX")
    """
    return await get_rtfi_data(f"referencepoints/state/{state_id}")


@mcp.tool()
async def get_reference_point_by_nwis_id(nwis_id: str) -> Dict[str, Any]:
    """Get reference point by USGS gage ID from USGS Real-Time Flood Impacts API.

    Args:
        nwis_id: USGS National Water Information System site ID
    """
    return await get_rtfi_data(f"referencepoints/nwis/{nwis_id}")


@mcp.tool()
async def get_reference_points_by_nws_id(nws_id: str) -> Dict[str, Any]:
    """Get reference points by National Weather Service ID from USGS Real-Time Flood Impacts API.

    Args:
        nws_id: National Weather Service location ID
    """
    return await get_rtfi_data(f"referencepoints/nws/{nws_id}")


@mcp.tool()
async def get_inactive_reference_points() -> Dict[str, Any]:
    """Get inactive reference points from USGS Real-Time Flood Impacts API."""
    return await get_rtfi_data("referencepoints/inactive")


@mcp.tool()
async def get_states() -> Dict[str, Any]:
    """Get list of states from USGS Real-Time Flood Impacts API."""
    return await get_rtfi_data("states")


@mcp.tool()
async def get_state_by_id(state_id: str) -> Dict[str, Any]:
    """Get specific state information from USGS Real-Time Flood Impacts API.

    Args:
        state_id: State ID (e.g., "CA", "TX")
    """
    return await get_rtfi_data(f"states/{state_id}")


@mcp.tool()
async def get_counties() -> Dict[str, Any]:
    """Get list of counties from USGS Real-Time Flood Impacts API."""
    return await get_rtfi_data("counties")


@mcp.tool()
async def get_counties_by_state(state_id: str) -> Dict[str, Any]:
    """Get counties for a specific state from USGS Real-Time Flood Impacts API.

    Args:
        state_id: State ID (e.g., "CA", "TX")
    """
    return await get_rtfi_data(f"counties/state/{state_id}")


@mcp.tool()
async def get_nws_usgs_crosswalk() -> Dict[str, Any]:
    """Get NWS/USGS crosswalk data from USGS Real-Time Flood Impacts API."""
    return await get_rtfi_data("nws_usgs")
