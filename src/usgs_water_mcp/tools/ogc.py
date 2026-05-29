"""Tools for the USGS OGC API (monitoring locations and reference metadata)."""

from __future__ import annotations

from typing import Any, Dict

from usgs_water_mcp.client import get_ogc_data
from usgs_water_mcp.server import mcp


@mcp.tool()
async def get_monitoring_locations(
    bbox: str = "",
    limit: int = 100,
    offset: int = 0,
    agency_code: str = "",
    state_code: str = "",
    county_code: str = "",
    site_type_code: str = "",
    monitoring_location_number: str = "",
) -> Dict[str, Any]:
    """Get monitoring locations from USGS OGC API.

    Args:
        bbox: Bounding box as "minx,miny,maxx,maxy"
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
        agency_code: Filter by agency code (e.g., "USGS")
        state_code: Filter by state code (e.g., "CA")
        county_code: Filter by county code
        site_type_code: Filter by site type code
        monitoring_location_number: Specific monitoring location number
    """
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if bbox:
        params["bbox"] = bbox
    if agency_code:
        params["agency_code"] = agency_code
    if state_code:
        params["state_code"] = state_code
    if county_code:
        params["county_code"] = county_code
    if site_type_code:
        params["site_type_code"] = site_type_code
    if monitoring_location_number:
        params["monitoring_location_number"] = monitoring_location_number
    return await get_ogc_data("collections/monitoring-locations/items", params)


@mcp.tool()
async def get_monitoring_location_by_id(location_id: str) -> Dict[str, Any]:
    """Get specific monitoring location by ID from USGS OGC API.

    Args:
        location_id: The monitoring location ID
    """
    return await get_ogc_data(f"collections/monitoring-locations/items/{location_id}")


@mcp.tool()
async def get_agency_codes(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get agency identification codes from USGS OGC API.

    Args:
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
    """
    return await get_ogc_data("collections/agency-codes/items", {"limit": limit, "offset": offset})


@mcp.tool()
async def get_altitude_datums(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get vertical datum information from USGS OGC API (recommended: NAVD88).

    Args:
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
    """
    return await get_ogc_data("collections/altitude-datums/items", {"limit": limit, "offset": offset})


@mcp.tool()
async def get_aquifer_codes(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get aquifer identification information from USGS OGC API.

    Args:
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
    """
    return await get_ogc_data("collections/aquifer-codes/items", {"limit": limit, "offset": offset})


@mcp.tool()
async def get_aquifer_types(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get aquifer type information from USGS OGC API (confined vs unconfined).

    Args:
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
    """
    return await get_ogc_data("collections/aquifer-types/items", {"limit": limit, "offset": offset})


@mcp.tool()
async def get_coordinate_accuracy_codes(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get coordinate accuracy codes for latitude-longitude values from USGS OGC API.

    Args:
        limit: Maximum number of results (default: 100)
        offset: Starting offset for pagination (default: 0)
    """
    return await get_ogc_data(
        "collections/coordinate-accuracy-codes/items", {"limit": limit, "offset": offset}
    )
