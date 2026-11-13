"""Shared async HTTP helpers for the USGS water data APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import httpx

from usgs_water_mcp.config import (
    USGS_DV_API_BASE,
    USGS_STAT_API_BASE,
    RTFI_API_BASE,
    OGC_API_BASE,
)


async def get_water_data_values(
    sites: str,
    parameter_codes: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stat_codes: Optional[str] = None,
    period: Optional[str] = None,
    base_url: str = USGS_DV_API_BASE,
    format: str = "json",
) -> Dict[str, Any]:
    """Fetch NWIS water data (daily-values by default, or instantaneous-values)."""
    params: Dict[str, Any] = {"sites": sites, "format": format}
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
        return {"data": response.text}


def _parse_rdb(text: str) -> List[Dict[str, str]]:
    """Parse a USGS RDB (tab-delimited) response into a list of row dicts.

    RDB layout: '#' comment lines, a header row, a column-format row
    (e.g. '5s\t15s'), then data rows.
    """
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, ln.split("\t"))) for ln in lines[2:]]


async def get_annual_statistics(
    sites: str,
    parameter_codes: str = "00060",
    year_type: str = "water",
) -> List[Dict[str, str]]:
    """Fetch USGS-computed annual mean statistics from the NWIS stat service.

    year_type: "water" (Oct 1 - Sep 30) or "calendar". USGS only reports years
    with a complete record, so incomplete years are absent rather than null.
    """
    params = {
        "format": "rdb",
        "sites": sites,
        "statReportType": "annual",
        "statYearType": year_type,
        "parameterCd": parameter_codes,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(USGS_STAT_API_BASE, params=params)
        response.raise_for_status()
        return _parse_rdb(response.text)


async def get_rtfi_data(
    endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], List[Any]]:
    """Fetch data from the USGS Real-Time Flood Impacts API."""
    url = f"{RTFI_API_BASE}/{endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"items": data, "count": len(data)}
        return data


async def get_ogc_data(
    endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Fetch data from the USGS OGC API."""
    url = f"{OGC_API_BASE}/{endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"items": data, "count": len(data)}
        return data
