"""Plotly visualization tools for USGS water data."""

from __future__ import annotations

import asyncio
import os
import tempfile
import webbrowser
from datetime import date as _date

import plotly.graph_objects as go

from usgs_water_mcp.client import get_water_data_values
from usgs_water_mcp.server import mcp

# Colour cycle for overlay traces (up to 8 years)
_COLORS = [
    "#2166ac",
    "#d6604d",
    "#4dac26",
    "#9970ab",
    "#f4a582",
    "#80cdc1",
    "#a6611a",
    "#c51b7d",
]

# Use a leap year as the shared x-axis so Feb 29 data maps without error
_REF_YEAR = 2000


def _build_figure(
    dates: list, flows: list, site_name: str, site_id: str, variable_name: str, unit: str
) -> go.Figure:
    peak_i = flows.index(max(flows))
    mean_q = sum(flows) / len(flows)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=flows,
            mode="lines",
            fill="tozeroy",
            line=dict(color="steelblue", width=1.5),
            fillcolor="rgba(70,130,180,0.25)",
            name=variable_name,
            hovertemplate="<b>%{x}</b><br>%{y:.2f} " + unit + "<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[dates[peak_i]],
            y=[flows[peak_i]],
            mode="markers+text",
            marker=dict(color="darkblue", size=10),
            text=[f"Peak: {flows[peak_i]:.1f} {unit}"],
            textposition="top center",
            textfont=dict(size=11, color="darkblue"),
            name="Peak",
            hovertemplate=f"<b>Peak</b><br>%{{x}}<br>%{{y:.1f}} {unit}<extra></extra>",
        )
    )
    fig.add_hline(
        y=mean_q,
        line_dash="dash",
        line_color="gray",
        line_width=1,
        annotation_text=f"Mean: {mean_q:.2f} {unit}",
        annotation_position="bottom right",
        annotation_font_size=11,
    )
    fig.update_layout(
        title=dict(
            text=f"{site_name}<br><sub>{variable_name} ({unit}) · USGS: {site_id}</sub>",
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="Date", showgrid=True, gridcolor="#eee"),
        yaxis=dict(title=f"{variable_name} ({unit})", showgrid=True, gridcolor="#eee"),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=30, t=90, b=60),
    )
    return fig


def _to_ref_date(date_str: str) -> str:
    """Map 'YYYY-MM-DD' to the shared reference year for day-of-year alignment.

    All years are remapped to _REF_YEAR (a leap year) so that Plotly's date
    axis renders clean monthly tick labels without artificial jumps at year or
    month boundaries.  The original year is preserved only in the hover label.
    """
    return f"{_REF_YEAR}-{date_str[5:]}"  # keep MM-DD, swap year


@mcp.tool()
async def plot_usgs_data(
    sites: str,
    parameter_codes: str = "00060",
    start_date: str = "",
    end_date: str = "",
    stat_codes: str = "00003",
    output_path: str = "",
) -> str:
    """Fetch USGS daily water data and generate an interactive Plotly HTML plot.
    Opens the plot in the default browser and returns the saved file path.
    parameter_codes: "00060"=streamflow (ft³/s), "00065"=gage height (ft).
    stat_codes: "00003"=mean (default), "00001"=max, "00002"=min.
    output_path: optional path to save the HTML file (defaults to system temp dir)."""
    data = await get_water_data_values(
        sites=sites,
        parameter_codes=parameter_codes if parameter_codes else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        stat_codes=stat_codes if stat_codes else None,
    )

    ts = data["value"]["timeSeries"][0]
    site_name = ts["sourceInfo"]["siteName"]
    variable_name = ts["variable"]["variableName"]
    unit = ts["variable"]["unit"]["unitCode"]
    raw_vals = ts["values"][0]["value"]

    dates = [v["dateTime"][:10] for v in raw_vals if v["value"] != "-999999"]
    flows = [float(v["value"]) for v in raw_vals if v["value"] != "-999999"]

    if not flows:
        return f"No valid data returned for site {sites}."

    fig = _build_figure(dates, flows, site_name, sites, variable_name, unit)

    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix=".html", prefix="usgs_plot_")
        os.close(fd)

    fig.write_html(output_path, include_plotlyjs="cdn")
    webbrowser.open(f"file://{os.path.abspath(output_path)}")

    return (
        f"Plot saved: {output_path}\n"
        f"Site: {site_name}\n"
        f"Records: {len(flows)}\n"
        f"Peak: {max(flows):.2f} {unit}  Mean: {sum(flows)/len(flows):.2f} {unit}"
        f"  Min: {min(flows):.2f} {unit}"
    )


@mcp.tool()
async def plot_usgs_overlay(
    sites: str,
    years: str,
    parameter_codes: str = "00060",
    stat_codes: str = "00003",
    output_path: str = "",
) -> str:
    """Fetch USGS daily data for multiple years and plot them on a shared
    day-of-year axis so that seasonal patterns (e.g. snowmelt peaks) line up
    regardless of calendar year.

    How it works
    ------------
    Every date is remapped to a single reference year (2000, a leap year)
    before being passed to Plotly.  This gives the x-axis clean monthly
    tick labels (Jan, Feb, …) with no artificial jumps at month or year
    boundaries.  The original year is shown in each trace label and in the
    peak annotation, so the real dates remain visible in hover tooltips.

    Parameters
    ----------
    sites : str
        Single USGS site number (e.g. "10109000").
    years : str
        Comma-separated calendar years to compare (e.g. "2023,2024,2025").
        The current year is fetched through today's date automatically.
    parameter_codes : str
        NWIS parameter code.  "00060" = streamflow (ft³/s, default),
        "00065" = gage height (ft).
    stat_codes : str
        Daily statistic.  "00003" = mean (default), "00001" = max,
        "00002" = min.
    output_path : str
        Optional path for the saved HTML file.  Defaults to a temp file.

    Returns
    -------
    str
        File path, site name, and per-year peak / mean summary.
    """
    today = _date.today()
    year_list = [y.strip() for y in years.split(",")]

    async def _fetch_year(yr: str):
        y = int(yr)
        start = f"{y}-01-01"
        end = f"{y}-12-31" if y < today.year else today.isoformat()
        data = await get_water_data_values(
            sites=sites,
            parameter_codes=parameter_codes if parameter_codes else None,
            start_date=start,
            end_date=end,
            stat_codes=stat_codes if stat_codes else None,
        )
        ts = data["value"]["timeSeries"][0]
        raw_vals = ts["values"][0]["value"]
        pairs = sorted(
            (
                (v["dateTime"][:10], float(v["value"]))
                for v in raw_vals
                if v["value"] != "-999999"
            ),
            key=lambda p: p[0],
        )
        return ts, pairs

    results = await asyncio.gather(*[_fetch_year(yr) for yr in year_list])

    first_ts = results[0][0]
    site_name = first_ts["sourceInfo"]["siteName"]
    variable_name = first_ts["variable"]["variableName"]
    unit = first_ts["variable"]["unit"]["unitCode"]

    fig = go.Figure()
    summary_lines: list[str] = [f"Site: {site_name}"]

    for i, (yr, (_, pairs)) in enumerate(zip(year_list, results)):
        if not pairs:
            summary_lines.append(f"{yr}: no data")
            continue

        color = _COLORS[i % len(_COLORS)]
        real_dates = [p[0] for p in pairs]
        flows = [p[1] for p in pairs]
        ref_dates = [_to_ref_date(d) for d in real_dates]
        peak_i = flows.index(max(flows))
        label = yr if int(yr) < today.year else f"{yr} (provisional)"

        fig.add_trace(
            go.Scatter(
                x=ref_dates,
                y=flows,
                mode="lines",
                name=label,
                line=dict(color=color, width=1.8),
                customdata=real_dates,
                hovertemplate=(
                    f"<b>{yr} %{{customdata}}</b><br>%{{y:.0f}} {unit}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[ref_dates[peak_i]],
                y=[flows[peak_i]],
                mode="markers+text",
                showlegend=False,
                marker=dict(color=color, size=9),
                text=[f"{flows[peak_i]:.0f} {unit}<br>{real_dates[peak_i]}"],
                textposition="top right",
                textfont=dict(size=9, color=color),
                hoverinfo="skip",
            )
        )

        mean_q = sum(flows) / len(flows)
        summary_lines.append(
            f"{yr}: {len(flows)} days | "
            f"peak {max(flows):.0f} {unit} on {real_dates[peak_i]} | "
            f"mean {mean_q:.1f} {unit}"
        )

    fig.update_layout(
        title=dict(
            text=(
                f"{site_name}<br>"
                f"<sub>{variable_name} ({unit}) · USGS: {sites} — day-of-year comparison</sub>"
            ),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="Month", tickformat="%b", dtick="M1", showgrid=True, gridcolor="#eee"),
        yaxis=dict(title=f"{variable_name} ({unit})", showgrid=True, gridcolor="#eee"),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
        margin=dict(l=65, r=30, t=100, b=60),
    )

    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix=".html", prefix="usgs_overlay_")
        os.close(fd)

    fig.write_html(output_path, include_plotlyjs="cdn")
    webbrowser.open(f"file://{os.path.abspath(output_path)}")

    return "\n".join([f"Plot saved: {output_path}", *summary_lines])
