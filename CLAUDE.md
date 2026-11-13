# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install / sync dependencies
uv sync

# Run the MCP server (stdio transport)
uv run python -m usgs_water_mcp

# Register globally in Claude Code (user scope, all projects)
claude mcp add usgs-water -s user -- \
    uv run --directory /Users/a02388352/github/usgs-water-mcp python -m usgs_water_mcp

# Verify all tools register (should print 26)
uv run python -c "
from usgs_water_mcp.server import mcp
print(len(mcp._tool_manager._tools))
"
```

After making changes, restart the MCP server (quit and reopen Claude Desktop/Code) so the new tool schemas are picked up. There is no test suite.

## Architecture

`src/usgs_water_mcp/` is a standard `src`-layout package built with hatchling.

```
src/usgs_water_mcp/
├── server.py      # FastMCP singleton + _INSTRUCTIONS + side-effect tool imports + main()
├── config.py      # API base-URL constants (four upstream services)
├── client.py      # shared async HTTP helpers: get_water_data_values, get_rtfi_data, get_ogc_data
├── __main__.py    # entry point for `python -m usgs_water_mcp`
└── tools/
    ├── water_data.py    # fetch_usgs_data, fetch_usgs_realtime_data, fetch_usgs_annual_statistics
    ├── flood_impact.py  # 12 RTFI tools
    ├── ogc.py           # 7 OGC tools
    └── plot.py          # plot_usgs_data, plot_usgs_overlay, plot_usgs_annual
```

**Singleton + side-effect import pattern** (mirrors `ats-mcp`):

1. `server.py` creates `mcp = FastMCP(...)` first.
2. Tool modules do `from usgs_water_mcp.server import mcp` and decorate functions
   with `@mcp.tool()` at module level — no closures, no `register_*` functions.
3. `server.py` then imports all tool modules for their side effects:
   `from usgs_water_mcp.tools import water_data, flood_impact, ogc, plot`.

Adding a new tool: create or edit a file under `tools/`, import `mcp` from
`usgs_water_mcp.server`, and decorate the async function. Add a side-effect
import in `server.py` if it's a new module. All base URLs live in `config.py`;
all HTTP logic goes through helpers in `client.py`.

| Module | Upstream API | Base URL constant |
|---|---|---|
| `water_data.py` | NWIS daily-values | `USGS_DV_API_BASE` |
| `water_data.py` | NWIS instantaneous | `USGS_IV_API_BASE` |
| `water_data.py`, `plot.py` | NWIS statistics (annual, RDB only) | `USGS_STAT_API_BASE` |
| `flood_impact.py` | Real-Time Flood Impacts | `RTFI_API_BASE` |
| `ogc.py` | OGC monitoring locations | `OGC_API_BASE` |
| `plot.py` | local Plotly (+ OGC for station name in `plot_usgs_annual`) | `OGC_API_BASE` |

## How multi-year overlay plots work correctly

A naive overlay that places raw `YYYY-MM-DD` strings from two different years
on the same Plotly axis will produce **spurious vertical jumps at month
boundaries** because the year prefix changes mid-series and Plotly sorts
date strings lexicographically.

The correct approach used by `plot_usgs_overlay` (in `tools/plot.py`):

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

## Annual statistics notes

- The NWIS stat service (`/nwis/stat/`) only returns RDB, not JSON; `client._parse_rdb` skips `#` comments and the column-format row.
- USGS omits incomplete years entirely (no nulls), and rounds annual means to 0.1. Two years can therefore show identical values (e.g. 10113500 WY2021 = 61.46, WY2022 = 61.53, both published as 61.5). For full precision, average `fetch_usgs_data` daily values over the water year.
- In `plot_usgs_annual`, each run of consecutive years is a separate trace: Plotly's `fill="tozeroy"` bridges `None` gaps even when `connectgaps=False`.
