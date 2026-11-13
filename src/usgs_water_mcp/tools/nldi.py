"""Tool for USGS NLDI API — upstream watershed basin boundaries."""

from __future__ import annotations

from typing import Any, Dict

import httpx

from usgs_water_mcp.config import NLDI_API_BASE
from usgs_water_mcp.server import mcp


def _nldi_site_id(site_id: str) -> str:
    """Normalise a USGS site ID to the NLDI format 'USGS-XXXXXXXX'.

    Accepts any of: 'USGS06019500', '06019500', 'USGS-06019500'.
    """
    s = site_id.strip().upper()
    if s.startswith("USGS-"):
        return s
    if s.startswith("USGS"):
        return f"USGS-{s[4:]}"
    return f"USGS-{s}"


@mcp.tool()
async def get_watershed_boundary(site_id: str) -> Dict[str, Any]:
    """Fetch the upstream watershed (basin) boundary for a USGS stream gage.

    Uses the USGS Network-Linked Data Index (NLDI) API to retrieve the
    upstream drainage basin as a GeoJSON FeatureCollection (WGS84).

    Args:
        site_id: USGS site number in any format accepted by NWIS, e.g.
                 "06019500", "USGS06019500", or "USGS-06019500".

    Returns:
        GeoJSON FeatureCollection with one Polygon or MultiPolygon feature
        representing the upstream watershed boundary.  The feature has no
        built-in properties; callers should add station metadata themselves.

    Raises:
        httpx.HTTPStatusError: if the NLDI API returns a non-2xx response
            (e.g. 404 when no basin is available for the requested site).
    """
    nldi_id = _nldi_site_id(site_id)
    url = f"{NLDI_API_BASE}/{nldi_id}/basin"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
