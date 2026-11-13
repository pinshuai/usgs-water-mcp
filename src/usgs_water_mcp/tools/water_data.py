"""Tools for querying USGS NWIS water data (daily and real-time)."""

from __future__ import annotations

import statistics
from typing import Any, Dict, List

from usgs_water_mcp.client import get_annual_statistics, get_water_data_values
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


def summarize_annual(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """Collapse stat-service rows into per-site annual series plus summary stats.

    Shared by fetch_usgs_annual_statistics and plot_usgs_annual. When a site has
    more than one time series (ts_id), each is kept separately.
    """
    out: Dict[str, Any] = {}
    for r in rows:
        key = r["site_no"] if not r.get("loc_web_ds") else f"{r['site_no']} ({r['loc_web_ds']})"
        key = f"{key} [ts {r['ts_id']}]" if r.get("ts_id") else key
        out.setdefault(key, {"site_no": r["site_no"], "ts_id": r.get("ts_id", ""),
                             "loc_web_ds": r.get("loc_web_ds", ""), "years": []})
        out[key]["years"].append(
            {"year": int(r["year_nu"]), "mean": float(r["mean_va"]), "days": int(r["count_nu"])}
        )
    for s in out.values():
        yrs = sorted(s["years"], key=lambda y: y["year"])
        s["years"] = yrs
        vals = [y["mean"] for y in yrs]
        have = {y["year"] for y in yrs}
        hi = max(yrs, key=lambda y: y["mean"])
        lo = min(yrs, key=lambda y: y["mean"])
        s["summary"] = {
            "n_years": len(vals),
            "first_year": yrs[0]["year"],
            "last_year": yrs[-1]["year"],
            "missing_years": [y for y in range(yrs[0]["year"], yrs[-1]["year"] + 1) if y not in have],
            "mean_of_annual_means": round(statistics.mean(vals), 2),
            "median_of_annual_means": round(statistics.median(vals), 2),
            "max": {"year": hi["year"], "mean": hi["mean"]},
            "min": {"year": lo["year"], "mean": lo["mean"]},
        }
    return out


@mcp.tool()
async def fetch_usgs_annual_statistics(
    sites: str,
    parameter_codes: str = "00060",
    year_type: str = "water",
) -> Dict[str, Any]:
    """Fetch USGS-published annual mean values (e.g. annual mean discharge by water year)
    from the NWIS statistics service, for the full period of record.
    year_type: "water" (Oct 1-Sep 30, default) or "calendar".
    Only complete years (365/366 approved daily values) are reported; gaps are listed
    under summary.missing_years. Values are rounded to 0.1 by USGS — for full precision,
    average fetch_usgs_data daily values over the year.
    parameter_codes: "00060"=streamflow (ft³/s, default)."""
    if year_type not in ("water", "calendar"):
        return {"error": 'year_type must be "water" or "calendar"'}
    rows = await get_annual_statistics(sites, parameter_codes, year_type)
    if not rows:
        return {"error": f"No annual statistics returned for site(s) {sites}, parameter {parameter_codes}."}
    return {"year_type": year_type, "parameter_cd": parameter_codes, "series": summarize_annual(rows)}
