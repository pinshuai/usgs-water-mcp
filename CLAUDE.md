# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the MCP server manually (stdio transport)
uv run python main.py

# Register globally in Claude Code (user scope, all projects)
claude mcp add usgs-water -s user -- uv run --directory /path/to/usgs-water-mcp python main.py

# Verify import health
uv run python -c "from plot_api import register_plot_tools; print('ok')"
```

There is no test suite. After making changes, restart the MCP server (quit and reopen Claude Desktop/Code) so the new tool schemas are picked up.

## Architecture

`main.py` creates a single `FastMCP` instance and calls four `register_*_tools(mcp)` functions — one per module. Each module owns its upstream API base URL, a private `get_*_data` async helper (uses `httpx.AsyncClient`), and a `register_*_tools` function that closes over `mcp` and registers inner `async` functions with `@mcp.tool()`.

| Module | Upstream API | Base URL |
|---|---|---|
| `water_data_api.py` | NWIS daily-values | `nwis.waterservices.usgs.gov/nwis/dv/` |
| `flood_impact_api.py` | Real-Time Flood Impacts | `api.waterdata.usgs.gov/rtfi-api` |
| `ogc_api.py` | OGC monitoring locations | `api.waterdata.usgs.gov/ogcapi/v0` |
| `plot_api.py` | (local Plotly, no upstream) | — |

`water_data_api.py` exposes `get_water_data_values()` as a public async helper; `plot_api.py` imports and reuses it so the visualization tools don't duplicate HTTP logic.

`plot_api.py` has two tools:
- `plot_usgs_data` — single site, single date range, filled area chart.
- `plot_usgs_overlay` — multiple years on a shared day-of-year axis (see below).

Module-level constants `_COLORS` (8-colour cycle) and `_REF_YEAR = 2000` are shared across both tools. `current_water_levels.py` is a legacy combined file kept for reference but is not imported by `main.py`.

## How multi-year overlay plots work correctly

A naive overlay that places raw `YYYY-MM-DD` strings from two different years
on the same Plotly axis will produce **spurious vertical jumps at month
boundaries** because the year prefix changes mid-series and Plotly sorts
date strings lexicographically.

The correct approach used by `plot_usgs_overlay` (in `plot_api.py`):

1. **Remap every date to a single reference year** (`2000`, a leap year that
   can represent Feb 29 from any source year) by replacing only the year
   component: `f"2000-{date[5:]}"`.  Month and day are preserved exactly.

2. **Sort the series by date** before remapping so no out-of-order segments
   reach Plotly, even if the API returns values in an unexpected order.

3. **Preserve real dates in hover labels** via Plotly's `customdata` field so
   the actual year/date is still visible when the user hovers, while the
   x-axis renders clean monthly tick labels (`Jan`, `Feb`, …).

4. **Fetch all years in parallel** with `asyncio.gather` so the wall-clock
   time equals one request, not N.

The reference-year trick and `tickformat="%b"` / `dtick="M1"` axis settings
are the critical pieces — apply the same pattern to any new multi-year
visualization added to this server.
