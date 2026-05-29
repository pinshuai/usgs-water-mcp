"""USGS Water MCP Server entry point.

Run with:  uv run python -m usgs_water_mcp

Register in Claude Code (user scope):
    claude mcp add usgs-water -s user -- \\
        uv run --directory /path/to/usgs-water-mcp python -m usgs_water_mcp
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

_INSTRUCTIONS = """\
Tools for querying USGS water data across three upstream APIs.

Water Services (NWIS):
  fetch_usgs_data          — daily mean/max/min values, any date range
  fetch_usgs_realtime_data — 15-min instantaneous values, last ~120 days only

Real-Time Flood Impacts (RTFI):
  get_flooding_reference_points, get_reference_points, get_reference_point_by_id,
  get_reference_points_by_state, get_reference_point_by_nwis_id,
  get_reference_points_by_nws_id, get_inactive_reference_points,
  get_states, get_state_by_id, get_counties, get_counties_by_state,
  get_nws_usgs_crosswalk

OGC / monitoring metadata:
  get_monitoring_locations, get_monitoring_location_by_id,
  get_agency_codes, get_altitude_datums, get_aquifer_codes,
  get_aquifer_types, get_coordinate_accuracy_codes

Visualization (Plotly HTML, opens in browser):
  plot_usgs_data    — single site / date range, filled area chart
  plot_usgs_overlay — multiple years on a shared day-of-year axis

Common parameter codes: "00060"=streamflow ft³/s, "00065"=gage height ft.
Common stat codes:      "00003"=mean (default), "00001"=max, "00002"=min.
"""

mcp = FastMCP("usgs-water-mcp", instructions=_INSTRUCTIONS)

# When run as `python -m usgs_water_mcp`, this module is loaded as __main__.
# Register it under the canonical name so sub-module imports share the same
# mcp singleton rather than creating a second instance.
if __name__ == "__main__":
    sys.modules.setdefault("usgs_water_mcp.server", sys.modules[__name__])

# Side-effect imports — each module does `from usgs_water_mcp.server import mcp`
# and registers its tools via @mcp.tool() at module level.
from usgs_water_mcp.tools import water_data, flood_impact, ogc, plot  # noqa: E402, F401


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
