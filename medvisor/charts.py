"""Plotly figures for the interactive dashboard layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import ACCENT, ALERT, BENCHMARKS, CARD, INK, MUTED, RULE, SERIES_COLORS, SERIES_LABELS, SLATE, WATCH
from .metrics import WEEKDAY_ORDER

FONT = "'IBM Plex Sans', Inter, sans-serif"
MONO = "'IBM Plex Mono', monospace"


def _base(fig: go.Figure, height: int = 340, y_title: str | None = None, x_title: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=6, t=34, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK),
        hoverlabel=dict(bgcolor=CARD, bordercolor=RULE, font=dict(family=MONO, size=11, color=INK)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.03, x=0, xanchor="left",
            bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=MUTED),
        ),
        bargap=0.28,
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, linecolor=RULE, linewidth=1,
        ticks="outside", ticklen=4, tickcolor=RULE, tickfont=dict(family=MONO, size=10, color=MUTED),
        title=dict(text=x_title, font=dict(size=11, color=MUTED)),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=RULE, gridwidth=0.6, griddash="dot", zeroline=False,
        tickfont=dict(family=MONO, size=10, color=MUTED),
        title=dict(text=y_title, font=dict(size=11, color=MUTED)),
    )
    return fig


def _labels(index) -> list[str]:
    return [pd.Timestamp(i).strftime("%d %b") for i in index]


def chart_volume(vol: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    x = _labels(vol.index)
    for key in ("kept", "cancelled", "no_show", "rescheduled"):
        if key not in vol.columns:
            continue
        fig.add_bar(
            x=x, y=vol[key].values, name=SERIES_LABELS[key], marker_color=SERIES_COLORS[key],
            marker_line_width=0, hovertemplate="%{y}<extra>" + SERIES_LABELS[key] + "</extra>",
        )
    trend = vol["kept"].rolling(3, min_periods=1).mean()
    fig.add_scatter(
        x=x, y=trend.values, name="3-week trend (kept)", mode="lines",
        line=dict(color=INK, width=2, dash="dot"),
        hovertemplate="%{y:.0f}<extra>3-week trend</extra>",
    )
    fig.update_layout(barmode="stack", hovermode="x unified")
    return _base(fig, 360)


def chart_rates(rates: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    x = _labels(rates.index)
    fig.add_scatter(
        x=x, y=rates["no_show_rate"].values * 100, name="No-show rate", mode="lines+markers",
        line=dict(color=ALERT, width=2.4), marker=dict(size=5),
        hovertemplate="%{y:.1f}%<extra>No-show</extra>",
    )
    fig.add_scatter(
        x=x, y=rates["cancel_rate"].values * 100, name="Cancellation rate", mode="lines+markers",
        line=dict(color=WATCH, width=2.0), marker=dict(size=5),
        hovertemplate="%{y:.1f}%<extra>Cancelled</extra>",
    )
    fig.add_hline(
        y=BENCHMARKS["no_show_rate"] * 100, line_dash="dash", line_color=ACCENT, line_width=1.2,
        annotation_text="Reference 8%", annotation_position="bottom right",
        annotation_font=dict(family=MONO, size=10, color=ACCENT),
    )
    return _base(fig, 330, y_title="% of scheduled appointments")


def chart_utilization(util: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        y=util["provider"].tolist(), x=util["utilization"].values * 100, orientation="h",
        marker_color=[ALERT if v < 0.65 else (WATCH if v < 0.80 else ACCENT) for v in util["utilization"]],
        marker_line_width=0,
        hovertemplate="%{x:.1f}%<extra>%{y}</extra>",
    )
    fig.add_vline(
        x=BENCHMARKS["utilization"] * 100, line_dash="dot", line_color=INK, line_width=1.3,
    )
    fig.add_annotation(
        x=BENCHMARKS["utilization"] * 100, y=1.06, yref="paper", text="Target 80%",
        showarrow=False, font=dict(family=MONO, size=10, color=INK), xanchor="left",
    )
    upper = max(100.0, float(util["utilization"].max()) * 100 * 1.12)
    fig.update_xaxes(range=[0, upper])
    return _base(fig, 300, x_title="% of available clinical time booked")


def chart_revenue(rev: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=rev["provider"].tolist(), y=rev["revenue"].values, name="Revenue",
        marker_color=ACCENT, marker_line_width=0,
        hovertemplate="%{y:,.0f}<extra>Revenue</extra>",
    )
    fig.add_scatter(
        x=rev["provider"].tolist(), y=rev["revenue_per_visit"].values, name="Revenue per visit",
        mode="lines+markers", yaxis="y2",
        line=dict(color=ALERT, width=2.2), marker=dict(size=7, symbol="diamond"),
        hovertemplate="%{y:,.0f}<extra>Per visit</extra>",
    )
    fig.update_layout(
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            tickfont=dict(family=MONO, size=10, color=ALERT),
            title=dict(text="per visit", font=dict(size=11, color=ALERT)),
        )
    )
    return _base(fig, 320)


def chart_revenue_trend(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    x = _labels(weekly.index)
    fig.add_bar(x=x, y=weekly["revenue"].values, name="Revenue", marker_color=ACCENT, marker_line_width=0)
    fig.add_scatter(
        x=x, y=weekly["revenue_per_visit"].values, name="Revenue per visit", mode="lines+markers",
        line=dict(color=ALERT, width=2.2), marker=dict(size=5), yaxis="y2",
    )
    fig.update_layout(
        yaxis2=dict(overlaying="y", side="right", showgrid=False, zeroline=False,
                    tickfont=dict(family=MONO, size=10, color=ALERT)),
        hovermode="x unified",
    )
    return _base(fig, 320)


def chart_flow(matrix: pd.DataFrame) -> go.Figure:
    z = matrix.values.astype(float)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[str(c) for c in matrix.columns],
            y=[int(i) for i in matrix.index],
            colorscale=[[0, "#F4F1EA"], [0.35, "#CBDDD7"], [0.7, "#3E8C7B"], [1, "#0D4237"]],
            colorbar=dict(tickfont=dict(family=MONO, size=10, color=MUTED), thickness=10, outlinewidth=0),
            hovertemplate="%{x} %{y}:00 — %{z:.0f} visits<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", dtick=1, title=dict(text="hour of day", font=dict(size=11, color=MUTED)))
    return _base(fig, 320, x_title=None)


def chart_wait(wait: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=[f"{int(h):02d}:00" for h in wait["hour"]], y=wait["median_wait"].values,
        name="Median wait", marker_color=SLATE, marker_line_width=0,
        hovertemplate="%{y:.0f} min<extra>%{x}</extra>",
    )
    fig.add_scatter(
        x=[f"{int(h):02d}:00" for h in wait["hour"]], y=wait["median_wait"].values,
        mode="lines", line=dict(color=INK, width=1.4, dash="dot"), showlegend=False,
    )
    fig.add_hline(y=BENCHMARKS["wait_median"], line_dash="dash", line_color=ACCENT, line_width=1.2,
                  annotation_text="Reference 20 min", annotation_position="bottom right",
                  annotation_font=dict(family=MONO, size=10, color=ACCENT))
    return _base(fig, 320, y_title="minutes")