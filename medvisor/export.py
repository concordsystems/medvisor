"""Static export: PDF report and PNG sheets, rendered with matplotlib only."""

from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from .config import ALERT, CARD, INK, MUTED, PAPER, RULE, SERIES_COLORS, SERIES_LABELS, WATCH, fmt_money, fmt_num, fmt_pct

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": INK,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": RULE,
    "axes.linewidth": 0.8,
    "figure.facecolor": PAPER,
    "axes.facecolor": CARD,
    "savefig.facecolor": PAPER,
    "font.size": 8.5,
})

A4 = (8.27, 11.69)


@dataclass
class ReportContext:
    clinic: str
    window_label: str
    generated_at: str
    summary: dict
    prev_summary: dict
    volume: pd.DataFrame
    rates: pd.DataFrame
    utilization: pd.DataFrame
    revenue: pd.DataFrame
    revenue_weekly: pd.DataFrame
    flags: list
    insights: list
    exec_summary: str
    validation: object | None = None


def _track(s: str) -> str:
    """Letter-spaced eyebrow label.

    matplotlib Text has no `letterspacing` property, so tracking is simulated
    with THIN SPACE characters to keep the ledger-header look.
    """
    return "\u2009".join(s)


def _page() -> plt.Figure:
    fig = plt.figure(figsize=A4)
    fig.patch.set_facecolor(PAPER)
    return fig


def _rule(fig, y, x0=0.07, x1=0.93, lw=1.0, color=RULE):
    fig.add_artist(plt.Line2D([x0, x1], [y, y], transform=fig.transFigure, color=color, linewidth=lw))


def _stamp(fig, x=0.665, y=0.925):
    box = mpatches.FancyBboxPatch(
        (x, y), 0.275, 0.052, transform=fig.transFigure,
        boxstyle="round,pad=0.004,rounding_size=0.006",
        linewidth=1.8, edgecolor=ALERT, facecolor="none",
    )
    fig.add_artist(box)
    fig.text(x + 0.1375, y + 0.031, "PROOF OF CONCEPT", ha="center", va="center",
             fontsize=9.5, fontweight="bold", color=ALERT, family="DejaVu Sans")
    fig.text(x + 0.1375, y + 0.013, "NOT A MEDICAL DEVICE", ha="center", va="center",
             fontsize=6.4, color=ALERT, family="DejaVu Sans")


def _header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.07, 0.952, _track("MEDVISOR  /  CLINIC OPERATIONS INTELLIGENCE"), fontsize=7.2, color=MUTED)
    fig.text(0.07, 0.912, title, fontsize=19, color=INK, fontweight="semibold")
    fig.text(0.07, 0.886, subtitle, fontsize=8.6, color=MUTED, style="italic")
    _stamp(fig)
    _rule(fig, 0.872, lw=1.6, color=INK)


def page_cover(ctx: ReportContext) -> plt.Figure:
    fig = _page()
    _header(fig, "Clinic operations report", f"{ctx.clinic}  ·  {ctx.window_label}")

    s, p = ctx.summary, ctx.prev_summary
    rows = [
        ("Scheduled appointments", fmt_num(s["appointments"]), "vs " + fmt_num(p.get("appointments", 0)) + " previous"),
        ("Kept visits", fmt_num(s["kept"]), "vs " + fmt_num(p.get("kept", 0)) + " previous"),
        ("No-show rate", fmt_pct(s["no_show_rate"]), "reference " + fmt_pct(0.08, 0)),
        ("Cancellation rate", fmt_pct(s["cancel_rate"]), "reference " + fmt_pct(0.10, 0)),
        ("Median wait", fmt_num(s["wait_median"]) + " min", "p90 " + fmt_num(s.get("wait_p90")) + " min"),
    ]
    if s.get("has_revenue"):
        rows += [
            ("Revenue from kept visits", fmt_money(s["revenue"]), "vs " + fmt_money(p.get("revenue", 0)) + " previous"),
            ("Revenue per visit", fmt_money(s["revenue_per_visit"]), "mix-driven"),
        ]

    y = 0.828
    fig.text(0.07, y, _track("PERIOD AT A GLANCE"), fontsize=7.4, color=MUTED)
    y -= 0.030
    for label, value, note in rows:
        fig.text(0.075, y, label, fontsize=8.6, color=MUTED)
        fig.text(0.60, y - 0.004, value, fontsize=11.5, color=INK, fontweight="bold", family="DejaVu Sans")
        fig.text(0.755, y, note, fontsize=7.4, color=MUTED)
        y -= 0.026
        _rule(fig, y + 0.006, 0.07, 0.93)
        y -= 0.008

    y -= 0.022
    fig.text(0.07, y, _track("EXECUTIVE SUMMARY"), fontsize=7.4, color=MUTED)
    y -= 0.032
    wrapped = textwrap.fill(ctx.exec_summary, 112)
    fig.text(0.07, y, wrapped, fontsize=8.6, color=INK, va="top", linespacing=1.65, wrap=False)

    fig.text(0.07, 0.115, _track("COMPLIANCE"), fontsize=7.4, color=ALERT)
    note = (
        "Proof of concept. Not production software and not a medical device. This report was generated from synthetic or "
        "de-identified sample data. No HIPAA, GDPR or LGPD compliance is claimed. Do not run this against real patient "
        "data. See the Compliance & PHI Policy before using any real data."
    )
    fig.text(0.07, 0.098, textwrap.fill(note, 112), fontsize=7.4, color=MUTED, va="top", linespacing=1.7)
    fig.text(0.07, 0.032, f"Generated {ctx.generated_at}  ·  MedVisor PoC 0.1.0", fontsize=6.8, color=MUTED)
    return fig


def _draw_volume(ax, vol: pd.DataFrame) -> None:
    x = np.arange(len(vol))
    bottom = np.zeros(len(vol))
    labels = [pd.Timestamp(i).strftime("%d %b") for i in vol.index]
    for key in ("kept", "cancelled", "no_show", "rescheduled"):
        if key not in vol.columns:
            continue
        vals = vol[key].values.astype(float)
        ax.bar(x, vals, bottom=bottom, color=SERIES_COLORS[key], width=0.72, linewidth=0, label=SERIES_LABELS[key])
        bottom += vals
    trend = vol["kept"].rolling(3, min_periods=1).mean().values
    ax.plot(x, trend, color=INK, linewidth=1.2, linestyle=":", label="3-week trend (kept)")
    step = max(1, len(x) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(labels[::step], rotation=45, ha="right", fontsize=6.5)
    ax.legend(frameon=False, fontsize=6.4, ncol=5, loc="upper left")
    ax.set_title("Appointment volume by status", loc="left", fontsize=9, color=INK, pad=8)


def _draw_rates(ax, rates: pd.DataFrame) -> None:
    x = np.arange(len(rates))
    labels = [pd.Timestamp(i).strftime("%d %b") for i in rates.index]
    ax.plot(x, rates["no_show_rate"].values * 100, color=ALERT, linewidth=1.7, marker="o", markersize=2.6, label="No-show rate")
    ax.plot(x, rates["cancel_rate"].values * 100, color=WATCH, linewidth=1.5, marker="o", markersize=2.6, label="Cancellation rate")
    ax.axhline(8, color=SERIES_COLORS["kept"], linestyle="--", linewidth=1.0)
    ax.text(len(x) - 0.5, 8.25, "reference 8%", ha="right", fontsize=6.2, color=SERIES_COLORS["kept"])
    step = max(1, len(x) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(labels[::step], rotation=45, ha="right", fontsize=6.5)
    ax.set_ylabel("% of scheduled", fontsize=7)
    ax.legend(frameon=False, fontsize=6.4, ncol=2, loc="upper left")
    ax.set_title("No-show & cancellation rate", loc="left", fontsize=9, color=INK, pad=8)
    ax.spines[["top", "right"]].set_visible(False)


def _draw_utilization(ax, util: pd.DataFrame) -> None:
    y = np.arange(len(util))
    colors = [ALERT if v < 0.65 else (WATCH if v < 0.80 else SERIES_COLORS["kept"]) for v in util["utilization"]]
    ax.barh(y, util["utilization"].values * 100, color=colors, height=0.62, linewidth=0)
    ax.set_yticks(y)
    ax.set_yticklabels(util["provider"].tolist(), fontsize=7)
    ax.axvline(80, color=INK, linestyle=":", linewidth=1.0)
    ax.text(81, len(y) - 0.35, "target 80%", fontsize=6.2, color=INK)
    ax.set_xlabel("% of available clinical time", fontsize=7)
    ax.set_title("Provider utilisation", loc="left", fontsize=9, color=INK, pad=8)
    ax.spines[["top", "right"]].set_visible(False)


def _draw_revenue(ax, rev: pd.DataFrame) -> None:
    x = np.arange(len(rev))
    ax.bar(x, rev["revenue"].values, color=SERIES_COLORS["kept"], width=0.6, linewidth=0, label="Revenue")
    ax.set_xticks(x)
    ax.set_xticklabels(rev["provider"].tolist(), rotation=35, ha="right", fontsize=6.5)
    ax.set_ylabel("revenue", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, rev["revenue_per_visit"].values, color=ALERT, linewidth=1.6, marker="D", markersize=3.4, label="Per visit")
    ax2.set_ylabel("per visit", fontsize=7, color=ALERT)
    ax2.tick_params(colors=ALERT, labelsize=6.5)
    ax.set_title("Revenue by provider", loc="left", fontsize=9, color=INK, pad=8)
    ax.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)


def page_charts(ctx: ReportContext) -> plt.Figure:
    fig = _page()
    _header(fig, "Exhibits 01–02  ·  Volume & reliability", f"{ctx.clinic}  ·  {ctx.window_label}")
    ax1 = fig.add_axes([0.085, 0.585, 0.855, 0.235])
    _draw_volume(ax1, ctx.volume)
    ax2 = fig.add_axes([0.085, 0.235, 0.855, 0.215])
    _draw_rates(ax2, ctx.rates)
    fig.text(0.085, 0.075, textwrap.fill(
        "Volumes are stacked by appointment status. The dotted line is the trailing three-week kept-visit trend; "
        "the rate chart plots no-shows and cancellations against the 8% reference for this clinic type.", 120),
        fontsize=7.2, color=MUTED, va="top", linespacing=1.7)
    return fig


def page_capacity(ctx: ReportContext) -> plt.Figure:
    fig = _page()
    _header(fig, "Exhibits 03–04  ·  Capacity & revenue", f"{ctx.clinic}  ·  {ctx.window_label}")
    ax1 = fig.add_axes([0.145, 0.615, 0.795, 0.215])
    _draw_utilization(ax1, ctx.utilization)
    if ctx.summary.get("has_revenue") and not ctx.revenue.empty:
        ax2 = fig.add_axes([0.095, 0.225, 0.845, 0.235])
        _draw_revenue(ax2, ctx.revenue.head(10))
    else:
        fig.text(0.10, 0.36, "No revenue column in this file — revenue exhibits omitted.", fontsize=8.5, color=MUTED)
    fig.text(0.085, 0.075, textwrap.fill(
        "Utilisation is booked clinical minutes divided by assumed availability (7h weekdays, 4h Saturday). "
        "Revenue is drawn from kept visits only.", 120), fontsize=7.2, color=MUTED, va="top", linespacing=1.7)
    return fig


def page_insights(ctx: ReportContext) -> plt.Figure:
    fig = _page()
    _header(fig, "Consulting layer  ·  Flags & recommended actions", f"{ctx.clinic}  ·  {ctx.window_label}")

    y = 0.845
    fig.text(0.07, y, _track("ANOMALY FLAGS"), fontsize=7.4, color=MUTED)
    y -= 0.028
    if not ctx.flags:
        fig.text(0.075, y, "No metric moved far enough from its recent range to warrant a flag.", fontsize=8.4, color=MUTED)
        y -= 0.030
    for f in ctx.flags[:5]:
        color = ALERT if f.severity == "alert" else (WATCH if f.severity == "watch" else SERIES_COLORS["kept"])
        fig.add_artist(plt.Line2D([0.07, 0.07], [y - 0.026, y + 0.012], transform=fig.transFigure, color=color, linewidth=2.2))
        fig.text(0.082, y + 0.002, f"[{f.severity.upper()}]  {f.title}", fontsize=8.6, color=INK, fontweight="bold")
        fig.text(0.082, y - 0.014, textwrap.fill(f.detail + (" " + f.benchmark_note if f.benchmark_note else ""), 118),
                 fontsize=7.4, color=MUTED, linespacing=1.6, va="top")
        y -= 0.052

    y -= 0.012
    _rule(fig, y + 0.012)
    y -= 0.014
    fig.text(0.07, y, _track("RECOMMENDED ACTIONS"), fontsize=7.4, color=MUTED)
    y -= 0.030
    for i, ins in enumerate(ctx.insights, 1):
        fig.text(0.075, y, f"{i:02d}  {ins['headline']}", fontsize=8.8, color=INK, fontweight="bold")
        y -= 0.019
        body = textwrap.fill(ins["body"], 118)
        fig.text(0.088, y, body, fontsize=7.5, color=MUTED, va="top", linespacing=1.65)
        y -= 0.014 * (body.count("\n") + 1) + 0.010
        act = textwrap.fill("ACTION  " + ins["action"], 118)
        fig.text(0.088, y, act, fontsize=7.5, color=ALERT, va="top", linespacing=1.65)
        y -= 0.014 * (act.count("\n") + 1) + 0.020

    fig.text(0.07, 0.042, "MedVisor PoC 0.1.0  ·  Synthetic / de-identified sample data  ·  Not a medical device",
             fontsize=6.8, color=MUTED)
    return fig


def build_pages(ctx: ReportContext) -> list[plt.Figure]:
    return [page_cover(ctx), page_charts(ctx), page_capacity(ctx), page_insights(ctx)]


def to_pdf(pages: list[plt.Figure]) -> bytes:
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        for fig in pages:
            pdf.savefig(fig, facecolor=fig.get_facecolor())
        meta = pdf.infodict()
        meta["Title"] = "MedVisor Clinic Operations Report (PoC)"
        meta["Subject"] = "Synthetic / de-identified sample data. Not a medical device."
    for fig in pages:
        plt.close(fig)
    return buf.getvalue()


def to_png(fig: plt.Figure, dpi: int = 170) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")