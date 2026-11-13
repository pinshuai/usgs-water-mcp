"""Plotly visualization tools for USGS water data."""

from __future__ import annotations

import asyncio
import os
import tempfile
import webbrowser
from datetime import date as _date

import plotly.graph_objects as go

from usgs_water_mcp.client import get_annual_statistics, get_ogc_data, get_water_data_values
from usgs_water_mcp.server import mcp
from usgs_water_mcp.tools.water_data import summarize_annual

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


async def _site_name(site: str) -> str:
    """Look up the station name via the OGC API; fall back to the site number."""
    try:
        data = await get_ogc_data(f"collections/monitoring-locations/items/USGS-{site}")
        return data.get("properties", {}).get("monitoring_location_name") or f"USGS {site}"
    except Exception:
        return f"USGS {site}"


def _contiguous_runs(years: list[int]) -> list[list[int]]:
    """Split sorted years into runs of consecutive years, e.g. [1,2,4] -> [[1,2],[4]]."""
    runs: list[list[int]] = []
    for y in years:
        if runs and y == runs[-1][-1] + 1:
            runs[-1].append(y)
        else:
            runs.append([y])
    return runs


def _year_ranges(years: list[int]) -> list[tuple[int, int]]:
    return [(r[0], r[-1]) for r in _contiguous_runs(years)] if years else []


@mcp.tool()
async def plot_usgs_annual(
    sites: str,
    parameter_codes: str = "00060",
    year_type: str = "water",
    output_path: str = "",
) -> str:
    """Plot the USGS-published annual mean time series (e.g. annual mean discharge by
    water year) for one site over its full period of record, as an interactive Plotly
    HTML chart opened in the browser. Same style as plot_usgs_data: filled area, peak
    and low markers, dashed long-term mean. Missing (incomplete) years are shaded and
    the line/fill break there instead of interpolating across them.
    year_type: "water" (default) or "calendar". output_path: optional HTML path."""
    site = sites.split(",")[0].strip()
    if year_type not in ("water", "calendar"):
        return 'year_type must be "water" or "calendar"'
    rows = await get_annual_statistics(site, parameter_codes, year_type)
    if not rows:
        return f"No annual statistics returned for site {site}, parameter {parameter_codes}."

    series = summarize_annual(rows)
    key, s = next(iter(series.items()))  # first time series if a site has several
    d = {y["year"]: y["mean"] for y in s["years"]}
    summ = s["summary"]
    site_name = await _site_name(site)
    unit = "ft3/s" if parameter_codes == "00060" else ""
    prefix = "WY" if year_type == "water" else ""
    label = f"Annual mean ({unit})" if unit else "Annual mean"

    fig = go.Figure()
    # fill="tozeroy" bridges None gaps in Plotly, so draw each consecutive run separately
    for i, run in enumerate(_contiguous_runs(sorted(d))):
        fig.add_trace(
            go.Scatter(
                x=run,
                y=[d[y] for y in run],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color="steelblue", width=1.5),
                marker=dict(size=4, color="steelblue"),
                fillcolor="rgba(70,130,180,0.25)",
                name=label,
                legendgroup="annual",
                showlegend=(i == 0),
                hovertemplate=f"<b>{prefix}%{{x}}</b><br>%{{y:.1f}} {unit}<extra></extra>",
            )
        )
    for tag, ext, color, pos in [
        ("Peak", summ["max"], "darkblue", "top center"),
        ("Low", summ["min"], "firebrick", "bottom center"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[ext["year"]],
                y=[ext["mean"]],
                mode="markers+text",
                marker=dict(color=color, size=10),
                text=[f"{tag}: {ext['mean']:.1f} {unit} ({prefix}{ext['year']})"],
                textposition=pos,
                textfont=dict(size=11, color=color),
                name=tag,
                hovertemplate=f"<b>{tag}</b><br>{prefix}%{{x}}<br>%{{y:.1f}} {unit}<extra></extra>",
            )
        )
    fig.add_hline(
        y=summ["mean_of_annual_means"],
        line_dash="dash",
        line_color="gray",
        line_width=1,
        annotation_text=f"Mean: {summ['mean_of_annual_means']:.2f} {unit}",
        annotation_position="bottom right",
        annotation_font_size=11,
    )
    for a, b in _year_ranges(summ["missing_years"]):
        fig.add_vrect(
            x0=a - 0.5, x1=b + 0.5, fillcolor="lightgray", opacity=0.35, line_width=0,
            annotation_text="no data", annotation_position="top left", annotation_font_size=10,
        )
    yr_word = "water" if year_type == "water" else "calendar"
    fig.update_layout(
        title=dict(
            text=(
                f"{site_name}<br><sub>Annual mean by {yr_word} year ({unit}) · USGS: {site}"
                f" · {summ['n_years']} complete {yr_word} years</sub>"
            ),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title=f"{yr_word.capitalize()} year",
            range=[summ["first_year"] - 2, summ["last_year"] + 2],
            showgrid=True,
            gridcolor="#eee",
        ),
        yaxis=dict(title=label, showgrid=True, gridcolor="#eee", rangemode="tozero"),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        margin=dict(l=60, r=30, t=90, b=100),
    )

    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix=".html", prefix="usgs_annual_")
        os.close(fd)
    fig.write_html(output_path, include_plotlyjs="cdn")
    webbrowser.open(f"file://{os.path.abspath(output_path)}")

    note = f"\nNote: site has {len(series)} time series; plotted {key}" if len(series) > 1 else ""
    return (
        f"Plot saved: {output_path}\n"
        f"Site: {site_name}\n"
        f"Years: {summ['first_year']}-{summ['last_year']} ({summ['n_years']} complete)\n"
        f"Missing: {summ['missing_years'] or 'none'}\n"
        f"Mean of annual means: {summ['mean_of_annual_means']:.2f} {unit}  "
        f"Peak: {summ['max']['mean']:.1f} ({prefix}{summ['max']['year']})  "
        f"Low: {summ['min']['mean']:.1f} ({prefix}{summ['min']['year']})"
        f"{note}"
    )
