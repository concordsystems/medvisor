"""Automatic anomaly flags — period-over-period with a robust z-score check."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BENCHMARKS


@dataclass
class Finding:
    key: str
    title: str
    detail: str
    severity: str          # alert | watch | ok
    delta_pct: float | None
    z: float | None
    window: str
    benchmark_note: str = ""


def _robust_z(last_value: float, series: np.ndarray) -> float | None:
    s = np.asarray(series, dtype=float)
    s = s[np.isfinite(s)]
    if s.size < 5:
        return None
    med = float(np.median(s))
    mad = float(np.median(np.abs(s - med)))
    if mad <= 1e-9:
        return 0.0
    return float(0.6745 * (last_value - med) / mad)


def detect(
    weekly: pd.Series,
    key: str,
    label: str,
    unit: str = "rate",
    relative_threshold: float = 0.18,
    min_base: float = 1e-6,
    higher_is_bad: bool = True,
    benchmark: float | None = None,
    benchmark_label: str = "",
    window: str = "last 4 weeks vs prior 4 weeks",
) -> Finding | None:
    s = weekly.dropna().astype(float)
    if len(s) < 8:
        return None

    recent = s.tail(4).mean()
    prior = s.iloc[-8:-4].mean()
    if prior is None or not np.isfinite(prior) or abs(prior) < min_base:
        return None

    delta = float((recent - prior) / abs(prior))
    z = _robust_z(float(s.tail(4).mean()), s.values)

    big = abs(delta) >= relative_threshold
    z_big = z is not None and abs(z) >= 2.2
    z_severe = z is not None and abs(z) >= 2.9
    bad = (delta > 0) if higher_is_bad else (delta < 0)

    if (big or z_big) and bad:
        severity = "alert" if (z_severe or abs(delta) >= 0.30) else "watch"
    elif (big or z_big):
        severity = "ok"
    else:
        severity = "ok"

    if severity == "ok" and not (big or z_big):
        return None

    unit_txt = {
        "rate": f"{recent * 100:.1f}% vs {prior * 100:.1f}%",
        "minutes": f"{recent:.0f} min vs {prior:.0f} min",
        "percent": f"{recent * 100:.0f}% vs {prior * 100:.0f}%",
        "money": f"{recent:,.0f} vs {prior:,.0f}",
        "count": f"{recent:,.0f} vs {prior:,.0f}",
    }.get(unit, f"{recent:.2f} vs {prior:.2f}")

    direction = "up" if delta > 0 else "down"
    title = f"{label} {direction} {abs(delta) * 100:.0f}%"
    detail = f"{unit_txt} across the comparison window."

    note = ""
    if benchmark is not None:
        gap = recent - benchmark
        state = "above" if gap > 0 else "below"
        if unit in ("rate", "percent"):
            b_txt, g_txt = f"{benchmark * 100:.0f}%", f"{abs(gap) * 100:.1f} pts"
        elif unit == "minutes":
            b_txt, g_txt = f"{benchmark:.0f} min", f"{abs(gap):.1f} min"
        else:
            b_txt, g_txt = f"{benchmark:,.0f}", f"{abs(gap):,.1f}"
        note = f"{benchmark_label or 'Reference threshold'}: {b_txt} — currently {state} it by {g_txt}."

    return Finding(
        key=key,
        title=title,
        detail=detail,
        severity=severity,
        delta_pct=delta,
        z=z,
        window=window,
        benchmark_note=note,
    )


def run_all(summary_now: dict, summary_prev: dict, weekly: pd.DataFrame, util: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    specs = [
        ("no_show_rate", "No-show rate", "rate", True, BENCHMARKS["no_show_rate"], "Reference threshold"),
        ("cancel_rate", "Cancellation rate", "rate", True, BENCHMARKS["cancel_rate"], "Reference threshold"),
        ("wait_median", "Median wait time", "minutes", True, BENCHMARKS["wait_median"], "Reference threshold"),
        ("revenue_per_visit", "Revenue per visit", "money", False, None, ""),
    ]
    for key, label, unit, bad_direction, bench, bench_label in specs:
        series = weekly.get(key)
        if series is None or series.dropna().empty:
            continue
        f = detect(
            series,
            key=key,
            label=label,
            unit=unit,
            higher_is_bad=bad_direction,
            benchmark=bench,
            benchmark_label=bench_label,
        )
        if f:
            findings.append(f)

    if util is not None and not util.empty:
        u = util["utilization"].astype(float)
        z = _robust_z(float(u.tail(3).mean()), u.values)
        mean_u = float(u.mean())
        if mean_u < BENCHMARKS["utilization"] - 0.03:
            findings.append(
                Finding(
                    key="utilization",
                    title=f"Provider utilisation at {mean_u * 100:.0f}%",
                    detail=f"{(BENCHMARKS['utilization'] - mean_u) * 100:.0f} pts of clinical capacity is going unused on average.",
                    severity="alert" if mean_u < 0.70 else "watch",
                    delta_pct=None,
                    z=z,
                    window="period to date",
                    benchmark_note=f"Reference threshold: {BENCHMARKS['utilization'] * 100:.0f}%.",
                )
            )

    kept_drop = summary_prev.get("kept", 0) - summary_now.get("kept", 0)
    if summary_prev.get("kept", 0) > 0 and kept_drop > max(5, summary_prev["kept"] * 0.08):
        findings.append(
            Finding(
                key="kept_volume",
                title=f"{kept_drop:,.0f} fewer kept visits",
                detail=f"Kept visits fell from {summary_prev['kept']:,.0f} to {summary_now['kept']:,.0f} against the previous window of equal length.",
                severity="watch",
                delta_pct=-kept_drop / summary_prev["kept"],
                z=None,
                window="period vs previous period",
            )
        )

    order = {"alert": 0, "watch": 1, "ok": 2}
    findings.sort(key=lambda f: (order.get(f.severity, 3), -(f.delta_pct or 0)))
    return findings